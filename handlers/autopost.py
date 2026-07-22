from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery

from utils.i18n import all_btn
from keyboards import autopost_kb
from database import (
    get_or_create_user, get_user, set_autopost_enabled,
    get_user_ads, get_user_groups, user_has_tg_account,
)
from utils.emoji import tg_emoji
from utils.subscription import has_active_subscription
from utils.antibot import safety_disclaimer
from services.poster import run_posting_for_telegram_user, can_user_post
from services.user_client import api_configured
from config import (
    MIN_INTERVAL_MINUTES,
    MAX_POSTS_PER_GROUP_PER_DAY,
    MAX_POSTS_PER_USER_PER_DAY,
)

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

    sub = "да" if has_active_subscription(user) else "нет"
    ready = bool(user.autopost_enabled and active_ads and active_groups and linked)
    status = "работает" if ready else "остановлен"
    acc = "подключён ✅" if linked else "не подключён — нужен вход"

    text = (
        f"{tg_emoji('AUTO')} <b>Автопостинг</b>\n\n"
        f"Статус: <b>{status}</b>\n"
        f"Переключатель: <b>{'вкл' if user.autopost_enabled else 'выкл'}</b>\n"
        f"Подписка: <b>{sub}</b>\n"
        f"Аккаунт: <b>{acc}</b>\n\n"
        f"{tg_emoji('ADS')} Активных объявлений: <b>{len(active_ads)}</b> / {len(ads)}\n"
        f"{tg_emoji('GROUPS')} Активных групп: <b>{len(active_groups)}</b> / {len(groups)}\n\n"
        f"Антибан: интервал ≥{MIN_INTERVAL_MINUTES} мин, "
        f"≤{MAX_POSTS_PER_GROUP_PER_DAY}/сутки на группу, "
        f"≤{MAX_POSTS_PER_USER_PER_DAY}/сутки всего.\n"
        "Посты только <b>от твоего аккаунта</b> в LV-барахолки — бот туда не заходит.\n"
        "100% защиты от бана нет; снижаем риск правилами и паузами."
    )
    return text, user.autopost_enabled


@router.message(F.text.in_(all_btn("autopost")))
async def autopost_menu(message: Message):
    text, enabled = await build_autopost_text(message.from_user.id)
    await message.answer(text, reply_markup=autopost_kb(enabled))
    await message.answer(safety_disclaimer())


def _gate(user) -> str | None:
    if not has_active_subscription(user):
        return "Нужна активная подписка"
    if not api_configured():
        return "Сервис ещё настраивается (API). Напиши в поддержку."
    if not user_has_tg_account(user):
        return "Сначала «Мой аккаунт» → подключи Telegram"
    return None


@router.callback_query(F.data == "ap_start")
async def ap_start(callback: CallbackQuery, bot: Bot):
    user = await get_or_create_user(callback.from_user.id, callback.from_user.username)
    gate = _gate(user)
    if gate:
        await callback.answer(gate, show_alert=True)
        return
    groups = await get_user_groups(user.id)
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
            f"{tg_emoji('OK')} Запостил: <b>{result['ok']}</b> "
            f"(пропущено антибаном: {result['skip']})",
        )
    elif result.get("reason") == "rate_limited":
        await bot.send_message(
            callback.from_user.id,
            f"{tg_emoji('WARN')} Включил, но сейчас рано слать снова "
            "(антибан: интервал / лимит суток). Подождите или дождитесь cron.",
        )
    elif result.get("reason") == "bad_content":
        await bot.send_message(
            callback.from_user.id,
            f"{tg_emoji('WARN')} Текст объявления похож на спам: {result.get('error')}",
        )
    elif result.get("reason") == "send_failed":
        await bot.send_message(
            callback.from_user.id,
            f"{tg_emoji('WARN')} Включить смог, но сейчас не ушло. "
            "Проверь, что ты участник этих барахолок.",
        )


@router.callback_query(F.data == "ap_now")
async def ap_now(callback: CallbackQuery, bot: Bot):
    user = await get_or_create_user(callback.from_user.id, callback.from_user.username)
    gate = _gate(user)
    if gate:
        await callback.answer(gate, show_alert=True)
        return
    await callback.answer("Постю от твоего аккаунта…")
    result = await run_posting_for_telegram_user(bot, callback.from_user.id, force=True)
    if result["ok"] > 0:
        await bot.send_message(
            callback.from_user.id,
            f"{tg_emoji('OK')} Ушло: <b>{result['ok']}</b> "
            f"(пропущено антибаном: {result['skip']})",
        )
    else:
        reason = {
            "no_ads": "Нет активных объявлений",
            "no_groups": "Нет групп",
            "no_account": "Подключи аккаунт в «Мой аккаунт»",
            "no_api": "Сервис настраивается — напиши в поддержку",
            "rate_limited": (
                "Антибан: слишком рано или дневной лимит. "
                "Так мы бережём аккаунт от бана в барахолке."
            ),
            "bad_content": f"Текст похож на спам: {result.get('error') or ''}",
            "send_failed": "Не смог написать. Ты участник этих барахолок?",
        }.get(result.get("reason") or "", "Не удалось отправить")
        await bot.send_message(callback.from_user.id, f"{tg_emoji('WARN')} {reason}")


@router.callback_query(F.data == "ap_stop")
async def ap_stop(callback: CallbackQuery):
    await set_autopost_enabled(callback.from_user.id, False)
    text, enabled = await build_autopost_text(callback.from_user.id)
    await callback.message.edit_text(text, reply_markup=autopost_kb(enabled))
    await callback.answer("Автопостинг выключен")
