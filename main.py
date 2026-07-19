import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from dotenv import load_dotenv
import os
from fastapi import FastAPI
import uvicorn

load_dotenv()

bot = Bot(token=os.getenv("BOT_TOKEN"), default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()

# Здесь подключай routers как раньше

app = FastAPI()

@app.post("/webhook")
async def webhook(request: dict):
    update = types.Update(**request)
    await dp.feed_update(bot, update)
    return {"status": "ok"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
