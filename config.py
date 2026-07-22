import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "")

# True on Vercel serverless (no always-on process, short request budget)
IS_VERCEL = bool(os.getenv("VERCEL") or os.getenv("VERCEL_ENV"))

# my.telegram.org → API development tools (нужно для постинга от аккаунта клиента)
TG_API_ID = int(os.getenv("TG_API_ID", "0") or "0")
TG_API_HASH = os.getenv("TG_API_HASH", "")
# Ключ шифрования сессий; если пусто — берём из BOT_TOKEN
SESSION_SECRET = os.getenv("SESSION_SECRET") or BOT_TOKEN or "change-me"


def _normalize_db_url(url: str) -> str:
    """Make common Postgres URLs work with async SQLAlchemy."""
    if not url:
        return url
    if url.startswith("postgres://"):
        url = "postgresql+asyncpg://" + url[len("postgres://"):]
    elif url.startswith("postgresql://") and "+asyncpg" not in url:
        url = "postgresql+asyncpg://" + url[len("postgresql://"):]
    return url


# Prefer explicit DB_URL, then Vercel/Neon/Supabase style vars
_raw_db = (
    os.getenv("DB_URL")
    or os.getenv("POSTGRES_URL")
    or os.getenv("POSTGRES_PRISMA_URL")
    or os.getenv("DATABASE_URL")
    or ""
)

if _raw_db:
    DB_URL = _normalize_db_url(_raw_db)
elif os.getenv("VERCEL"):
    DB_URL = "sqlite+aiosqlite:////tmp/bot.db"
else:
    DB_URL = "sqlite+aiosqlite:///bot.db"

# Comma-separated Telegram IDs, e.g. "8414329140,123456789"
_raw_admins = os.getenv("ADMIN_IDS", "8414329140")
ADMIN_IDS: set[int] = {
    int(x.strip()) for x in _raw_admins.split(",") if x.strip().isdigit()
}

# Public support contact (opens in Telegram)
SUPPORT_USERNAME = (os.getenv("SUPPORT_USERNAME", "eb_support") or "eb_support").lstrip("@")
SUPPORT_URL = f"https://t.me/{SUPPORT_USERNAME}"

# Required public channel — user must join before using the bot
# Example: @your_channel or -1001234567890
REQUIRED_CHANNEL = (os.getenv("REQUIRED_CHANNEL", "") or "").strip()
REQUIRED_CHANNEL_URL = (os.getenv("REQUIRED_CHANNEL_URL", "") or "").strip() or None

# EU / Latvia payment details (EUR). Leave placeholders → support.
PAYMENT_CARD_DETAILS = os.getenv(
    "PAYMENT_CARD_DETAILS",
    "SEPA / card (EUR)\nIBAN: уточни у @eb_support\nПолучатель: уточни у @eb_support",
)
PAYMENT_BANKS_OTHER = os.getenv(
    "PAYMENT_BANKS_OTHER",
    "Другие банки / Revolut / Wise (EUR)\n"
    "Реквизиты: уточни у @eb_support\n"
    "В комментарии укажи номер заявки.",
)
PAYMENT_CRYPTO_DETAILS = os.getenv(
    "PAYMENT_CRYPTO_DETAILS",
    "USDT (TRC20): уточни кошелёк у @eb_support",
)
# EUR prices (whole euros). Override via env.
PAYMENT_EUR_WEEK = int(os.getenv("PAYMENT_EUR_WEEK", os.getenv("PAYMENT_RUB_WEEK", "5")))
PAYMENT_EUR_MONTH = int(os.getenv("PAYMENT_EUR_MONTH", os.getenv("PAYMENT_RUB_MONTH", "12")))
PAYMENT_EUR_QUARTER = int(os.getenv("PAYMENT_EUR_QUARTER", os.getenv("PAYMENT_RUB_QUARTER", "29")))
# Legacy aliases (amount still stored in DB column amount_rub = EUR amount)
PAYMENT_RUB_WEEK = PAYMENT_EUR_WEEK
PAYMENT_RUB_MONTH = PAYMENT_EUR_MONTH
PAYMENT_RUB_QUARTER = PAYMENT_EUR_QUARTER

