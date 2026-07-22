"""Poster: publish ads into groups via user account (Telethon) or bot API."""

from __future__ import annotations

import asyncio
import logging
import random
import time
from datetime import datetime, timedelta
from io import BytesIO

from aiogram import Bot
from aiogram.exceptions import TelegramAPIError, TelegramForbiddenError, TelegramBadRequest

from config import (
    MAX_GROUP_FAILS,
    INTER_GROUP_DELAY_MIN,
    INTER_GROUP_DELAY_MAX,
    GLOBAL_POST_DELAY,
    POST_BUDGET_SECONDS,
)
from database import (
    get_active_groups_for_user,
    update_ad,
    update_group,
    add_post_log,
    set_user_tg_session,
    user_has_tg_account,
)
from services.user_client import AccountError, FloodWaitError, send_as_user, api_configured

logger = logging.getLogger(__name__)

_post_lock = asyncio.Lock()
_last_global_post: datetime | None = None


def _in_quiet_hours(now: datetime, start: int, end: int) -> bool:
    if start == end:
        return False
    hour = now.hour
    if start < end:
        return start <= hour < end
    return hour >= start or hour < end


def build_ad_variants(text: str, price: str | None, seed: int) -> str:
    lines = [ln for ln in text.strip().splitlines() if ln.strip()]
    if not lines:
        body = text.strip()
    else:
        rng = random.Random(seed)
        head, rest = lines[0], lines[1:]
        if len(rest) > 1 and seed % 3 == 0:
            rng.shuffle(rest)
        body = "\n".join([head] + rest)

    tags = ["#продажа", "#объявление", "#барахолка", "#товар", "#срочно"]
    tag = tags[seed % len(tags)]

    parts = [body]
    if price:
        price_forms = [
            f"💰 Цена: {price}",
            f"💵 Стоимость: {price}",
            f"🏷 {price}",
        ]
        parts.append(price_forms[seed % len(price_forms)])

    if seed % 2 == 0:
        parts.append(tag)
    else:
        parts.insert(0, tag)

    spacer = " " * ((seed % 3) + 1)
    return "\n\n".join(parts) + spacer


def due_for_group(group, ad, now: datetime, force: bool = False) -> bool:
    if force:
        return True
    if group.cooldown_until and group.cooldown_until > now:
        return False
    if _in_quiet_hours(now, group.quiet_hours_start or 0, group.quiet_hours_end or 0):
        return False

    last = group.last_post_at
    base_min = group.min_interval_minutes or 60
    jitter = group.jitter_seconds or 0
    earliest = timedelta(minutes=base_min) - timedelta(seconds=jitter)
    if earliest.total_seconds() < 30 * 60:
        earliest = timedelta(minutes=30)

    if last and now - last < earliest:
        return False
    return True


def can_user_post(user) -> bool:
    """True if posts can go from the client's Telegram account."""
    return bool(user_has_tg_account(user) and api_configured())


def can_bot_post_group(group) -> bool:
    return bool(getattr(group, "bot_can_post", False))


def can_post_anywhere(user, groups) -> bool:
    if can_user_post(user):
        return True
    return any(can_bot_post_group(g) for g in groups)


# Back-compat alias used by handlers
can_autopost = can_user_post


async def _global_throttle():
    global _last_global_post
    async with _post_lock:
        now = datetime.utcnow()
        if _last_global_post:
            elapsed = (now - _last_global_post).total_seconds()
            if elapsed < GLOBAL_POST_DELAY:
                await asyncio.sleep(GLOBAL_POST_DELAY - elapsed)
        _last_global_post = datetime.utcnow()


async def _download_photo(bot: Bot, file_id: str) -> bytes | None:
    try:
        buf = BytesIO()
        await bot.download(file_id, destination=buf)
        return buf.getvalue()
    except Exception:
        logger.exception("Failed to download photo %s", file_id)
        return None


async def _send_via_bot(bot: Bot, chat_id: int, text: str, photo_file_id: str | None) -> None:
    if photo_file_id:
        await bot.send_photo(chat_id, photo_file_id, caption=text)
    else:
        await bot.send_message(chat_id, text)


