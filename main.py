import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from dotenv import load_dotenv
import os

load_dotenv()

from bot.handlers.user import router as user_router
from bot.handlers.admin import router as admin_router
from bot.database import init_db
from bot.services.scheduler import start_scheduler

bot = Bot(token=os.getenv("BOT_TOKEN"), default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()

dp.include_router(user_router)
dp.include_router(admin_router)

async def main():
    await init_db()
    start_scheduler(bot)
    logging.basicConfig(level=logging.INFO)
    print("✅ Бот запущен")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())