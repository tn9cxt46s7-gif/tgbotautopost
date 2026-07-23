"""
Vercel serverless entrypoint (webhook mode).

Env required for production:
  BOT_TOKEN, DB_URL/POSTGRES_URL, CRON_SECRET (or WEBHOOK_SECRET),
  CRYPTO_BOT_TOKEN, TG_API_ID, TG_API_HASH, ADMIN_IDS
"""

from __future__ import annotations

import hashlib
import hmac
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

if os.getenv("VERCEL") and not os.getenv("DB_URL") and not os.getenv("POSTGRES_URL") and not os.getenv("DATABASE_URL"):
    os.environ["DB_URL"] = "sqlite+aiosqlite:////tmp/bot.db"

from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, Request, Header, HTTPException
from aiogram import Bot, Dispatcher, types
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from config import BOT_TOKEN, IS_VERCEL, TG_API_ID, DB_URL, WEBHOOK_SECRET, SETUP_SECRET
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


def _check_setup_secret(request: Request) -> None:
    secret = SETUP_SECRET or WEBHOOK_SECRET or os.getenv("CRON_SECRET", "")
    if not secret:
        raise HTTPException(403, "Set SETUP_SECRET or CRON_SECRET before /setup-webhook")
    q = request.query_params.get("secret", "")
    if q != secret:
        raise HTTPException(403, "Forbidden — use /setup-webhook?secret=YOUR_SECRET")


def _verify_telegram_secret(request: Request) -> None:
    """Telegram sends X-Telegram-Bot-Api-Secret-Token when secret_token was set."""
    if not WEBHOOK_SECRET:
        # Bring-up without secret — allow but warn via response logs
        return
    got = request.headers.get("x-telegram-bot-api-secret-token", "")
    if not hmac.compare_digest(got, WEBHOOK_SECRET):
        raise HTTPException(403, "Invalid webhook secret")


def _verify_cryptobot_signature(body: bytes, signature: str | None) -> bool:
    """Crypto Pay: HMAC-SHA-256(body, token) hex digest in crypto-pay-api-signature."""
    token = os.getenv("CRYPTO_BOT_TOKEN", "")
    if not token:
        return False
    if not signature:
        return False
    digest = hmac.new(token.encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(digest, signature)


@app.get("/")
async def root():
    return {
        "status": "ok" if BOT_TOKEN else "missing BOT_TOKEN",
        "version": "2.3.4-eu",
        "vercel": IS_VERCEL,
        "db": _db_kind(),
        "tg_api": api_configured(),
        "cryptobot": bool(os.getenv("CRYPTO_BOT_TOKEN")),
        "webhook_secret": bool(WEBHOOK_SECRET),
        "hint": "Open /setup-webhook?secret=CRON_SECRET after setting env vars",
    }


@app.get("/health")
async def health():
    return {
        "ok": bool(BOT_TOKEN),
        "bot_token": bool(BOT_TOKEN),
        "tg_api_id": bool(TG_API_ID),
        "db": _db_kind(),
        "persistent_db": _db_kind() == "postgres",
    }


@app.get("/setup-webhook")
async def setup_webhook(request: Request):
    """Register Telegram webhook. Requires ?secret=SETUP_SECRET|CRON_SECRET."""
    if not BOT_TOKEN or bot is None:
        raise HTTPException(500, "BOT_TOKEN not set in Vercel Environment Variables")
    _check_setup_secret(request)

    host = request.headers.get("x-forwarded-host") or request.headers.get("host")
    proto = request.headers.get("x-forwarded-proto", "https")
    base = f"{proto}://{host}"
    webhook_url = f"{base}/webhook"

    kwargs = dict(
        url=webhook_url,
        drop_pending_updates=True,
        allowed_updates=["message", "callback_query", "pre_checkout_query", "my_chat_member"],
    )
    if WEBHOOK_SECRET:
        kwargs["secret_token"] = WEBHOOK_SECRET

    await bot.set_webhook(**kwargs)
    info = await bot.get_webhook_info()
    return {
        "ok": True,
        "webhook_url": webhook_url,
        "secret_token_set": bool(WEBHOOK_SECRET),
        "telegram": {
            "url": info.url,
            "pending_update_count": info.pending_update_count,
            "last_error_message": info.last_error_message,
        },
        "db": _db_kind(),
        "tg_api": api_configured(),
        "next": [
            "Write /start to your bot in Telegram",
            "Ensure bot is ADMIN of @autopostbottg",
            "Set CRON_SECRET and external cron → /cron?secret=...",
        ],
    }


@app.post("/webhook")
async def telegram_webhook(request: Request):
    if not BOT_TOKEN or bot is None or dp is None:
        raise HTTPException(500, "BOT_TOKEN not set")
    _verify_telegram_secret(request)

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
    if not BOT_TOKEN or bot is None:
        raise HTTPException(500, "BOT_TOKEN not set")

    secret = os.getenv("CRON_SECRET", "") or WEBHOOK_SECRET
    if not secret:
        raise HTTPException(403, "CRON_SECRET not set — refusing open cron")
    qsecret = request.query_params.get("secret", "")
    auth_ok = authorization == f"Bearer {secret}" or qsecret == secret
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
    """Crypto Pay webhook — requires valid HMAC signature when token is set."""
    if not BOT_TOKEN or bot is None:
        raise HTTPException(500, "BOT_TOKEN not set")

    body = await request.body()
    sig = request.headers.get("crypto-pay-api-signature")
    if os.getenv("CRYPTO_BOT_TOKEN"):
        if not _verify_cryptobot_signature(body, sig):
            raise HTTPException(403, "Invalid CryptoBot signature")

    await ensure_db()
    import json
    data = json.loads(body.decode() or "{}")

    update_type = data.get("update_type") or data.get("type")
    invoice = data.get("payload") if isinstance(data.get("payload"), dict) else data.get("invoice")
    if update_type and update_type != "invoice_paid" and not (invoice and invoice.get("status") == "paid"):
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
