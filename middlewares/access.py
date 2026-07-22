"""Access gate: language + required channel before using the bot."""

from __future__ import annotations

from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware, Bot
from aiogram.types import Message, CallbackQuery, TelegramObject

from config import is_admin
from database import get_user
from utils.channel import channel_configured, is_subscribed
from utils.i18n import t
from keyboards import channel_gate_kb, language_kb

# Callbacks / commands allowed without channel
_FREE_CB_PREFIX = ("lang_", "channel_check")
_FREE_CMD_PREFIX = ("/start", "/lang", "/language")


def _cb_free(data: str | None) -> bool:
    if not data:
        return False
    return any(data.startswith(p) for p in _FREE_CB_PREFIX) or data == "channel_check"


def _msg_free(text: str | None) -> bool:
    if not text:
        return False
    low = text.strip().lower()
    return any(low.startswith(p) for p in _FREE_CMD_PREFIX)


class AccessMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        bot: Bot = data["bot"]
        user = None
        message: Message | None = None
        callback: CallbackQuery | None = None

        if isinstance(event, Message):
            message = event
            user = event.from_user
        elif isinstance(event, CallbackQuery):
            callback = event
            user = event.from_user
            message = event.message if isinstance(event.message, Message) else None
        else:
            return await handler(event, data)

        if not user or user.is_bot:
            return await handler(event, data)

        # Always allow free paths
        if message and _msg_free(message.text):
            return await handler(event, data)
        if message and getattr(message, "successful_payment", None):
            return await handler(event, data)
        if callback and _cb_free(callback.data):
            return await handler(event, data)

        db_user = await get_user(user.id)
        lang = getattr(db_user, "language", None) if db_user else None

        # Force language first
        if not lang:
            if callback:
                await callback.answer()
                target = callback.message
            else:
                target = message
            if target:
                await target.answer(
                    t("choose_lang", "en"),
                    reply_markup=language_kb(),
                )
            return None

        data["lang"] = lang

        # Channel gate (admins bypass)
        if channel_configured() and not is_admin(user.id):
            ok = await is_subscribed(bot, user.id)
            if not ok:
                text = t("channel_required", lang)
                kb = channel_gate_kb(lang)
                if callback:
                    await callback.answer(t("channel_no", lang), show_alert=True)
                    try:
                        await callback.message.edit_text(text, reply_markup=kb)
                    except Exception:
                        await callback.message.answer(text, reply_markup=kb)
                elif message:
                    await message.answer(text, reply_markup=kb)
                return None

        return await handler(event, data)
