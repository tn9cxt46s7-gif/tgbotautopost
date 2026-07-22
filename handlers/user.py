from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart, CommandObject
from aiogram.fsm.context import FSMContext
from datetime import datetime

from keyboards import main_menu, profile_menu, back_to_menu_kb, settings_kb, cancel_kb
from database import (
    get_or_create_user, get_user, count_referrals, update_user_settings,
    user_has_tg_account, extend_subscription, mark_trial_used,
    count_user_ok_posts_since, get_user_ads, get_user_groups,
)
from utils.emoji import tg_emoji
from utils.subscription import has_active_subscription
from utils.antibot import safety_disclaimer
from services.user_client import mask_phone
from states import UserSettings
from config import TRIAL_DAYS, BOT_VERSION, SUPPORT_USERNAME, MIN_INTERVAL_MINUTES

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message, command: CommandObject, state: FSMContext):
    await state.clear()
    referrer_id = None
    if command.args and command.args.startswith("ref_"):
        raw = command.args.removeprefix("ref_")
        if raw.isdigit() and int(raw) != message.from_user.id:
            referrer_id = int(raw)

    user = await get_or_create_user(
        telegram_id=message.from_user.id,
        username=message.from_user.username,
        referrer_id=referrer_id,
    )

    if user.is_blocked:
        await message.answer(
            f"{tg_emoji('LOCK')} Аккаунт заблокирован.\n"
            f"Напиши @{SUPPORT_USERNAME}."
        )
        return

    await message.answer(
        f"{tg_emoji('WAVE')} <b>Автопост в барахолки Латвии</b> 🇱🇻 · v{BOT_VERSION}\n\n"
        f"{tg_emoji('USER')} Подключи аккаунт («Мой аккаунт»)\n"
        f"{tg_emoji('GROUPS')} Добавь LV-группы (Rīga, Daugavpils и др.)\n"
        f"{tg_emoji('ADS')} Создай объявление или «Шаблоны»\n"
        f"{tg_emoji('AUTO')} Включи автопостинг\n\n"
        "Посты идут <b>от твоего аккаунта</b>. Бот в группы не заходит.\n"
        f"Пробный день в профиле · саппорт @{SUPPORT_USERNAME}\n\n"
        "Меню ниже 👇",
        reply_markup=main_menu,
    )


async def build_profile_text(telegram_id: int, username: str | None) -> str:
    user = await get_user(telegram_id)
    if not user:
        user = await get_or_create_user(telegram_id, username)

    if has_active_subscription(user):
        sub_status = (
            f"{tg_emoji('OK')} активна до {user.subscription_end.strftime('%d.%m.%Y')} "
            f"({user.plan or '—'})"
        )
    else:
        sub_status = f"{tg_emoji('WARN')} не активна"

    refs = await count_referrals(telegram_id)
    ap = "вкл" if user.autopost_enabled else "выкл"
    if user_has_tg_account(user):
        acc = f"{tg_emoji('OK')} {user.tg_account_name or 'привязан'} ({mask_phone(user.tg_phone)})"
    else:
        acc = f"{tg_emoji('WARN')} не привязан"

    day_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    posts_today = await count_user_ok_posts_since(user.id, day_start)
    ads = await get_user_ads(user.id)
    groups = await get_user_groups(user.id)

    return (
        f"{tg_emoji('PROFILE')} <b>Твой профиль</b> · v{BOT_VERSION}\n\n"
        f"{tg_emoji('ID')} ID: <code>{telegram_id}</code>\n"
        f"{tg_emoji('USER')} Username: @{username or '—'}\n"
        f"{tg_emoji('LINK')} Аккаунт: {acc}\n"
        f"{tg_emoji('SUB')} Подписка: {sub_status}\n"
        f"{tg_emoji('AUTO')} Автопостинг: <b>{ap}</b>\n"
        f"{tg_emoji('ADS')} Объявлений: <b>{len(ads)}</b> · групп: <b>{len(groups)}</b>\n"
        f"{tg_emoji('FIRE')} Постов сегодня: <b>{posts_today}</b>\n"
        f"{tg_emoji('PEOPLE')} Приглашено друзей: <b>{refs}</b>\n"
    )


