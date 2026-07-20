"""Anti-ban poster: user-account auto OR assist (DM ready post to forward)."""

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
from services.user_client import AccountError, FloodWaitError, send_as_user

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


def due_for_group(group, ad, now: datetime) -> bool:
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


async def _mark_ok(ad, group, user, now: datetime, seed: int, how: str):
    await update_ad(ad.id, last_posted_at=now, variant_seed=seed)
    await update_group(
        group.id,
        last_post_at=now,
        fail_count=0,
        cooldown_until=None,
    )
    await add_post_log(ad.id, group.id, user.id, "ok", how)
    logger.info("%s ad=%s group=%s", how, ad.id, group.id)


async def _assist_forward(bot: Bot, ad, group, user, text: str) -> None:
    """Send ready post to user DM — they forward it into the marketplace group."""
    title = group.title or str(group.chat_id)
    header = (
        f"📣 Пора запостить в <b>{title}</b>\n"
        f"Перешли следующее сообщение в эту группу 👇"
    )
    await bot.send_message(user.telegram_id, header)

    if ad.photo_file_id:
        await bot.send_photo(user.telegram_id, ad.photo_file_id, caption=text)
    else:
        await bot.send_message(user.telegram_id, text)


async def post_ad_to_group(bot: Bot, ad, group, user) -> bool:
    """Post via linked account, or assist-mode DM if no account linked."""
    now = datetime.utcnow()
    seed = (ad.variant_seed or 0) + 1
    text = build_ad_variants(ad.text, ad.price, seed)

    # ── Assist mode: no account auth required ──────────────────────────────
    if not user_has_tg_account(user):
        try:
            await _global_throttle()
            await _assist_forward(bot, ad, group, user, text)
            await _mark_ok(ad, group, user, now, seed, "assist")
            return True
        except Exception as e:
            fails = (group.fail_count or 0) + 1
            cooldown = datetime.utcnow() + timedelta(minutes=15)
            kwargs = {"fail_count": fails, "cooldown_until": cooldown}
            if fails >= MAX_GROUP_FAILS:
                kwargs["active"] = False
            await update_group(group.id, **kwargs)
            await add_post_log(ad.id, group.id, user.id, "error", str(e))
            logger.exception("Assist post failed ad=%s group=%s", ad.id, group.id)
            return False

    # ── Full auto: Telethon from client account ────────────────────────────
    photo_bytes = None
    if ad.photo_file_id:
        photo_bytes = await _download_photo(bot, ad.photo_file_id)

    try:
        await _global_throttle()
        await send_as_user(user, group.chat_id, text, photo_bytes)
        await _mark_ok(ad, group, user, now, seed, "user_account")
        return True

    except FloodWaitError as e:
        cooldown = datetime.utcnow() + timedelta(seconds=e.seconds + 5)
        fails = (group.fail_count or 0) + 1
        await update_group(group.id, cooldown_until=cooldown, fail_count=fails)
        await add_post_log(ad.id, group.id, user.id, "error", f"FloodWait {e.seconds}")
        logger.warning("FloodWait ad=%s group=%s wait=%s", ad.id, group.id, e.seconds)
        return False

    except AccountError as e:
        msg = str(e)
        fails = (group.fail_count or 0) + 1
        kwargs: dict = {"fail_count": fails}
        if "Сессия" in msg or "привязан" in msg.lower() or "недействительна" in msg.lower():
            await set_user_tg_session(user.telegram_id, None)
            try:
                await bot.send_message(
                    user.telegram_id,
                    f"⚠️ Автопост от аккаунта недоступен: {msg}\n"
                    "Переключился на режим «пришлю готовый пост — перешли сам».\n"
                    "Или подключи QR снова в «Мой аккаунт».",
                )
            except Exception:
                pass
            # fallback to assist once
            try:
                await _assist_forward(bot, ad, group, user, text)
                await _mark_ok(ad, group, user, now, seed, "assist_fallback")
                return True
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
                    f"⚠️ Не удалось постить в «{group.title or group.chat_id}»: {msg}"
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
            for group in groups:
                if not due_for_group(group, ad, now):
                    continue

                ok = await post_ad_to_group(bot, ad, group, user)
                if ok:
                    delay = random.randint(INTER_GROUP_DELAY_MIN, INTER_GROUP_DELAY_MAX)
                    await asyncio.sleep(delay)
                else:
                    await asyncio.sleep(5)
