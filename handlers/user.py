from datetime import datetime
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart, CommandObject

from keyboards import main_menu, profile_menu, back_to_menu_kb
from database import get_or_create_user, get_user, count_referrals

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message, command: CommandObject):
    referrer_id = None
    if command.args and command.args.startswith("ref_"):
        raw = command.args.removeprefix("ref_")
        if raw.isdigit() and int(raw) != message.from_user.id:
            referrer_id = int(raw)

    await get_or_create_user(
        telegram_id=message.from_user.id,
        username=message.from_user.username,
        referrer_id=referrer_id,
    )

    await message.answer(
        "👋 <b>Добро пожаловать в бота автопостинга!</b>\n\n"
        "🚀 Автоматическая публикация объявлений в твои группы\n"
        "💎 Гибкая система подписки\n"
        "🔗 Реферальная программа с бонусами\n\n"
        "Выбирай раздел в меню ниже 👇",
        reply_markup=main_menu
    )


async def build_profile_text(telegram_id: int, username: str | None) -> str:
    user = await get_user(telegram_id)
    if not user:
        user = await get_or_create_user(telegram_id, username)

    now = datetime.utcnow()
    if user.subscription_end and user.subscription_end > now:
        sub_status = f"✅ активна до {user.subscription_end.strftime('%d.%m.%Y')}"
    else:
        sub_status = "❌ не активна"

    refs = await count_referrals(telegram_id)

    return (
        "👤 <b>Твой профиль</b>\n\n"
        f"🆔 ID: <code>{telegram_id}</code>\n"
        f"🔖 Username: @{username or '—'}\n"
        f"💎 Подписка: {sub_status}\n"
        f"👥 Приглашено друзей: <b>{refs}</b>\n"
    )


@router.message(F.text == "👤 Профиль")
async def profile_handler(message: Message):
    text = await build_profile_text(message.from_user.id, message.from_user.username)
    await message.answer(text, reply_markup=profile_menu)


@router.callback_query(F.data == "back_to_profile")
async def back_to_profile(callback: CallbackQuery):
    text = await build_profile_text(callback.from_user.id, callback.from_user.username)
    await callback.message.edit_text(text, reply_markup=profile_menu)
    await callback.answer()


@router.callback_query(F.data == "ref_menu")
async def referral_menu(callback: CallbackQuery):
    bot_info = await callback.bot.get_me()
    link = f"https://t.me/{bot_info.username}?start=ref_{callback.from_user.id}"
    refs = await count_referrals(callback.from_user.id)

    text = (
        "🔗 <b>Реферальная программа</b>\n\n"
        "Приглашай друзей по своей ссылке — и получай "
        "<b>+3 дня подписки</b> за каждого, кто оплатит план.\n\n"
        f"👥 Уже приглашено: <b>{refs}</b>\n\n"
        f"Твоя ссылка:\n<code>{link}</code>"
    )
    await callback.message.edit_text(text, reply_markup=back_to_menu_kb)
    await callback.answer()


@router.message(F.text == "📝 Мои объявления")
async def my_ads(message: Message):
    await message.answer("📭 Пока нет объявлений. Нажми «➕ Добавить объявление», чтобы создать первое.")


@router.message(F.text == "➕ Добавить объявление")
async def add_ad(message: Message):
    await message.answer("✍️ Функция добавления объявлений скоро будет доступна.")


@router.message(F.text == "👥 Мои группы")
async def my_groups(message: Message):
    await message.answer("📭 Группы для автопостинга пока не добавлены.")


@router.message(F.text == "🚀 Автопостинг")
async def autopost_menu(message: Message):
    await message.answer("🚀 Раздел автопостинга в разработке — скоро здесь можно будет запускать рассылку по группам.")


@router.message(F.text == "⚙️ Настройки")
async def settings_menu(message: Message):
    await message.answer("⚙️ Настройки скоро появятся здесь.")