@router.message(F.text == "Профиль")
async def profile_handler(message: Message):
    text = await build_profile_text(message.from_user.id, message.from_user.username)
    await message.answer(text, reply_markup=profile_menu)


@router.callback_query(F.data == "back_to_profile")
async def back_to_profile(callback: CallbackQuery):
    text = await build_profile_text(callback.from_user.id, callback.from_user.username)
    await callback.message.edit_text(text, reply_markup=profile_menu)
    await callback.answer()


@router.callback_query(F.data == "trial_start")
async def trial_start(callback: CallbackQuery):
    user = await get_or_create_user(callback.from_user.id, callback.from_user.username)
    if has_active_subscription(user):
        await callback.answer("Подписка уже активна", show_alert=True)
        return
    if getattr(user, "trial_used", False):
        await callback.answer("Пробный день уже использован", show_alert=True)
        return
    await extend_subscription(callback.from_user.id, "trial", TRIAL_DAYS)
    await mark_trial_used(callback.from_user.id)
    await callback.answer("Пробный день активирован!", show_alert=True)
    text = await build_profile_text(callback.from_user.id, callback.from_user.username)
    try:
        await callback.message.edit_text(text, reply_markup=profile_menu)
    except Exception:
        pass
    await callback.message.answer(
        f"{tg_emoji('OK')} Пробный день на {TRIAL_DAYS} дн. активен.\n"
        "Лимит: 1 объявление, 2 группы.\n"
        "1) Мой аккаунт → подключи\n"
        "2) Добавь LV-барахолки (Rīga и др.)\n"
        "3) Создай объявление и включи автопостинг"
    )


@router.message(F.text == "Инструкция")
async def help_guide(message: Message):
    await message.answer(
        f"{tg_emoji('SUPPORT')} <b>Инструкция · v{BOT_VERSION}</b>\n\n"
        "1. Купи подписку или возьми пробный день (Профиль)\n"
        "2. «Мой аккаунт» — подключи Telegram\n"
        "3. «Мои группы» — выбери барахолки Латвии "
        "(Rīga, Daugavpils, Baltic Marketplace и т.п. — ты уже участник)\n"
        "4. «Добавить объявление» или «Шаблоны»\n"
        "5. «Автопостинг» → Запустить / Запостить сейчас\n\n"
        f"Интервал минимум {MIN_INTERVAL_MINUTES} мин — безопаснее для аккаунта.\n"
        f"Промо: START20 (−20%), SALE15, VIP30\n"
        f"Саппорт: @{SUPPORT_USERNAME}\n\n"
        + safety_disclaimer()
    )


@router.message(F.text == "Шаблоны")
async def show_templates(message: Message):
    from utils.templates import TEMPLATES
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    rows = [
        [InlineKeyboardButton(text=t["title"], callback_data=f"tpl_{key}")]
        for key, t in TEMPLATES.items()
    ]
    await message.answer(
        f"{tg_emoji('ADS')} <b>Шаблоны объявлений</b>\n"
        "Выбери нишу — получишь текст, который можно сразу править:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=rows),
    )


@router.callback_query(F.data.startswith("tpl_"))
async def send_template(callback: CallbackQuery):
    from utils.templates import TEMPLATES
    key = callback.data.removeprefix("tpl_")
    t = TEMPLATES.get(key)
    if not t:
        await callback.answer("Нет шаблона", show_alert=True)
        return
    await callback.message.answer(
        f"{t['title']}\n\n<code>{t['text']}</code>\n\n"
        "Скопируй → «Добавить объявление» → вставь и поправь."
    )
    await callback.answer()


@router.callback_query(F.data == "ref_menu")
async def referral_menu(callback: CallbackQuery):
    bot_info = await callback.bot.get_me()
    link = f"https://t.me/{bot_info.username}?start=ref_{callback.from_user.id}"
    refs = await count_referrals(callback.from_user.id)

    text = (
        f"{tg_emoji('REF')} <b>Реферальная программа</b>\n\n"
        "Приглашай друзей по своей ссылке — и получай "
        "<b>+3 дня подписки</b> за каждого, кто оплатит план.\n\n"
        f"{tg_emoji('PEOPLE')} Уже приглашено: <b>{refs}</b>\n\n"
        f"Твоя ссылка:\n<code>{link}</code>"
    )
    await callback.message.edit_text(text, reply_markup=back_to_menu_kb)
    await callback.answer()