async def _mark_ok(ad, group, user, via: str):
    now = datetime.utcnow()
    seed = (ad.variant_seed or 0) + 1
    await update_ad(ad.id, last_posted_at=now, variant_seed=seed)
    await update_group(
        group.id,
        last_post_at=now,
        fail_count=0,
        cooldown_until=None,
        bot_can_post=True if via == "bot" else getattr(group, "bot_can_post", False),
    )
    await add_post_log(ad.id, group.id, user.id, "ok", via)
    logger.info("Posted ad=%s group=%s via=%s", ad.id, group.id, via)


async def _mark_fail(bot: Bot, ad, group, user, msg: str, *, drop_session: bool = False):
    fails = (group.fail_count or 0) + 1
    kwargs: dict = {"fail_count": fails}
    if drop_session:
        await set_user_tg_session(user.telegram_id, None)
        try:
            await bot.send_message(
                user.telegram_id,
                f"⚠️ Сессия аккаунта слетела: {msg}\n"
                "Открой «Мой аккаунт» → подключи снова.",
            )
        except Exception:
            pass
    else:
        cooldown = datetime.utcnow() + timedelta(minutes=15)
        kwargs["cooldown_until"] = cooldown
        if fails >= MAX_GROUP_FAILS:
            kwargs["active"] = False
        try:
            await bot.send_message(
                user.telegram_id,
                f"⚠️ Не смог запостить в «{group.title or group.chat_id}»: {msg}"
                + (" Группа отключена." if fails >= MAX_GROUP_FAILS else ""),
            )
        except Exception:
            pass
    await update_group(group.id, **kwargs)
    await add_post_log(ad.id, group.id, user.id, "error", msg)


async def post_ad_to_group(bot: Bot, ad, group, user) -> bool:
    """Post one ad to one group: prefer user account, else bot API."""
    now = datetime.utcnow()
    seed = (ad.variant_seed or 0) + 1
    text = build_ad_variants(ad.text, ad.price, seed)

    # 1) From client's account (works in flea markets that ban bots)
    if can_user_post(user):
        photo_bytes = None
        if ad.photo_file_id:
            photo_bytes = await _download_photo(bot, ad.photo_file_id)
        try:
            await _global_throttle()
            await send_as_user(user, group.chat_id, text, photo_bytes)
            await update_ad(ad.id, last_posted_at=now, variant_seed=seed)
            await update_group(group.id, last_post_at=now, fail_count=0, cooldown_until=None)
            await add_post_log(ad.id, group.id, user.id, "ok", "user_account")
            logger.info("Posted ad=%s group=%s via=user", ad.id, group.id)
            return True
        except FloodWaitError as e:
            cooldown = datetime.utcnow() + timedelta(seconds=e.seconds + 5)
            fails = (group.fail_count or 0) + 1
            await update_group(group.id, cooldown_until=cooldown, fail_count=fails)
            await add_post_log(ad.id, group.id, user.id, "error", f"FloodWait {e.seconds}")
            return False
        except AccountError as e:
            msg = str(e)
            drop = any(x in msg.lower() for x in ("сессия", "привязан", "недействительн", "недоступн"))
            if drop:
                await _mark_fail(bot, ad, group, user, msg, drop_session=True)
                if not can_bot_post_group(group):
                    return False
                # fall through: try bot
            elif can_bot_post_group(group):
                # soft fail — still try bot
                logger.warning("User post failed, trying bot: %s", msg)
            else:
                await _mark_fail(bot, ad, group, user, msg)
                return False
        except Exception as e:
            if can_bot_post_group(group):
                logger.warning("User post error, trying bot: %s", e)
            else:
                await _mark_fail(bot, ad, group, user, str(e))
                logger.exception("Post error ad=%s group=%s", ad.id, group.id)
                return False

    # 2) From the bot (groups where the bot is a member/admin)
    if can_bot_post_group(group) or not can_user_post(user):
        try:
            await _global_throttle()
            await _send_via_bot(bot, group.chat_id, text, ad.photo_file_id)
            await _mark_ok(ad, group, user, "bot")
            return True
        except (TelegramForbiddenError, TelegramBadRequest, TelegramAPIError) as e:
            await update_group(group.id, bot_can_post=False)
            await _mark_fail(bot, ad, group, user, f"Бот не может писать: {e}")
            return False
        except Exception as e:
            await _mark_fail(bot, ad, group, user, str(e))
            logger.exception("Bot post error ad=%s group=%s", ad.id, group.id)
            return False

    await add_post_log(ad.id, group.id, user.id, "error", "no_post_channel")
    return False


