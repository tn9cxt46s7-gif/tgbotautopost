"""Poster: publish ads ONLY from the client's Telegram account (Telethon).

Bot is never posted into flea markets — clients buy a subscription and posts
must look like normal human ads. Anti-ban: intervals, daily caps, quiet hours,
text variants, FloodWait cooldowns. No system can guarantee zero bans.
"""

from __future__ import annotations

import asyncio
import logging
import random
import time
from datetime import datetime, timedelta
from io import BytesIO

from aiogram import Bot

from config import (
    MAX_GROUP_FAILS,
    INTER_GROUP_DELAY_MIN,
    INTER_GROUP_DELAY_MAX,
    GLOBAL_POST_DELAY,
    POST_BUDGET_SECONDS,
    MIN_INTERVAL_MINUTES,
    FORCE_MIN_INTERVAL_MINUTES,
    MAX_POSTS_PER_GROUP_PER_DAY,
    MAX_POSTS_PER_USER_PER_DAY,
    MAX_GROUPS_PER_TICK,
    FLOOD_COOLDOWN_EXTRA_MINUTES,
    IS_VERCEL,
)
from database import (
    get_active_groups_for_user,
    update_ad,
    update_group,
    add_post_log,
    set_user_tg_session,
    user_has_tg_account,
    count_user_ok_posts_since,
    count_group_ok_posts_since,
)
from services.user_client import AccountError, FloodWaitError, send_as_user, api_configured
from utils.antibot import build_ad_variants, validate_ad_text

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


def _day_start_utc(now: datetime | None = None) -> datetime:
    now = now or datetime.utcnow()
    return datetime(now.year, now.month, now.day)


def due_for_group(group, ad, now: datetime, force: bool = False) -> bool:
    """Whether this group may receive a post now (anti-ban gates)."""
    if group.cooldown_until and group.cooldown_until > now:
        return False
    if _in_quiet_hours(now, group.quiet_hours_start or 0, group.quiet_hours_end or 0):
        return False

    last = group.last_post_at
    base_min = max(group.min_interval_minutes or MIN_INTERVAL_MINUTES, MIN_INTERVAL_MINUTES)
    # Manual «Запостить сейчас» still keeps a soft floor (reduces ban risk)
    if force:
        floor = timedelta(minutes=FORCE_MIN_INTERVAL_MINUTES)
        if last and now - last < floor:
            return False
        return True

    jitter = group.jitter_seconds or 0
    earliest = timedelta(minutes=base_min) - timedelta(seconds=min(jitter, 600))
    if earliest.total_seconds() < MIN_INTERVAL_MINUTES * 60:
        earliest = timedelta(minutes=MIN_INTERVAL_MINUTES)

    if last and now - last < earliest:
        return False
    return True


def can_user_post(user) -> bool:
    return bool(user_has_tg_account(user) and api_configured())


# Back-compat
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


async def _daily_caps_ok(user, group) -> tuple[bool, str | None]:
    since = _day_start_utc()
    user_n = await count_user_ok_posts_since(user.id, since)
    if user_n >= MAX_POSTS_PER_USER_PER_DAY:
        return False, "daily_user_cap"
    group_n = await count_group_ok_posts_since(group.id, since)
    if group_n >= MAX_POSTS_PER_GROUP_PER_DAY:
        return False, "daily_group_cap"
    return True, None


async def _mark_fail(bot: Bot, ad, group, user, msg: str, *, drop_session: bool = False, ban_like: bool = False):
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
        minutes = 60 if ban_like else 20
        kwargs["cooldown_until"] = datetime.utcnow() + timedelta(minutes=minutes)
        if ban_like or fails >= MAX_GROUP_FAILS:
            kwargs["active"] = False
        try:
            extra = ""
            if ban_like or fails >= MAX_GROUP_FAILS:
                extra = (
                    "\nГруппа отключена — похоже на ограничение/бан в чате. "
                    "Проверь правила барахолки и права писать."
                )
            await bot.send_message(
                user.telegram_id,
                f"⚠️ Не смог запостить в «{group.title or group.chat_id}»: {msg}{extra}",
            )
        except Exception:
            pass
    await update_group(group.id, **kwargs)
    await add_post_log(ad.id, group.id, user.id, "error", msg)


