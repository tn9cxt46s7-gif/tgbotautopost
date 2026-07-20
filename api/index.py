"""
Vercel serverless entrypoint (webhook mode).

Limits on free Vercel:
- Bot answers (commands/menus) work via webhook
- Autopost is weak: no always-on scheduler; cron on Hobby = 1/day max
- SQLite in /tmp resets between cold starts / instances
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# On Vercel use writable /tmp for SQLite unless DB_URL is already set
if os.getenv("VERCEL") and not os.getenv("DB_URL"):
    os.environ["DB_URL"] = "sqlite+aiosqlite:////tmp/bot.db"

from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, Request, Header, HTTPException
from aiogram import Bot, Dispatcher, types
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from config import BOT_TOKEN, is_admin
from handlers.user import router as user_router
from handlers.ads import router as ads_router
from handlers.groups import router as groups_router
from handlers.autopost import router as autopost_router
from handlers.support import router as support_router
from handlers.admin import router as admin_router
from handlers.payments import router as payments_router
from database import init_db

if not BOT_TOKEN:
    # Still create app so / returns a clear error instead of crash at import
    bot = None
    dp = None
else:
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
_db_ready = False


async def ensure_db():
    global _db_ready
    if not _db_ready:
        await init_db()
        _db_ready = True


@app.get("/")
async def root():
    return {
        "status": "ok" if BOT_TOKEN else "missing BOT_TOKEN",
        "hint": "Open /setup-webhook after setting env vars on Vercel",
    }


@app.get("/setup-webhook")
async def setup_webhook(request: Request):
    """Register Telegram webhook to this Vercel deployment."""
    if not BOT_TOKEN or bot is None:
        raise HTTPException(500, "BOT_TOKEN not set in Vercel Environment Variables")

    # Public URL of this deployment
    host = request.headers.get("x-forwarded-host") or request.headers.get("host")
    proto = request.headers.get("x-forwarded-proto", "https")
    base = f"{proto}://{host}"
    webhook_url = f"{base}/webhook"

    await bot.set_webhook(
        url=webhook_url,
        drop_pending_updates=True,
        allowed_updates=["message", "callback_query", "pre_checkout_query"],
    )
    info = await bot.get_webhook_info()
    return {
        "ok": True,
        "webhook_url": webhook_url,
        "telegram": {
            "url": info.url,
            "pending_update_count": info.pending_update_count,
            "last_error_message": info.last_error_message,
        },
        "next": "Write /start to your bot in Telegram",
    }


@app.post("/webhook")
async def telegram_webhook(request: Request):
    if not BOT_TOKEN or bot is None or dp is None:
        raise HTTPException(500, "BOT_TOKEN not set")

    await ensure_db()
    data = await request.json()
    update = types.Update.model_validate(data)
    await dp.feed_update(bot, update)
    return {"ok": True}


@app.get("/cron")
@app.post("/cron")
async def cron_autopost(
    request: Request,
    authorization: str | None = Header(default=None),
):
    """
    Optional autopost tick.
    Protect with CRON_SECRET env, or call from Vercel Cron.
    Free Hobby cron is once/day — not enough for real autopost.
    """
    if not BOT_TOKEN or bot is None:
        raise HTTPException(500, "BOT_TOKEN not set")

    secret = os.getenv("CRON_SECRET", "")
    # Vercel Cron sends Authorization: Bearer <CRON_SECRET> if configured;
    # also allow ?secret= for manual tests
    qsecret = request.query_params.get("secret", "")
    auth_ok = False
    if secret:
        if authorization == f"Bearer {secret}" or qsecret == secret:
            auth_ok = True
    else:
        # no secret set — allow (not ideal, but ok for first bring-up)
        auth_ok = True

    if not auth_ok:
        raise HTTPException(403, "Forbidden")

    await ensure_db()
    from services.poster import run_posting_cycle

    await run_posting_cycle(bot)
    return {"ok": True, "ran": "posting_cycle"}
