from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from keyboards import admin_menu, e

router = Router()
ADMIN_ID = 8414329140  # Замени на свой ID


def tg_emoji(emoji_id: int, fallback: str) -> str:
    return f'<tg-emoji emoji-id="{emoji_id}">{fallback}</tg-emoji>'


@router.message(Command("admin"))
async def admin_panel(message: Message):
    if message.from_user.id != ADMIN_ID:
        return
    await message.answer(f"{tg_emoji(e(40), '🔧')} Админ-панель", reply_markup=admin_menu)


@router.callback_query(F.data == "admin_users")
async def admin_users(callback: CallbackQuery):
    await callback.answer("Список пользователей (пока пусто)")