BOT_VERSION = "2.3.0"
TRIAL_DAYS = int(os.getenv("TRIAL_DAYS", "1"))
# Disable premium custom emoji in text (faster, less lag on clients)
USE_PREMIUM_EMOJI = os.getenv("USE_PREMIUM_EMOJI", "0") == "1"
DEFAULT_LANG = os.getenv("DEFAULT_LANG", "ru")

# CryptoBot (Crypto Pay) — автооплата криптой
# Токен: @CryptoBot → Crypto Pay → Create App
CRYPTO_BOT_TOKEN = os.getenv("CRYPTO_BOT_TOKEN", "")
CRYPTO_BOT_ASSET = os.getenv("CRYPTO_BOT_ASSET", "USDT")
CRYPTO_BOT_FIAT = os.getenv("CRYPTO_BOT_FIAT", "EUR")
# testnet: https://testnet-pay.crypt.bot/api  main: https://pay.crypt.bot/api
CRYPTO_BOT_API = os.getenv(
    "CRYPTO_BOT_API",
    "https://pay.crypt.bot/api",
)

# Subscription expiry reminders (days before end)
SUB_REMIND_DAYS = int(os.getenv("SUB_REMIND_DAYS", "2"))

# Subscription plans — EUR primary (EU / Latvia). Stars optional pay method only.
PLANS = {
    "week": {
        "title": "Неделя",
        "days": 7,
        "stars": 150,
        "eur": PAYMENT_EUR_WEEK,
        "rub": PAYMENT_EUR_WEEK,  # DB column amount_rub stores EUR
    },
    "month": {
        "title": "Месяц",
        "days": 30,
        "stars": 450,
        "eur": PAYMENT_EUR_MONTH,
        "rub": PAYMENT_EUR_MONTH,
    },
    "quarter": {
        "title": "3 месяца",
        "days": 90,
        "stars": 1100,
        "eur": PAYMENT_EUR_QUARTER,
        "rub": PAYMENT_EUR_QUARTER,
    },
}

# Plan limits: max ads / max groups
PLAN_LIMITS = {
    None: {"ads": 0, "groups": 0},
    "trial": {"ads": 1, "groups": 2},
    "week": {"ads": 1, "groups": 3},
    "month": {"ads": 5, "groups": 15},
    "quarter": {"ads": 20, "groups": 50},
    "bonus": {"ads": 1, "groups": 3},
}

DEFAULT_INTERVAL_MINUTES = 90
DEFAULT_JITTER_SECONDS = 300
DEFAULT_QUIET_START = 0   # 00:00 UTC
DEFAULT_QUIET_END = 7     # 07:00 UTC
MAX_GROUP_FAILS = 2
# Absolute floors (anti-ban) — even «Запостить сейчас» cannot go below soft floor
MIN_INTERVAL_MINUTES = 60
FORCE_MIN_INTERVAL_MINUTES = 45  # soft floor for manual post
MAX_POSTS_PER_GROUP_PER_DAY = int(os.getenv("MAX_POSTS_PER_GROUP_PER_DAY", "6"))
MAX_POSTS_PER_USER_PER_DAY = int(os.getenv("MAX_POSTS_PER_USER_PER_DAY", "30"))
# One group per serverless tick — next cron continues (safer + fits timeout)
MAX_GROUPS_PER_TICK = 1 if IS_VERCEL else 3
# Delays between groups (always-on). On Vercel tick posts ≤1 group, so delays matter less.
INTER_GROUP_DELAY_MIN = 45
INTER_GROUP_DELAY_MAX = 180
SCHEDULER_TICK_SECONDS = 60
GLOBAL_POST_DELAY = 2.0
# Soft time budget for one posting cycle on serverless (seconds)
POST_BUDGET_SECONDS = int(os.getenv("POST_BUDGET_SECONDS", "8" if IS_VERCEL else "300"))
REFERRAL_BONUS_DAYS = 3
FLOOD_COOLDOWN_EXTRA_MINUTES = 10


def is_admin(telegram_id: int) -> bool:
    return telegram_id in ADMIN_IDS
