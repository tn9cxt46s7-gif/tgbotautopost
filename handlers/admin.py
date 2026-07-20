from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from keyboards import admin_menu

router = Router()

ADMIN_ID = 8414329140  # Замени на свой ID

@router.message(Command("admin"))
async def admin_panel(message: Message):
    if message.from_user.id != ADMIN_ID:
        return
    await message.answer("🔧 Админ-панель", reply_markup=admin_menu)

@router.callback_query(F.data == "admin_users")
async def admin_users(callback: CallbackQuery):
    await callback.answer("Список пользователей (пока пусто)")
