"""Anti-ban poster: per-group intervals, jitter, quiet hours, text variants, cooldowns."""

from __future__ import annotations

import asyncio
import logging
import random
from datetime import datetime, timedelta

from aiogram import Bot
from aiogram.exceptions import TelegramRetryAfter, TelegramForbiddenError, TelegramAPIError

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
)

logger = logging.getLogger(__name__)

_post_lock = asyncio.Lock()
_last_global_post: datetime | None = None


def _in_quiet_hours(now: datetime, start: int, end: int) -> bool:
    """Return True if current UTC hour is inside quiet window [start, end)."""
    if start == end:
        return False
    hour = now.hour
    if start < end:
        return start <= hour < end
    # wraps midnight, e.g. 23-7
    return hour >= start or hour < end


def build_ad_variants(text: str, price: str | None, seed: int) -> str:
    """Produce a slight variation of the ad text to reduce duplicate-spam flags."""
    lines = [ln for ln in text.strip().splitlines() if ln.strip()]
    if not lines:
        body = text.strip()
    else:
        rng = random.Random(seed)
        # occasionally shuffle non-first lines
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

    # rotate tag placement
    if seed % 2 == 0:
        parts.append(tag)
    else:
        parts.insert(0, tag)

    # invisible variation: zero-width / spacing (keep HTML-safe, just trailing spaces pattern)
    spacer = " " * ((seed % 3) + 1)
    return "\n\n".join(parts) + spacer


def due_for_group(group, ad, now: datetime) -> bool:
    if group.cooldown_until and group.cooldown_until > now:
        return False
    if _in_quiet_hours(now, group.quiet_hours_start or 0, group.quiet_hours_end or 0):
        return False

    # group interval + jitter
    last = group.last_post_at
    base_min = group.min_interval_minutes or 60
    jitter = group.jitter_seconds or 0
    # effective wait = interval + random jitter already applied at last schedule;
    # for due check use interval - jitter as earliest, interval + jitter as latest window
    earliest = timedelta(minutes=base_min) - timedelta(seconds=jitter)
    if earliest.total_seconds() < 30 * 60:
        earliest = timedelta(minutes=30)

    if last and now - last < earliest:
        return False

    # also respect ad-level interval
    ad_interval = timedelta(minutes=ad.interval_minutes or 60)
    if ad.last_posted_at and now - ad.last_posted_at < ad_interval - timedelta(seconds=jitter or 0):
        # allow posting same ad to different groups sooner; only gate if group was recently posted
        pass

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


async def post_ad_to_group(bot: Bot, ad, group, user) -> bool:
    """Post one ad to one group. Returns True on success."""
    now = datetime.utcnow()
    seed = (ad.variant_seed or 0) + 1
    text = build_ad_variants(ad.text, ad.price, seed)

    try:
        await _global_throttle()
        if ad.photo_file_id:
            await bot.send_photo(group.chat_id, ad.photo_file_id, caption=text)
        else:
            await bot.send_message(group.chat_id, text)

        await update_ad(ad.id, last_posted_at=now, variant_seed=seed)
        await update_group(
            group.id,
            last_post_at=now,
            fail_count=0,
            cooldown_until=None,
        )
        await add_post_log(ad.id, group.id, user.id, "ok")
        logger.info("Posted ad=%s group=%s", ad.id, group.id)
        return True

    except TelegramRetryAfter as e:
        cooldown = datetime.utcnow() + timedelta(seconds=e.retry_after + 5)
        fails = (group.fail_count or 0) + 1
        await update_group(group.id, cooldown_until=cooldown, fail_count=fails)
        await add_post_log(ad.id, group.id, user.id, "error", f"FloodWait {e.retry_after}")
        logger.warning("FloodWait ad=%s group=%s wait=%s", ad.id, group.id, e.retry_after)
        return False

    except TelegramForbiddenError as e:
        fails = (group.fail_count or 0) + 1
        kwargs = {"fail_count": fails}
        if fails >= MAX_GROUP_FAILS:
            kwargs["active"] = False
        await update_group(group.id, **kwargs)
        await add_post_log(ad.id, group.id, user.id, "error", str(e))
        try:
            await bot.send_message(
                user.telegram_id,
                f"⚠️ Не могу писать в группу «{group.title or group.chat_id}». "
                f"Проверь права бота. Группа {'отключена' if fails >= MAX_GROUP_FAILS else 'на паузе ошибок'}.",
            )
        except Exception:
            pass
        return False

    except TelegramAPIError as e:
        fails = (group.fail_count or 0) + 1
        cooldown = datetime.utcnow() + timedelta(minutes=15)
        kwargs = {"fail_count": fails, "cooldown_until": cooldown}
        if fails >= MAX_GROUP_FAILS:
            kwargs["active"] = False
        await update_group(group.id, **kwargs)
        await add_post_log(ad.id, group.id, user.id, "error", str(e))
        logger.error("API error ad=%s group=%s: %s", ad.id, group.id, e)
        if fails >= MAX_GROUP_FAILS:
            try:
                await bot.send_message(
                    user.telegram_id,
                    f"⚠️ Группа «{group.title or group.chat_id}» отключена после {fails} ошибок: {e}",
                )
            except Exception:
                pass
        return False


async def run_posting_cycle(bot: Bot):
    """One scheduler tick: post due ads to due groups with anti-ban delays."""
    from database import get_active_ads_for_posting

    rows = await get_active_ads_for_posting()
    if not rows:
        return

    now = datetime.utcnow()
    # group by user to apply inter-group delay
    by_user: dict[int, list] = {}
    for ad, user in rows:
        by_user.setdefault(user.id, []).append((ad, user))

    for user_id, items in by_user.items():
        groups = await get_active_groups_for_user(user_id)
        if not groups:
            continue

        for ad, user in items:
            posted_any = False
            for group in groups:
                if not due_for_group(group, ad, now):
                    continue

                ok = await post_ad_to_group(bot, ad, group, user)
                if ok:
                    posted_any = True
                    delay = random.randint(INTER_GROUP_DELAY_MIN, INTER_GROUP_DELAY_MAX)
                    await asyncio.sleep(delay)
                else:
                    # small pause after error
                    await asyncio.sleep(5)

            if posted_any:
                # refresh ad last_posted already done inside post
                pass
