import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from config import BOT_TOKEN
from handlers.user import router as user_router
from handlers.ads import router as ads_router
from handlers.groups import router as groups_router
from handlers.account import router as account_router
from handlers.autopost import router as autopost_router
from handlers.support import router as support_router
from handlers.admin import router as admin_router
from handlers.payments import router as payments_router
from database import init_db
from services.scheduler import start_scheduler, stop_scheduler
from services.user_client import api_configured
from middlewares.access import AccessMiddleware

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher(storage=MemoryStorage())

dp.message.middleware(AccessMiddleware())
dp.callback_query.middleware(AccessMiddleware())

dp.include_router(user_router)
dp.include_router(account_router)
dp.include_router(ads_router)
dp.include_router(groups_router)
dp.include_router(autopost_router)
dp.include_router(support_router)
dp.include_router(payments_router)
dp.include_router(admin_router)


async def main():
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN is not set")
    if not api_configured():
        logger.warning(
            "TG_API_ID / TG_API_HASH not set — account linking and user-posting disabled. "
            "Get them at https://my.telegram.org"
        )
    await init_db()
    await bot.delete_webhook(drop_pending_updates=True)
    start_scheduler(bot)
    logger.info("Bot started (polling)")
    try:
        await dp.start_polling(bot)
    finally:
        stop_scheduler()


if __name__ == "__main__":
    asyncio.run(main())
