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


def _can_post_as_user(user) -> bool:
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


async def _mark_ok(ad, group, user, now: datetime, seed: int, how: str):
    await update_ad(ad.id, last_posted_at=now, variant_seed=seed)
    await update_group(
        group.id,
        last_post_at=now,
        fail_count=0,
        cooldown_until=None,
    )
    await add_post_log(ad.id, group.id, user.id, "ok", how)


async def _assist_forward(bot: Bot, ad, group, user, text: str) -> None:
    title = group.title or str(group.chat_id)
    header = (
        f"📣 Пора в <b>{title}</b>\n\n"
        "Ниже готовый пост — <b>перешли его в группу</b> "
        "(зажми сообщение → Переслать)."
    )
    await bot.send_message(user.telegram_id, header)
    if ad.photo_file_id:
        await bot.send_photo(user.telegram_id, ad.photo_file_id, caption=text)
    else:
        await bot.send_message(user.telegram_id, text)


async def _assist_batch(bot: Bot, ad, groups: list, user, text: str, seed: int) -> int:
    """One ready post in DM for many groups (fast, Vercel-safe)."""
    now = datetime.utcnow()
    names = ", ".join((g.title or str(g.chat_id)) for g in groups)
    header = (
        f"📣 Готовый пост для: <b>{names}</b>\n\n"
        "Перешли сообщение ниже в каждую барахолку "
        "(зажми → Переслать)."
    )
    await bot.send_message(user.telegram_id, header)
    if ad.photo_file_id:
        await bot.send_photo(user.telegram_id, ad.photo_file_id, caption=text)
    else:
        await bot.send_message(user.telegram_id, text)

    for group in groups:
        await _mark_ok(ad, group, user, now, seed, "assist_batch")
    return len(groups)


async def post_ad_to_group(bot: Bot, ad, group, user) -> bool:
    """Post via linked account, or assist-mode DM. Always falls back to assist."""
    now = datetime.utcnow()
    seed = (ad.variant_seed or 0) + 1
    text = build_ad_variants(ad.text, ad.price, seed)

    if not _can_post_as_user(user):
        try:
            await _global_throttle()
            await _assist_forward(bot, ad, group, user, text)
            await _mark_ok(ad, group, user, now, seed, "assist")
            return True
        except Exception as e:
            await add_post_log(ad.id, group.id, user.id, "error", str(e))
            logger.exception("Assist post failed ad=%s group=%s", ad.id, group.id)
            return False

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
        await update_group(group.id, cooldown_until=cooldown, fail_count=(group.fail_count or 0) + 1)
        await add_post_log(ad.id, group.id, user.id, "error", f"FloodWait {e.seconds}")
        return False

    except Exception as e:
        msg = str(e)
        logger.warning("Account post failed, fallback assist: %s", msg)
        # Broken / unusable session → drop it so UI shows assist mode
        if isinstance(e, AccountError) or "session" in msg.lower() or "api" in msg.lower():
            try:
                await set_user_tg_session(user.telegram_id, None)
                user.tg_session = None
            except Exception:
                pass
        try:
            await _assist_forward(bot, ad, group, user, text)
            await _mark_ok(ad, group, user, now, seed, "assist_fallback")
            return True
        except Exception as e2:
            await add_post_log(ad.id, group.id, user.id, "error", f"{msg} | assist: {e2}")
            logger.exception("Assist fallback failed")
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
                await asyncio.sleep(
                    random.randint(INTER_GROUP_DELAY_MIN, INTER_GROUP_DELAY_MAX) if ok else 5
                )


async def run_posting_for_telegram_user(bot: Bot, telegram_id: int, force: bool = False) -> dict:
    """
    Immediate post/assist for one user (works on Vercel webhook).
    On force + assist: one DM batch per ad (not 4× spam), avoids timeouts.
    """
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

    # Drop dead "linked" state without API — otherwise UI lies and Telethon crashes
    if user_has_tg_account(user) and not api_configured():
        await set_user_tg_session(telegram_id, None)
        user.tg_session = None

    assist = not _can_post_as_user(user)
    ok_n = 0
    skip_n = 0
    last_error = None
    now = datetime.utcnow()

    if force and assist:
        for ad in ads:
            seed = (ad.variant_seed or 0) + 1
            text = build_ad_variants(ad.text, ad.price, seed)
            try:
                n = await _assist_batch(bot, ad, groups, user, text, seed)
                ok_n += n
            except Exception as e:
                last_error = str(e)
                logger.exception("assist_batch failed")
                skip_n += len(groups)
        return {
            "ok": ok_n,
            "skip": skip_n,
            "reason": None if ok_n else "send_failed",
            "assist": True,
            "error": last_error,
        }

    for ad in ads:
        for group in groups:
            if not due_for_group(group, ad, now, force=force):
                skip_n += 1
                continue
            try:
                if await post_ad_to_group(bot, ad, group, user):
                    ok_n += 1
                else:
                    skip_n += 1
                    last_error = "post_failed"
            except Exception as e:
                skip_n += 1
                last_error = str(e)
                logger.exception("post loop")
            await asyncio.sleep(0.3)

    return {
        "ok": ok_n,
        "skip": skip_n,
        "reason": None if ok_n else ("send_failed" if last_error else None),
        "assist": assist or not _can_post_as_user(user),
        "error": last_error,
    }
