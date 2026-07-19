from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command
from keyboards import main_menu

router = Router()

@router.message(Command("start"))
async def cmd_start(message: Message):
    await message.answer(
        "👋 Добро пожаловать в бота автопостинга!\n\n"
        "Для работы нужна активная подписка.",
        reply_markup=main_menu
    )

@router.message(F.text == "📝 Мои объявления")
async def my_ads(message: Message):
    await message.answer("Пока нет объявлений. Используй '➕ Добавить объявление'")

# Добавляй остальные handlers по мере необходимости
