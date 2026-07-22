"""
Vercel serverless entrypoint (webhook mode).

Recommended setup for real posting on Vercel:
1. Postgres (Neon / Supabase / Vercel Postgres) → DB_URL or POSTGRES_URL
2. Env: BOT_TOKEN, ADMIN_IDS, TG_API_ID, TG_API_HASH, CRON_SECRET
3. Open /setup-webhook once after deploy
4. Autopost: Vercel Cron (Hobby = 1/day) OR external cron every 5–15 min → /cron?secret=...
5. Manual: «Запостить сейчас» in the bot (works immediately)
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# On Vercel use writable /tmp for SQLite unless DB_URL is already set
if os.getenv("VERCEL") and not os.getenv("DB_URL") and not os.getenv("POSTGRES_URL") and not os.getenv("DATABASE_URL"):
    os.environ["DB_URL"] = "sqlite+aiosqlite:////tmp/bot.db"

from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, Request, Header, HTTPException
from aiogram import Bot, Dispatcher, types
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from config import BOT_TOKEN, IS_VERCEL, TG_API_ID, DB_URL
from handlers.user import router as user_router
from handlers.account import router as account_router
from handlers.ads import router as ads_router
from handlers.groups import router as groups_router
from handlers.autopost import router as autopost_router
from handlers.support import router as support_router
from handlers.admin import router as admin_router
from handlers.payments import router as payments_router
from database import init_db
from services.user_client import api_configured
from middlewares.access import AccessMiddleware

if not BOT_TOKEN:
    # Still create app so / returns a clear error instead of crash at import
    bot = None
    dp = None
else:
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

app = FastAPI()
_db_ready = False


async def ensure_db():
    global _db_ready
    if not _db_ready:
        await init_db()
        _db_ready = True


def _db_kind() -> str:
    if "postgresql" in (DB_URL or "") or "asyncpg" in (DB_URL or ""):
        return "postgres"
    if "/tmp/" in (DB_URL or ""):
        return "sqlite_tmp_ephemeral"
    return "sqlite"


@app.get("/")
async def root():
    return {
        "status": "ok" if BOT_TOKEN else "missing BOT_TOKEN",
        "version": "2.3.0-eu",
        "vercel": IS_VERCEL,
        "db": _db_kind(),
        "tg_api": api_configured(),
        "cryptobot": bool(os.getenv("CRYPTO_BOT_TOKEN")),
        "hint": "Open /setup-webhook after setting env vars; use Postgres for production",
    }


@app.get("/health")
async def health():
    ok = bool(BOT_TOKEN)
    return {
        "ok": ok,
        "bot_token": bool(BOT_TOKEN),
        "tg_api_id": bool(TG_API_ID),
        "db": _db_kind(),
        "persistent_db": _db_kind() == "postgres",
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
        allowed_updates=["message", "callback_query", "pre_checkout_query", "my_chat_member"],
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
        "db": _db_kind(),
        "tg_api": api_configured(),
        "next": [
            "Write /start to your bot in Telegram",
            "Add groups (add bot as admin for normal groups)",
            "For flea markets: Мой аккаунт → по номеру",
            "Set external cron every 5–15 min to GET /cron?secret=CRON_SECRET",
        ],
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
    Autopost tick for serverless.
    Protect with CRON_SECRET. Call from Vercel Cron or external cron (cron-job.org).
    Free Hobby Vercel cron is once/day — use external cron every 5–15 min for real autopost.
    """
    if not BOT_TOKEN or bot is None:
        raise HTTPException(500, "BOT_TOKEN not set")

    secret = os.getenv("CRON_SECRET", "")
    qsecret = request.query_params.get("secret", "")
    auth_ok = False
    if secret:
        if authorization == f"Bearer {secret}" or qsecret == secret:
            auth_ok = True
    else:
        # no secret set — allow (bring-up); set CRON_SECRET in production
        auth_ok = True

    if not auth_ok:
        raise HTTPException(403, "Forbidden")

    await ensure_db()
    from services.poster import run_posting_cycle
    from services.reminders import run_subscription_reminders

    result = await run_posting_cycle(bot)
    reminded = await run_subscription_reminders(bot)
    return {"ok": True, "ran": "posting_cycle", "reminded": reminded, **(result or {})}


@app.post("/cryptobot-webhook")
async def cryptobot_webhook(request: Request):
    """
    Crypto Pay webhook. In @CryptoBot app set URL:
    https://YOUR.vercel.app/cryptobot-webhook
    """
    if not BOT_TOKEN or bot is None:
        raise HTTPException(500, "BOT_TOKEN not set")
    await ensure_db()
    data = await request.json()
    # Formats vary: {update_type, payload: invoice} or {invoice}
    update_type = data.get("update_type") or data.get("type")
    invoice = data.get("payload") if isinstance(data.get("payload"), dict) else data.get("invoice")
    if update_type and update_type != "invoice_paid" and not (invoice and invoice.get("status") == "paid"):
        # Sometimes body IS the invoice
        if data.get("status") == "paid" and data.get("invoice_id"):
            invoice = data
        else:
            return {"ok": True, "ignored": True}
    if not invoice:
        invoice = data if data.get("status") == "paid" else None
    if not invoice:
        return {"ok": True, "ignored": True}

    from handlers.payments import activate_from_cryptobot_webhook
    activated = await activate_from_cryptobot_webhook(bot, invoice)
    return {"ok": True, "activated": activated}
