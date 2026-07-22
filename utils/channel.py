"""Channel membership gate for required bot channel."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from aiogram import Bot
from aiogram.enums import ChatMemberStatus

from config import REQUIRED_CHANNEL, REQUIRED_CHANNEL_URL

logger = logging.getLogger(__name__)

# Cache resolved chat id (username → numeric) for the process lifetime
_resolved_chat_id: str | int | None = None


@dataclass
class SubCheck:
    ok: bool
    reason: str = ""  # ok | not_member | bot_not_admin | chat_not_found | error
    detail: str = ""


def channel_configured() -> bool:
    return bool(REQUIRED_CHANNEL)


def _normalize_chat_ref(raw: str) -> str | int:
    ch = (raw or "").strip()
    if not ch:
        return ch
    if ch.startswith("@"):
        return ch
    # numeric / -100... channel id
    if ch.lstrip("-").isdigit():
        return int(ch)
    return f"@{ch.lstrip('@')}"


async def _chat_ref(bot: Bot) -> str | int:
    """Resolve @username to chat id when possible (more reliable for getChatMember)."""
    global _resolved_chat_id
    if _resolved_chat_id is not None:
        return _resolved_chat_id
    ref = _normalize_chat_ref(REQUIRED_CHANNEL)
    if isinstance(ref, int) or not ref:
        _resolved_chat_id = ref
        return ref
    try:
        chat = await bot.get_chat(ref)
        _resolved_chat_id = chat.id
        logger.info("Resolved channel %s → %s", ref, chat.id)
        return chat.id
    except Exception as e:
        logger.warning("get_chat(%s) failed: %s — using username", ref, e)
        _resolved_chat_id = ref
        return ref


def _is_bot_config_error(err: str) -> bool:
    e = err.lower()
    needles = (
        "bot is not a member",
        "not enough rights",
        "chat not found",
        "chat_id is empty",
        "group chat was upgraded",
        "have no rights",
        "need administrator",
        "bot was kicked",
        "forbidden",
    )
    return any(n in e for n in needles)


def _is_not_member_error(err: str) -> bool:
    e = err.lower()
    return any(
        n in e
        for n in (
            "user not found",
            "participant_id_invalid",
            "user_not_participant",
            "member not found",
        )
    )


async def check_subscription(bot: Bot, user_id: int) -> SubCheck:
    """Check channel membership. Bot must be admin of the channel."""
    if not REQUIRED_CHANNEL:
        return SubCheck(True, "ok")

    try:
        chat_id = await _chat_ref(bot)
        member = await bot.get_chat_member(chat_id, user_id)
        status = member.status

        # aiogram may return enum or str depending on version
        status_val = status.value if hasattr(status, "value") else str(status)

        if status in (
            ChatMemberStatus.MEMBER,
            ChatMemberStatus.ADMINISTRATOR,
            ChatMemberStatus.CREATOR,
        ) or status_val in ("member", "administrator", "creator"):
            return SubCheck(True, "ok")

        if status == ChatMemberStatus.RESTRICTED or status_val == "restricted":
            # Restricted but still in channel
            if getattr(member, "is_member", True):
                return SubCheck(True, "ok")
            return SubCheck(False, "not_member")

        if status in (ChatMemberStatus.LEFT, ChatMemberStatus.KICKED) or status_val in (
            "left",
            "kicked",
        ):
            return SubCheck(False, "not_member")

        # Unknown status — deny safely
        logger.warning("Unknown member status %s for user %s", status_val, user_id)
        return SubCheck(False, "not_member", status_val)

    except Exception as e:
        err = str(e)
        logger.warning("channel check failed user=%s: %s", user_id, err)

        if _is_not_member_error(err):
            return SubCheck(False, "not_member", err)

        if _is_bot_config_error(err):
            # Bot cannot verify (usually not admin). Fail OPEN so users aren't stuck,
            # but surface reason so owner can fix.
            logger.error(
                "Channel gate misconfigured for %s — allowing access. "
                "Add the bot as ADMIN of the channel. Error: %s",
                REQUIRED_CHANNEL,
                err,
            )
            return SubCheck(True, "bot_not_admin", err)

        # Unknown API error — fail open once rather than lock everyone
        logger.error("Unexpected channel check error, allowing: %s", err)
        return SubCheck(True, "error", err)


async def is_subscribed(bot: Bot, user_id: int) -> bool:
    """True if channel not configured, or user is a member (or check impossible)."""
    result = await check_subscription(bot, user_id)
    return result.ok


def channel_url() -> str | None:
    if REQUIRED_CHANNEL_URL:
        return REQUIRED_CHANNEL_URL
    ch = (REQUIRED_CHANNEL or "").strip()
    if not ch:
        return None
    if ch.startswith("@"):
        return f"https://t.me/{ch.lstrip('@')}"
    if ch.startswith("-100") or ch.lstrip("-").isdigit():
        return None
    return f"https://t.me/{ch.lstrip('@')}"
