from fastapi import FastAPI, Request
from aiogram import Bot, Dispatcher, types
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from dotenv import load_dotenv
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

load_dotenv()

from config import BOT_TOKEN  # noqa: E402
from handlers.user import router as user_router  # noqa: E402
from handlers.ads import router as ads_router  # noqa: E402
from handlers.groups import router as groups_router  # noqa: E402
from handlers.autopost import router as autopost_router  # noqa: E402
from handlers.support import router as support_router  # noqa: E402
from handlers.admin import router as admin_router  # noqa: E402
from handlers.payments import router as payments_router  # noqa: E402
from database import init_db  # noqa: E402

bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher(storage=MemoryStorage())

dp.include_router(user_router)
dp.include_router(ads_router)
dp.include_router(groups_router)
dp.include_router(autopost_router)
dp.include_router(support_router)
dp.include_router(payments_router)
dp.include_router(admin_router)

app = FastAPI()

# Note: APScheduler / long-running autopost does NOT run reliably on Vercel serverless.
# Use polling (main.py) or a always-on host (Railway/Heroku/VPS) for autopost.


@app.on_event("startup")
async def on_startup():
    await init_db()


@app.post("/webhook")
async def webhook(request: Request):
    data = await request.json()
    update = types.Update(**data)
    await dp.feed_update(bot, update)
    return {"ok": True}


@app.get("/")
async def root():
    return {
        "status": "bot is running",
        "note": "Autopost scheduler requires polling (main.py), not serverless webhook alone",
    }
