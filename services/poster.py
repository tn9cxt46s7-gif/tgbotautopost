"""Poster: publish ads from the client's Telegram account (Telethon)."""

from __future__ import annotations

import asyncio
import logging
import random
from datetime import datetime, timedelta
from io import BytesIO

from aiogram import Bot

from config import (
    MAX_GROUP_FAILS,
    INTER_GROUP_DELAY_MIN,
    INTER_GROUP_DELAY_MAX,
    GLOBAL_POST_DELAY,
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


def can_autopost(user) -> bool:
    return bool(user_has_tg_account(user) and api_configured())


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


async def post_ad_to_group(bot: Bot, ad, group, user) -> bool:
    """Post one ad to one group from the client's account."""
    if not can_autopost(user):
        await add_post_log(ad.id, group.id, user.id, "error", "account_not_linked")
        return False

    now = datetime.utcnow()
    seed = (ad.variant_seed or 0) + 1
    text = build_ad_variants(ad.text, ad.price, seed)

    photo_bytes = None
    if ad.photo_file_id:
        photo_bytes = await _download_photo(bot, ad.photo_file_id)

    try:
        await _global_throttle()
        await send_as_user(user, group.chat_id, text, photo_bytes)

        await update_ad(ad.id, last_posted_at=now, variant_seed=seed)
        await update_group(
            group.id,
            last_post_at=now,
            fail_count=0,
            cooldown_until=None,
        )
        await add_post_log(ad.id, group.id, user.id, "ok", "user_account")
        logger.info("Posted ad=%s group=%s", ad.id, group.id)
        return True

    except FloodWaitError as e:
        cooldown = datetime.utcnow() + timedelta(seconds=e.seconds + 5)
        fails = (group.fail_count or 0) + 1
        await update_group(group.id, cooldown_until=cooldown, fail_count=fails)
        await add_post_log(ad.id, group.id, user.id, "error", f"FloodWait {e.seconds}")
        return False

    except AccountError as e:
        msg = str(e)
        fails = (group.fail_count or 0) + 1
        kwargs: dict = {"fail_count": fails}
        if any(x in msg.lower() for x in ("сессия", "привязан", "недействительн", "недоступн")):
            await set_user_tg_session(user.telegram_id, None)
            try:
                await bot.send_message(
                    user.telegram_id,
                    f"⚠️ Сессия аккаунта слетела: {msg}\n"
                    "Открой «Мой аккаунт» → подключи снова через QR.",
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
        return False

    except Exception as e:
        fails = (group.fail_count or 0) + 1
        cooldown = datetime.utcnow() + timedelta(minutes=15)
        kwargs = {"fail_count": fails, "cooldown_until": cooldown}
        if fails >= MAX_GROUP_FAILS:
            kwargs["active"] = False
        await update_group(group.id, **kwargs)
        await add_post_log(ad.id, group.id, user.id, "error", str(e))
        logger.exception("Post error ad=%s group=%s", ad.id, group.id)
        return False


async def run_posting_cycle(bot: Bot):
    from database import get_active_ads_for_posting

    rows = await get_active_ads_for_posting()
    if not rows:
        return

    now = datetime.utcnow()
    by_user: dict[int, list] = {}
    for ad, user in rows:
        by_user.setdefault(user.id, []).append((ad, user))

    for user_id, items in by_user.items():
        groups = await get_active_groups_for_user(user_id)
        if not groups:
            continue
        for ad, user in items:
            if not can_autopost(user):
                continue
            for group in groups:
                if not due_for_group(group, ad, now):
                    continue
                ok = await post_ad_to_group(bot, ad, group, user)
                await asyncio.sleep(
                    random.randint(INTER_GROUP_DELAY_MIN, INTER_GROUP_DELAY_MAX) if ok else 5
                )


async def run_posting_for_telegram_user(bot: Bot, telegram_id: int, force: bool = False) -> dict:
    from database import get_user, get_user_ads

    user = await get_user(telegram_id)
    if not user:
        return {"ok": 0, "skip": 0, "reason": "no_user", "error": None}
    if not api_configured():
        return {"ok": 0, "skip": 0, "reason": "no_api", "error": None}
    if not user_has_tg_account(user):
        return {"ok": 0, "skip": 0, "reason": "no_account", "error": None}
    if not user.autopost_enabled and not force:
        return {"ok": 0, "skip": 0, "reason": "autopost_off", "error": None}

    ads = [a for a in await get_user_ads(user.id) if a.status == "active"]
    groups = list(await get_active_groups_for_user(user.id))
    if not ads:
        return {"ok": 0, "skip": 0, "reason": "no_ads", "error": None}
    if not groups:
        return {"ok": 0, "skip": 0, "reason": "no_groups", "error": None}

    now = datetime.utcnow()
    ok_n = 0
    skip_n = 0
    last_error = None
    for ad in ads:
        for group in groups:
            if not due_for_group(group, ad, now, force=force):
                skip_n += 1
                continue
            if await post_ad_to_group(bot, ad, group, user):
                ok_n += 1
            else:
                skip_n += 1
                last_error = "post_failed"
            await asyncio.sleep(random.randint(INTER_GROUP_DELAY_MIN, INTER_GROUP_DELAY_MAX) if ok_n else 2)

    return {
        "ok": ok_n,
        "skip": skip_n,
        "reason": None if ok_n else "send_failed",
        "error": last_error,
    }
