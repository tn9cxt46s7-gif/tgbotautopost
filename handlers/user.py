from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart, CommandObject, Command
from aiogram.fsm.context import FSMContext
from datetime import datetime

from keyboards import (
    main_menu_kb, profile_menu_kb, back_to_menu_kb_for, settings_kb,
    cancel_kb_for, language_kb, channel_gate_kb,
)
from database import (
    get_or_create_user, get_user, count_referrals, update_user_settings,
    user_has_tg_account, extend_subscription, mark_trial_used,
    count_user_ok_posts_since, get_user_ads, get_user_groups,
    set_user_language,
)
from utils.emoji import tg_emoji
from utils.subscription import has_active_subscription
from utils.antibot import safety_disclaimer
from utils.i18n import t, all_btn, btn, LANGS
from utils.channel import is_subscribed, channel_configured
from services.user_client import mask_phone
from states import UserSettings
from config import TRIAL_DAYS, BOT_VERSION, SUPPORT_USERNAME, MIN_INTERVAL_MINUTES
from handlers.payments import price_list_text, _plans_kb_with_promo

router = Router()


async def _lang(telegram_id: int) -> str:
    user = await get_user(telegram_id)
    return (user.language if user and user.language else "ru")


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
        lang = user.language or "ru"
        await message.answer(t("blocked", lang, support=SUPPORT_USERNAME))
        return

    # 1) Language first
    if not user.language:
        await message.answer(t("choose_lang", "en"), reply_markup=language_kb())
        return

    lang = user.language

    # 2) Channel gate
    if channel_configured():
        ok = await is_subscribed(message.bot, message.from_user.id)
        if not ok:
            await message.answer(
                t("channel_required", lang),
                reply_markup=channel_gate_kb(lang),
            )
            return

    # 3) Welcome + mandatory subscription menu
    await message.answer(
        t("welcome", lang, version=BOT_VERSION, support=SUPPORT_USERNAME),
        reply_markup=main_menu_kb(lang),
    )
    await message.answer(
        price_list_text(0, None, lang),
        reply_markup=_plans_kb_with_promo(lang),
    )


@router.message(Command("lang", "language"))
@router.message(F.text.in_(all_btn("language")))
async def lang_menu_msg(message: Message):
    await message.answer(t("choose_lang", await _lang(message.from_user.id)), reply_markup=language_kb())


@router.callback_query(F.data == "lang_menu")
async def lang_menu_cb(callback: CallbackQuery):
    await callback.message.edit_text(
        t("choose_lang", await _lang(callback.from_user.id)),
        reply_markup=language_kb(),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("lang_"))
async def set_lang(callback: CallbackQuery, state: FSMContext):
    code = callback.data.removeprefix("lang_")
    if code not in LANGS:
        await callback.answer("?", show_alert=True)
        return
    await get_or_create_user(callback.from_user.id, callback.from_user.username)
    await set_user_language(callback.from_user.id, code)
    await callback.answer()
    await callback.message.edit_text(t("lang_saved", code))

    # Continue onboarding: channel → subscription
    if channel_configured():
        ok = await is_subscribed(callback.bot, callback.from_user.id)
        if not ok:
            await callback.message.answer(
                t("channel_required", code),
                reply_markup=channel_gate_kb(code),
            )
            return

    await callback.message.answer(
        t("welcome", code, version=BOT_VERSION, support=SUPPORT_USERNAME),
        reply_markup=main_menu_kb(code),
    )
    await callback.message.answer(
        price_list_text(0, None, code),
        reply_markup=_plans_kb_with_promo(code),
    )


@router.callback_query(F.data == "channel_check")
async def channel_check(callback: CallbackQuery):
    lang = await _lang(callback.from_user.id)
    ok = await is_subscribed(callback.bot, callback.from_user.id)
    if not ok:
        await callback.answer(t("channel_no", lang), show_alert=True)
        return
    await callback.answer(t("channel_ok", lang), show_alert=True)
    try:
        await callback.message.edit_text(t("channel_ok", lang))
    except Exception:
        pass
    await callback.message.answer(
        t("welcome", lang, version=BOT_VERSION, support=SUPPORT_USERNAME),
        reply_markup=main_menu_kb(lang),
    )
    await callback.message.answer(
        price_list_text(0, None, lang),
        reply_markup=_plans_kb_with_promo(lang),
    )