async def run_posting_cycle(bot: Bot, budget_seconds: int | None = None):
    from database import get_active_ads_for_posting

    rows = await get_active_ads_for_posting()
    if not rows:
        return {"ok": 0, "skip": 0, "budget_left": True}

    budget = budget_seconds if budget_seconds is not None else POST_BUDGET_SECONDS
    started = time.monotonic()
    now = datetime.utcnow()
    ok_n = 0
    skip_n = 0

    by_user: dict[int, list] = {}
    for ad, user in rows:
        by_user.setdefault(user.id, []).append((ad, user))

    for user_id, items in by_user.items():
        if time.monotonic() - started > budget:
            break
        groups = await get_active_groups_for_user(user_id)
        if not groups:
            continue
        for ad, user in items:
            if not can_post_anywhere(user, groups):
                continue
            for group in groups:
                if time.monotonic() - started > budget:
                    return {"ok": ok_n, "skip": skip_n, "budget_left": False}
                if not due_for_group(group, ad, now):
                    skip_n += 1
                    continue
                # Skip groups that need user-account but none linked
                if not can_user_post(user) and not can_bot_post_group(group):
                    skip_n += 1
                    continue
                ok = await post_ad_to_group(bot, ad, group, user)
                if ok:
                    ok_n += 1
                    await asyncio.sleep(
                        random.randint(INTER_GROUP_DELAY_MIN, INTER_GROUP_DELAY_MAX)
                    )
                else:
                    skip_n += 1
                    await asyncio.sleep(2)

    return {"ok": ok_n, "skip": skip_n, "budget_left": True}


async def run_posting_for_telegram_user(bot: Bot, telegram_id: int, force: bool = False) -> dict:
    from database import get_user, get_user_ads

    user = await get_user(telegram_id)
    if not user:
        return {"ok": 0, "skip": 0, "reason": "no_user", "error": None}
    if not user.autopost_enabled and not force:
        return {"ok": 0, "skip": 0, "reason": "autopost_off", "error": None}

    ads = [a for a in await get_user_ads(user.id) if a.status == "active"]
    groups = list(await get_active_groups_for_user(user.id))
    if not ads:
        return {"ok": 0, "skip": 0, "reason": "no_ads", "error": None}
    if not groups:
        return {"ok": 0, "skip": 0, "reason": "no_groups", "error": None}
    if not can_post_anywhere(user, groups):
        return {"ok": 0, "skip": 0, "reason": "no_channel", "error": None}

    now = datetime.utcnow()
    started = time.monotonic()
    ok_n = 0
    skip_n = 0
    last_error = None
    for ad in ads:
        for group in groups:
            if time.monotonic() - started > POST_BUDGET_SECONDS:
                break
            if not due_for_group(group, ad, now, force=force):
                skip_n += 1
                continue
            if not can_user_post(user) and not can_bot_post_group(group):
                skip_n += 1
                continue
            if await post_ad_to_group(bot, ad, group, user):
                ok_n += 1
            else:
                skip_n += 1
                last_error = "post_failed"
            await asyncio.sleep(
                random.randint(INTER_GROUP_DELAY_MIN, INTER_GROUP_DELAY_MAX) if ok_n else 2
            )

    return {
        "ok": ok_n,
        "skip": skip_n,
        "reason": None if ok_n else "send_failed",
        "error": last_error,
    }
