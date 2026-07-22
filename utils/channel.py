"""Channel membership gate for required bot channel."""

from __future__ import annotations

import logging

from aiogram import Bot
from aiogram.enums import ChatMemberStatus

from config import REQUIRED_CHANNEL

logger = logging.getLogger(__name__)


def channel_configured() -> bool:
    return bool(REQUIRED_CHANNEL)


async def is_subscribed(bot: Bot, user_id: int) -> bool:
    """True if channel not configured, or user is a member/admin/creator."""
    if not REQUIRED_CHANNEL:
        return True
    try:
        member = await bot.get_chat_member(REQUIRED_CHANNEL, user_id)
        return member.status in (
            ChatMemberStatus.MEMBER,
            ChatMemberStatus.ADMINISTRATOR,
            ChatMemberStatus.CREATOR,
            ChatMemberStatus.RESTRICTED,
        )
    except Exception as e:
        logger.warning("channel check failed for %s: %s", user_id, e)
        # Fail open only if channel is misconfigured (chat not found); otherwise deny
        err = str(e).lower()
        if "chat not found" in err or "chat_id is empty" in err:
            return True
        return False


def channel_url() -> str | None:
    ch = (REQUIRED_CHANNEL or "").strip()
    if not ch:
        return None
    if ch.startswith("@"):
        return f"https://t.me/{ch.lstrip('@')}"
    if ch.startswith("-100") or ch.lstrip("-").isdigit():
        # private invite must be set via REQUIRED_CHANNEL_URL
        from config import REQUIRED_CHANNEL_URL
        return REQUIRED_CHANNEL_URL or None
    return f"https://t.me/{ch.lstrip('@')}"
