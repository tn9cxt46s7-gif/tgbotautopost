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

# Manual payment details (shown for card/crypto). Leave empty → «напиши в поддержку».
PAYMENT_CARD_DETAILS = os.getenv(
    "PAYMENT_CARD_DETAILS",
    "Карта: уточни реквизиты у @eb_support",
)
PAYMENT_CRYPTO_DETAILS = os.getenv(
    "PAYMENT_CRYPTO_DETAILS",
    "USDT (TRC20): уточни кошелёк у @eb_support",
)
# Optional fixed RUB prices (can override via env)
PAYMENT_RUB_WEEK = int(os.getenv("PAYMENT_RUB_WEEK", "299"))
PAYMENT_RUB_MONTH = int(os.getenv("PAYMENT_RUB_MONTH", "799"))
PAYMENT_RUB_QUARTER = int(os.getenv("PAYMENT_RUB_QUARTER", "1990"))

BOT_VERSION = "2.1.0"
TRIAL_DAYS = int(os.getenv("TRIAL_DAYS", "1"))

# Subscription plans (single source of truth)
PLANS = {
    "week": {
        "title": "Неделя",
        "days": 7,
        "stars": 150,
        "rub": PAYMENT_RUB_WEEK,
    },
    "month": {
        "title": "Месяц",
        "days": 30,
        "stars": 450,
        "rub": PAYMENT_RUB_MONTH,
    },
    "quarter": {
        "title": "3 месяца",
        "days": 90,
        "stars": 1100,
        "rub": PAYMENT_RUB_QUARTER,
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
