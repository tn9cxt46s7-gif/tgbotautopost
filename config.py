import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "")

# On Vercel filesystem is read-only except /tmp
if os.getenv("VERCEL") and not os.getenv("DB_URL"):
    DB_URL = "sqlite+aiosqlite:////tmp/bot.db"
else:
    DB_URL = os.getenv("DB_URL", "sqlite+aiosqlite:///bot.db")

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
INTER_GROUP_DELAY_MIN = 30
INTER_GROUP_DELAY_MAX = 120
SCHEDULER_TICK_SECONDS = 60
GLOBAL_POST_DELAY = 1.5  # seconds between any two bot posts
REFERRAL_BONUS_DAYS = 3


def is_admin(telegram_id: int) -> bool:
    return telegram_id in ADMIN_IDS
