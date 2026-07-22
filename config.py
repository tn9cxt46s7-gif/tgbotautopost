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

# Plan limits: max ads / max groups
PLAN_LIMITS = {
    None: {"ads": 0, "groups": 0},
    "week": {"ads": 1, "groups": 3},
    "month": {"ads": 5, "groups": 15},
    "quarter": {"ads": 20, "groups": 50},
    "bonus": {"ads": 1, "groups": 3},
}

DEFAULT_INTERVAL_MINUTES = 60
DEFAULT_JITTER_SECONDS = 180
DEFAULT_QUIET_START = 0   # 00:00 UTC
DEFAULT_QUIET_END = 6     # 06:00 UTC
MAX_GROUP_FAILS = 3
# On Vercel keep delays short so a cron/webhook fits into maxDuration
INTER_GROUP_DELAY_MIN = 3 if IS_VERCEL else 30
INTER_GROUP_DELAY_MAX = 8 if IS_VERCEL else 120
SCHEDULER_TICK_SECONDS = 60
GLOBAL_POST_DELAY = 0.4 if IS_VERCEL else 1.5  # seconds between any two posts
# Soft time budget for one posting cycle on serverless (seconds)
# Hobby Vercel ≈ 10s maxDuration → keep budget under that
POST_BUDGET_SECONDS = int(os.getenv("POST_BUDGET_SECONDS", "8" if IS_VERCEL else "300"))
REFERRAL_BONUS_DAYS = 3


def is_admin(telegram_id: int) -> bool:
    return telegram_id in ADMIN_IDS
