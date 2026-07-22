"""Premium custom emoji — owner's sticker pack + legacy fallbacks."""

# Owner premium pack (from Telegram custom_emoji entities)
# Message order: 👑🪙💵💎💎💎💳💎💎🪙
PACK = {
    "CROWN": 5807868868886009920,   # 👑 premium / subscription
    "COIN": 5992430854909989581,    # 🪙 week / coin
    "CASH": 5974217466270716579,    # 💵 EUR / fiat
    "GEM": 5807499888245612254,     # 💎 month
    "GEM2": 6028530359975548369,    # 💎 quarter
    "GEM3": 5807465992363710697,    # 💎 banks / promo
    "CARD": 5927169041595634481,    # 💳 SEPA / card
    "GEM4": 5771755323572359189,    # 💎 CryptoBot
    "GEM5": 5778546023349621090,    # 💎 crypto manual
    "COIN2": 5778311685638984859,   # 🪙 Stars
}

# Named roles used across the bot
EMOJI = {
    # ── Owner pack (payment / premium UX) ──
    "CROWN": PACK["CROWN"],
    "COIN": PACK["COIN"],
    "CASH": PACK["CASH"],
    "GEM": PACK["GEM"],
    "GEM2": PACK["GEM2"],
    "GEM3": PACK["GEM3"],
    "CARD": PACK["CARD"],
    "GEM4": PACK["GEM4"],
    "GEM5": PACK["GEM5"],
    "COIN2": PACK["COIN2"],
    # Logical aliases
    "SUB": PACK["CROWN"],
    "PLAN_WEEK": PACK["COIN"],
    "PLAN_MONTH": PACK["GEM"],
    "PLAN_QUARTER": PACK["GEM2"],
    "MONEY": PACK["CASH"],
    "BANKS": PACK["GEM3"],
    "CRYPTO": PACK["GEM5"],
    "CRYPTOBOT": PACK["GEM4"],
    "STAR": PACK["COIN2"],
    "PROMO": PACK["GEM3"],
    "PRICE": PACK["CASH"],
    # ── Legacy pack (rest of bot UI) ──
    "AUTO": 5794182096603847292,
    "PROFILE": 5794303034292968945,
    "REF": 5793901252987330401,
    "ADS": 5794066823976592976,
    "ADD": 5794235255414069703,
    "GROUPS": 5794030595927448202,
    "SETTINGS": 5794426162415409242,
    "SUPPORT": 5793905801357695657,
    "ADMIN": 5794310013614824017,
    "BACK": 5794342041185949794,
    "OK": 5794170049220581625,
    "WARN": 5794071015864671326,
    "PAUSE": 5794335744763894508,
    "PLAY": 5794442693744531795,
    "DELETE": 5818920837645867167,
    "SOLD": 5983399041197675256,
    "SEARCH": 5985630530111020079,
    "STATS": 5769403330761593044,
    "BROADCAST": 5891206318353551398,
    "TICKET": 5890838600433536921,
    "USER": 5890997763331591703,
    "CLOCK": 5897602448075263134,
    "PHOTO": 5897488197650223178,
    "WAVE": 5931415565955503486,
    "FIRE": 5778575233422200567,
    "LINK": 5958376256788502078,
    "ID": 5960672896060756972,
    "PEOPLE": 5875180111744995604,
    "EMPTY": 5841541824803509441,
    "EDIT": 5987718983728503684,
    "LOCK": 5987802868734760945,
    "UNLOCK": 5854776233950188167,
    "CHANNEL": 5958376256788502078,
    "LANG": 5931415565955503486,
}

FALLBACK = {
    "CROWN": "👑",
    "COIN": "🪙",
    "CASH": "💶",
    "GEM": "💎",
    "GEM2": "💎",
    "GEM3": "💎",
    "CARD": "💳",
    "GEM4": "💎",
    "GEM5": "💎",
    "COIN2": "🪙",
    "SUB": "👑",
    "PLAN_WEEK": "🪙",
    "PLAN_MONTH": "💎",
    "PLAN_QUARTER": "💎",
    "MONEY": "💶",
    "BANKS": "🏦",
    "CRYPTO": "₿",
    "CRYPTOBOT": "💎",
    "STAR": "⭐",
    "PROMO": "🎟",
    "PRICE": "💶",
    "AUTO": "🚀",
    "PROFILE": "👤",
    "REF": "🔗",
    "ADS": "📋",
    "ADD": "✍️",
    "GROUPS": "👥",
    "SETTINGS": "⚙️",
    "SUPPORT": "💬",
    "ADMIN": "🛡",
    "BACK": "◀️",
    "OK": "✅",
    "WARN": "⚠️",
    "PAUSE": "⏸",
    "PLAY": "▶️",
    "DELETE": "🗑",
    "SOLD": "🏷",
    "SEARCH": "🔍",
    "STATS": "📊",
    "BROADCAST": "📢",
    "TICKET": "🎫",
    "USER": "👤",
    "CLOCK": "🕒",
    "PHOTO": "🖼",
    "WAVE": "👋",
    "FIRE": "🔥",
    "LINK": "🔗",
    "ID": "🆔",
    "PEOPLE": "👥",
    "EMPTY": "📭",
    "EDIT": "✏️",
    "LOCK": "🔒",
    "UNLOCK": "🔓",
    "CHANNEL": "📢",
    "LANG": "🌍",
}

PLAN_EMOJI_KEY = {
    "week": "PLAN_WEEK",
    "month": "PLAN_MONTH",
    "quarter": "PLAN_QUARTER",
}


def eid(key: str) -> int:
    """Return custom emoji id for a named key."""
    return EMOJI[key]


def tg_emoji(key: str, fallback: str | None = None, *, force: bool = False) -> str:
    """HTML tg-emoji tag for message text.

    By default respects USE_PREMIUM_EMOJI. Pass force=True for sub/pay screens.
    """
    fb = fallback or FALLBACK.get(key, "•")
    if not force:
        try:
            from config import USE_PREMIUM_EMOJI
            if not USE_PREMIUM_EMOJI:
                return fb
        except Exception:
            return fb
    emoji_id = EMOJI.get(key)
    if not emoji_id:
        return fb
    return f'<tg-emoji emoji-id="{emoji_id}">{fb}</tg-emoji>'


def plain(key: str) -> str:
    """Unicode fallback only — never premium emoji."""
    return FALLBACK.get(key, "•")