@router.message(F.text == "Рефералка")
async def referral_menu_from_reply(message: Message):
    bot_info = await message.bot.get_me()
    link = f"https://t.me/{bot_info.username}?start=ref_{message.from_user.id}"
    refs = await count_referrals(message.from_user.id)

    text = (
        f"{tg_emoji('REF')} <b>Реферальная программа</b>\n\n"
        "Приглашай друзей по своей ссылке — и получай "
        "<b>+3 дня подписки</b> за каждого, кто оплатил план.\n\n"
        f"{tg_emoji('PEOPLE')} Уже приглашено: <b>{refs}</b>\n\n"
        f"Твоя ссылка:\n<code>{link}</code>"
    )
    await message.answer(text, reply_markup=back_to_menu_kb)


@router.message(F.text == "Настройки")
async def settings_menu(message: Message):
    user = await get_user(message.from_user.id)
    if not user:
        user = await get_or_create_user(message.from_user.id, message.from_user.username)
    text = (
        f"{tg_emoji('SETTINGS')} <b>Настройки</b>\n\n"
        f"{tg_emoji('CLOCK')} Интервал по умолчанию: <b>{user.default_interval}</b> мин\n"
        f"Тихие часы (UTC): <b>{user.quiet_hours_start:02d}:00–{user.quiet_hours_end:02d}:00</b>\n\n"
        "В тихие часы посты не уходят в группы."
    )
    await message.answer(text, reply_markup=settings_kb)


@router.callback_query(F.data == "set_interval")
async def set_interval_start(callback: CallbackQuery, state: FSMContext):
    await state.set_state(UserSettings.default_interval)
    await callback.message.answer(
        f"{tg_emoji('CLOCK')} Введи интервал по умолчанию в минутах (от 60 до 1440):",
        reply_markup=cancel_kb,
    )
    await callback.answer()


@router.message(UserSettings.default_interval)
async def set_interval_save(message: Message, state: FSMContext):
    if message.text == "Отмена":
        await state.clear()
        await message.answer("Отменено.", reply_markup=main_menu)
        return
    if not message.text or not message.text.isdigit():
        await message.answer("Нужно число минут, например 90.")
        return
    minutes = int(message.text)
    if minutes < 60 or minutes > 1440:
        await message.answer("Для защиты от бана: 60–1440 минут.")
        return
    await update_user_settings(message.from_user.id, default_interval=minutes)
    await state.clear()
    await message.answer(f"{tg_emoji('OK')} Интервал сохранён: {minutes} мин.", reply_markup=main_menu)


@router.callback_query(F.data == "set_quiet")
async def set_quiet_start(callback: CallbackQuery, state: FSMContext):
    await state.set_state(UserSettings.quiet_hours)
    await callback.message.answer(
        f"{tg_emoji('SETTINGS')} Введи тихие часы в формате <code>START-END</code> (UTC), например <code>0-6</code> или <code>23-7</code>.\n"
        "Чтобы отключить: <code>0-0</code>",
        reply_markup=cancel_kb,
    )
    await callback.answer()


@router.message(UserSettings.quiet_hours)
async def set_quiet_save(message: Message, state: FSMContext):
    if message.text == "Отмена":
        await state.clear()
        await message.answer("Отменено.", reply_markup=main_menu)
        return
    try:
        a, b = message.text.replace(" ", "").split("-")
        start, end = int(a), int(b)
        if not (0 <= start <= 23 and 0 <= end <= 23):
            raise ValueError
    except Exception:
        await message.answer("Формат: START-END, например 0-6")
        return
    await update_user_settings(message.from_user.id, quiet_hours_start=start, quiet_hours_end=end)
    await state.clear()
    await message.answer(f"{tg_emoji('OK')} Тихие часы: {start:02d}:00–{end:02d}:00 UTC", reply_markup=main_menu)


@router.message(F.text == "Отмена")
async def cancel_any(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Отменено.", reply_markup=main_menu)
