from fastapi import FastAPI, Request
from aiogram import Bot, Dispatcher, types
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from dotenv import load_dotenv
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

load_dotenv()

bot = Bot(
    token=os.getenv("BOT_TOKEN"),
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)
dp = Dispatcher()

from handlers.user import router as user_router
from handlers.admin import router as admin_router
from handlers.payments import router as payments_router
from database import init_db

dp.include_router(user_router)
dp.include_router(admin_router)
dp.include_router(payments_router)

app = FastAPI()


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
    return {"status": "bot is running"}
