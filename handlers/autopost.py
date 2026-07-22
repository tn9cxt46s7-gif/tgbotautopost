from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery

from keyboards import autopost_kb
from database import (
    get_or_create_user, get_user, set_autopost_enabled,
    get_user_ads, get_user_groups, user_has_tg_account,
)
from utils.emoji import tg_emoji
from utils.subscription import has_active_subscription
from services.poster import (
    run_posting_for_telegram_user,
    can_user_post,
    can_bot_post_group,
    can_post_anywhere,
)
from services.user_client import api_configured

router = Router()


async def build_autopost_text(telegram_id: int) -> tuple[str, bool]:
    user = await get_user(telegram_id)
    if not user:
        user = await get_or_create_user(telegram_id)
    ads = await get_user_ads(user.id)
    groups = await get_user_groups(user.id)
    active_ads = [a for a in ads if a.status == "active"]
    active_groups = [g for g in groups if g.active]
    linked = can_user_post(user)
    bot_groups = sum(1 for g in active_groups if can_bot_post_group(g))

    sub = "да" if has_active_subscription(user) else "нет"
    ready = bool(
        user.autopost_enabled
        and active_ads
        and active_groups
        and can_post_anywhere(user, active_groups)
    )
    status = "работает" if ready else "остановлен"
    if linked:
        acc = "аккаунт подключён ✅"
    elif bot_groups:
        acc = f"бот в {bot_groups} группе(ах) ✅"
    else:
        acc = "нет канала отправки — нужен аккаунт или бот в группе"

    text = (
        f"{tg_emoji('AUTO')} <b>Автопостинг</b>\n\n"
        f"Статус: <b>{status}</b>\n"
        f"Переключатель: <b>{'вкл' if user.autopost_enabled else 'выкл'}</b>\n"
        f"Подписка: <b>{sub}</b>\n"
        f"Канал: <b>{acc}</b>\n\n"
        f"{tg_emoji('ADS')} Активных объявлений: <b>{len(active_ads)}</b> / {len(ads)}\n"
        f"{tg_emoji('GROUPS')} Активных групп: <b>{len(active_groups)}</b> / {len(groups)}\n\n"
        "• Обычные группы: добавь бота админом → посты от бота (Vercel)\n"
        "• Барахолки без ботов: «Мой аккаунт» → номер или QR\n"
        "• «Запостить сейчас» шлёт сразу; cron на Vercel — по расписанию"
    )
    return text, user.autopost_enabled


@router.message(F.text == "Автопостинг")
async def autopost_menu(message: Message):
    text, enabled = await build_autopost_text(message.from_user.id)
    await message.answer(text, reply_markup=autopost_kb(enabled))


def _gate(user, groups) -> str | None:
    if not has_active_subscription(user):
        return "Нужна активная подписка"
    if can_post_anywhere(user, groups):
        return None
    if not api_configured() and not any(can_bot_post_group(g) for g in groups):
        return "Нет канала отправки: добавь бота в группу или настрой API"
    if not user_has_tg_account(user):
        return "Подключи аккаунт или добавь бота админом в группу"
    return "Нет канала отправки"


@router.callback_query(F.data == "ap_start")
async def ap_start(callback: CallbackQuery, bot: Bot):
    user = await get_or_create_user(callback.from_user.id, callback.from_user.username)
    groups = await get_user_groups(user.id)
    gate = _gate(user, groups)
    if gate:
        await callback.answer(gate, show_alert=True)
        return
    ads = await get_user_ads(user.id)
    if not any(g.active for g in groups):
        await callback.answer("Сначала добавь группу", show_alert=True)
        return
    if not any(a.status == "active" for a in ads):
        await callback.answer("Сначала запусти объявление", show_alert=True)
        return

    await set_autopost_enabled(callback.from_user.id, True)
    text, enabled = await build_autopost_text(callback.from_user.id)
    await callback.message.edit_text(text, reply_markup=autopost_kb(enabled))
    await callback.answer("Автопостинг включён")

    result = await run_posting_for_telegram_user(bot, callback.from_user.id, force=True)
    if result["ok"] > 0:
        await bot.send_message(
            callback.from_user.id,
            f"{tg_emoji('OK')} Запостил в группы: <b>{result['ok']}</b>",
        )
    elif result.get("reason") == "send_failed":
        await bot.send_message(
            callback.from_user.id,
            f"{tg_emoji('WARN')} Включить смог, но сейчас не ушло. "
            "Проверь доступ к группам. Cron/«Запостить сейчас» попробуют снова.",
        )


@router.callback_query(F.data == "ap_now")
async def ap_now(callback: CallbackQuery, bot: Bot):
    user = await get_or_create_user(callback.from_user.id, callback.from_user.username)
    groups = await get_user_groups(user.id)
    gate = _gate(user, groups)
    if gate:
        await callback.answer(gate, show_alert=True)
        return
    await callback.answer("Постю в группы…")
    result = await run_posting_for_telegram_user(bot, callback.from_user.id, force=True)
    if result["ok"] > 0:
        await bot.send_message(
            callback.from_user.id,
            f"{tg_emoji('OK')} Ушло в группы: <b>{result['ok']}</b>",
        )
    else:
        reason = {
            "no_ads": "Нет активных объявлений",
            "no_groups": "Нет групп",
            "no_channel": "Нет канала: подключи аккаунт или добавь бота в группу",
            "no_account": "Подключи аккаунт",
            "no_api": "Сервис настраивается — напиши в поддержку",
            "send_failed": "Не смог написать. Бот админ в группе? Или аккаунт участник барахолки?",
        }.get(result.get("reason") or "", "Не удалось отправить")
        await bot.send_message(callback.from_user.id, f"{tg_emoji('WARN')} {reason}")


@router.callback_query(F.data == "ap_stop")
async def ap_stop(callback: CallbackQuery):
    await set_autopost_enabled(callback.from_user.id, False)
    text, enabled = await build_autopost_text(callback.from_user.id)
    await callback.message.edit_text(text, reply_markup=autopost_kb(enabled))
    await callback.answer("Автопостинг выключен")