async def post_ad_to_group(bot: Bot, ad, group, user) -> bool:
    """Post one ad to one group from the client's account only."""
    if not can_user_post(user):
        await add_post_log(ad.id, group.id, user.id, "error", "account_not_linked")
        return False

    ok_cap, cap_reason = await _daily_caps_ok(user, group)
    if not ok_cap:
        await add_post_log(ad.id, group.id, user.id, "skipped", cap_reason)
        return False

    risk = validate_ad_text(ad.text or "")
    if risk:
        await add_post_log(ad.id, group.id, user.id, "skipped", f"content:{risk}")
        try:
            await bot.send_message(
                user.telegram_id,
                f"⚠️ Объявление #{ad.id} не отправлено (антиспам): {risk}",
            )
        except Exception:
            pass
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
        await update_group(group.id, last_post_at=now, fail_count=0, cooldown_until=None)
        await add_post_log(ad.id, group.id, user.id, "ok", "user_account")
        logger.info("Posted ad=%s group=%s via=user", ad.id, group.id)
        return True

    except FloodWaitError as e:
        cooldown = datetime.utcnow() + timedelta(
            seconds=e.seconds + 5,
            minutes=FLOOD_COOLDOWN_EXTRA_MINUTES,
        )
        fails = (group.fail_count or 0) + 1
        await update_group(group.id, cooldown_until=cooldown, fail_count=fails)
        await add_post_log(ad.id, group.id, user.id, "error", f"FloodWait {e.seconds}")
        try:
            await bot.send_message(
                user.telegram_id,
                f"⏳ Telegram просит паузу {e.seconds}с (FloodWait). "
                f"Группа «{group.title or group.chat_id}» на паузе — так безопаснее для аккаунта.",
            )
        except Exception:
            pass
        return False

    except AccountError as e:
        msg = str(e)
        drop = any(x in msg.lower() for x in ("сессия", "привязан", "недействительн", "недоступн"))
        ban_like = any(
            x in msg.lower()
            for x in ("нет доступа", "banned", "forbidden", "private", "писать")
        )
        await _mark_fail(bot, ad, group, user, msg, drop_session=drop, ban_like=ban_like)
        return False

    except Exception as e:
        await _mark_fail(bot, ad, group, user, str(e))
        logger.exception("Post error ad=%s group=%s", ad.id, group.id)
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
    posted_this_tick = 0

    by_user: dict[int, list] = {}
    for ad, user in rows:
        by_user.setdefault(user.id, []).append((ad, user))

    user_ids = list(by_user.keys())
    random.shuffle(user_ids)

    for user_id in user_ids:
        if time.monotonic() - started > budget:
            break
        if posted_this_tick >= MAX_GROUPS_PER_TICK:
            break
        items = by_user[user_id]
        groups = list(await get_active_groups_for_user(user_id))
        if not groups:
            continue
        random.shuffle(groups)
        for ad, user in items:
            if not can_user_post(user):
                continue
            for group in groups:
                if time.monotonic() - started > budget:
                    return {"ok": ok_n, "skip": skip_n, "budget_left": False}
                if posted_this_tick >= MAX_GROUPS_PER_TICK:
                    return {"ok": ok_n, "skip": skip_n, "budget_left": True}
                if not due_for_group(group, ad, now):
                    skip_n += 1
                    continue
                ok = await post_ad_to_group(bot, ad, group, user)
                if ok:
                    ok_n += 1
                    posted_this_tick += 1
                    if not IS_VERCEL:
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

    # Content gate once
    for ad in ads:
        risk = validate_ad_text(ad.text or "")
        if risk:
            return {"ok": 0, "skip": 0, "reason": "bad_content", "error": risk}

    now = datetime.utcnow()
    started = time.monotonic()
    ok_n = 0
    skip_n = 0
    last_error = None
    random.shuffle(groups)
    # Manual run: still cap how many groups in one go (anti-ban)
    max_now = MAX_GROUPS_PER_TICK if IS_VERCEL else min(5, len(groups))

    for ad in ads:
        for group in groups:
            if ok_n >= max_now:
                break
            if time.monotonic() - started > POST_BUDGET_SECONDS:
                break
            if not due_for_group(group, ad, now, force=force):
                skip_n += 1
                continue
            if await post_ad_to_group(bot, ad, group, user):
                ok_n += 1
            else:
                skip_n += 1
                last_error = "post_failed"
            if not IS_VERCEL and ok_n:
                await asyncio.sleep(random.randint(INTER_GROUP_DELAY_MIN, INTER_GROUP_DELAY_MAX))
            elif ok_n:
                await asyncio.sleep(2)

    reason = None
    if ok_n == 0:
        if skip_n:
            reason = "rate_limited"
        else:
            reason = "send_failed"

    return {
        "ok": ok_n,
        "skip": skip_n,
        "reason": reason,
        "error": last_error,
    }