async def build_profile_text(telegram_id: int, username: str | None) -> str:
    user = await get_user(telegram_id)
    if not user:
        user = await get_or_create_user(telegram_id, username)
    lang = user.language or "ru"

    if has_active_subscription(user):
        sub_status = (
            f"{tg_emoji('OK')} до {user.subscription_end.strftime('%d.%m.%Y')} "
            f"({user.plan or '—'})"
        )
    else:
        sub_status = f"{tg_emoji('WARN')} —"

    refs = await count_referrals(telegram_id)
    ap = "ON" if user.autopost_enabled else "OFF"
    if user_has_tg_account(user):
        acc = f"{tg_emoji('OK')} {user.tg_account_name or 'OK'} ({mask_phone(user.tg_phone)})"
    else:
        acc = f"{tg_emoji('WARN')} —"

    day_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    posts_today = await count_user_ok_posts_since(user.id, day_start)
    ads = await get_user_ads(user.id)
    groups = await get_user_groups(user.id)

    headers = {
        "ru": "Твой профиль",
        "en": "Your profile",
        "lt": "Tavo profilis",
        "et": "Sinu profiil",
    }
    return (
        f"{tg_emoji('PROFILE')} <b>{headers.get(lang, headers['ru'])}</b> · v{BOT_VERSION}\n\n"
        f"{tg_emoji('ID')} ID: <code>{telegram_id}</code>\n"
        f"{tg_emoji('USER')} @{username or '—'}\n"
        f"{tg_emoji('LINK')} {acc}\n"
        f"{tg_emoji('SUB')} {sub_status}\n"
        f"{tg_emoji('AUTO')} {ap}\n"
        f"{tg_emoji('ADS')} ads: <b>{len(ads)}</b> · groups: <b>{len(groups)}</b>\n"
        f"{tg_emoji('FIRE')} today: <b>{posts_today}</b>\n"
        f"{tg_emoji('PEOPLE')} refs: <b>{refs}</b>\n"
        f"🌍 {lang.upper()}"
    )


@router.message(F.text.in_(all_btn("profile")))
async def profile_handler(message: Message):
    lang = await _lang(message.from_user.id)
    text = await build_profile_text(message.from_user.id, message.from_user.username)
    await message.answer(text, reply_markup=profile_menu_kb(lang))


@router.callback_query(F.data == "back_to_profile")
async def back_to_profile(callback: CallbackQuery):
    lang = await _lang(callback.from_user.id)
    text = await build_profile_text(callback.from_user.id, callback.from_user.username)
    await callback.message.edit_text(text, reply_markup=profile_menu_kb(lang))
    await callback.answer()


@router.callback_query(F.data == "trial_start")
async def trial_start(callback: CallbackQuery):
    lang = await _lang(callback.from_user.id)
    user = await get_or_create_user(callback.from_user.id, callback.from_user.username)
    if has_active_subscription(user):
        await callback.answer("OK", show_alert=True)
        return
    if getattr(user, "trial_used", False):
        await callback.answer("Trial used", show_alert=True)
        return
    await extend_subscription(callback.from_user.id, "trial", TRIAL_DAYS)
    await mark_trial_used(callback.from_user.id)
    await callback.answer("Trial ON", show_alert=True)
    text = await build_profile_text(callback.from_user.id, callback.from_user.username)
    try:
        await callback.message.edit_text(text, reply_markup=profile_menu_kb(lang))
    except Exception:
        pass
    await callback.message.answer(
        f"{tg_emoji('OK')} Trial {TRIAL_DAYS}d · 1 ad, 2 groups\n"
        f"@{SUPPORT_USERNAME}"
    )


@router.message(F.text.in_(all_btn("guide")))
async def help_guide(message: Message):
    await message.answer(
        f"{tg_emoji('SUPPORT')} <b>Guide · v{BOT_VERSION}</b>\n\n"
        "1. Subscription / trial\n"
        "2. My account → link Telegram\n"
        "3. My groups → Latvia markets\n"
        "4. Add ad / Templates\n"
        "5. Autopost → Start\n\n"
        f"Min interval {MIN_INTERVAL_MINUTES} min\n"
        f"Promo: START20, SALE15, VIP30\n"
        f"@{SUPPORT_USERNAME}\n\n"
        + safety_disclaimer()
    )


@router.message(F.text.in_(all_btn("templates")))
async def show_templates(message: Message):
    from utils.templates import TEMPLATES
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    rows = [
        [InlineKeyboardButton(text=t["title"], callback_data=f"tpl_{key}")]
        for key, t in TEMPLATES.items()
    ]
    await message.answer(
        f"{tg_emoji('ADS')} <b>Templates</b>",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=rows),
    )


@router.callback_query(F.data.startswith("tpl_"))
async def send_template(callback: CallbackQuery):
    from utils.templates import TEMPLATES
    key = callback.data.removeprefix("tpl_")
    tpl = TEMPLATES.get(key)
    if not tpl:
        await callback.answer("—", show_alert=True)
        return
    await callback.message.answer(f"{tpl['title']}\n\n<code>{tpl['text']}</code>")
    await callback.answer()


