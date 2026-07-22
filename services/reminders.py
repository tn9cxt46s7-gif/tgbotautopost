"""Subscription expiry reminders."""

from __future__ import annotations

import logging

from aiogram import Bot

from config import SUB_REMIND_DAYS, SUPPORT_USERNAME
from database import users_needing_sub_reminder, mark_sub_reminded
from utils.emoji import tg_emoji

logger = logging.getLogger(__name__)


async def run_subscription_reminders(bot: Bot) -> int:
    users = await users_needing_sub_reminder(SUB_REMIND_DAYS)
    sent = 0
    for user in users:
        days_left = max(0, (user.subscription_end - __import__("datetime").datetime.utcnow()).days)
        try:
            await bot.send_message(
                user.telegram_id,
                f"{tg_emoji('WARN')} <b>Подписка скоро закончится</b>\n\n"
                f"Осталось ≈ <b>{days_left}</b> дн. "
                f"(до {user.subscription_end.strftime('%d.%m.%Y')}).\n\n"
                "Продли в «Подписка» — Stars / CryptoBot / карта.\n"
                "Промокоды: START20, SALE15\n"
                f"Саппорт: @{SUPPORT_USERNAME}",
            )
            await mark_sub_reminded(user.telegram_id)
            sent += 1
        except Exception:
            logger.exception("remind fail %s", user.telegram_id)
    return sent