@router.callback_query(F.data == "ref_menu")
async def referral_menu(callback: CallbackQuery):
    lang = await _lang(callback.from_user.id)
    bot_info = await callback.bot.get_me()
    link = f"https://t.me/{bot_info.username}?start=ref_{callback.from_user.id}"
    refs = await count_referrals(callback.from_user.id)
    text = (
        f"{tg_emoji('REF')} <b>Referral</b>\n\n"
        f"+3 days per paid friend\n"
        f"Refs: <b>{refs}</b>\n\n"
        f"<code>{link}</code>"
    )
    await callback.message.edit_text(text, reply_markup=back_to_menu_kb_for(lang))
    await callback.answer()


@router.message(F.text.in_(all_btn("ref")))
async def referral_menu_from_reply(message: Message):
    lang = await _lang(message.from_user.id)
    bot_info = await message.bot.get_me()
    link = f"https://t.me/{bot_info.username}?start=ref_{message.from_user.id}"
    refs = await count_referrals(message.from_user.id)
    text = (
        f"{tg_emoji('REF')} <b>Referral</b>\n\n"
        f"+3 days per paid friend\n"
        f"Refs: <b>{refs}</b>\n\n"
        f"<code>{link}</code>"
    )
    await message.answer(text, reply_markup=back_to_menu_kb_for(lang))


@router.message(F.text.in_(all_btn("settings")))
async def settings_menu(message: Message):
    user = await get_user(message.from_user.id)
    if not user:
        user = await get_or_create_user(message.from_user.id, message.from_user.username)
    text = (
        f"{tg_emoji('SETTINGS')} <b>Settings</b>\n\n"
        f"Interval: <b>{user.default_interval}</b> min\n"
        f"Quiet UTC: <b>{user.quiet_hours_start:02d}:00–{user.quiet_hours_end:02d}:00</b>\n"
        f"Lang: <b>{(user.language or 'ru').upper()}</b>"
    )
    await message.answer(text, reply_markup=settings_kb)


@router.callback_query(F.data == "set_interval")
async def set_interval_start(callback: CallbackQuery, state: FSMContext):
    lang = await _lang(callback.from_user.id)
    await state.set_state(UserSettings.default_interval)
    await callback.message.answer(
        f"{tg_emoji('CLOCK')} Interval minutes (60–1440):",
        reply_markup=cancel_kb_for(lang),
    )
    await callback.answer()


@router.message(UserSettings.default_interval)
async def set_interval_save(message: Message, state: FSMContext):
    lang = await _lang(message.from_user.id)
    if message.text in all_btn("cancel"):
        await state.clear()
        await message.answer("OK", reply_markup=main_menu_kb(lang))
        return
    if not message.text or not message.text.isdigit():
        await message.answer("60–1440")
        return
    minutes = int(message.text)
    if minutes < 60 or minutes > 1440:
        await message.answer("60–1440")
        return
    await update_user_settings(message.from_user.id, default_interval=minutes)
    await state.clear()
    await message.answer(f"{tg_emoji('OK')} {minutes} min", reply_markup=main_menu_kb(lang))


@router.callback_query(F.data == "set_quiet")
async def set_quiet_start(callback: CallbackQuery, state: FSMContext):
    lang = await _lang(callback.from_user.id)
    await state.set_state(UserSettings.quiet_hours)
    await callback.message.answer(
        f"{tg_emoji('SETTINGS')} Quiet hours UTC: <code>START-END</code> e.g. <code>0-6</code>",
        reply_markup=cancel_kb_for(lang),
    )
    await callback.answer()


@router.message(UserSettings.quiet_hours)
async def set_quiet_save(message: Message, state: FSMContext):
    lang = await _lang(message.from_user.id)
    if message.text in all_btn("cancel"):
        await state.clear()
        await message.answer("OK", reply_markup=main_menu_kb(lang))
        return
    try:
        a, b = message.text.replace(" ", "").split("-")
        start, end = int(a), int(b)
        if not (0 <= start <= 23 and 0 <= end <= 23):
            raise ValueError
    except Exception:
        await message.answer("START-END, e.g. 0-6")
        return
    await update_user_settings(message.from_user.id, quiet_hours_start=start, quiet_hours_end=end)
    await state.clear()
    await message.answer(
        f"{tg_emoji('OK')} {start:02d}:00–{end:02d}:00 UTC",
        reply_markup=main_menu_kb(lang),
    )


@router.message(F.text.in_(all_btn("cancel")))
async def cancel_any(message: Message, state: FSMContext):
    lang = await _lang(message.from_user.id)
    await state.clear()
    await message.answer("OK", reply_markup=main_menu_kb(lang))
