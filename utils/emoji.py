"""Named premium custom emoji IDs mapped by meaning (TgAndroidIcons pack)."""

# Stable IDs from the original pool, assigned by semantic role.
EMOJI = {
    "AUTO": 5794182096603847292,       # rocket / launch
    "PROFILE": 5794303034292968945,    # person
    "SUB": 5794031944547178894,        # diamond / premium
    "REF": 5793901252987330401,        # link / share
    "ADS": 5794066823976592976,        # list / docs
    "ADD": 5794235255414069703,        # plus / write
    "GROUPS": 5794030595927448202,     # group / chat
    "SETTINGS": 5794426162415409242,   # gear
    "SUPPORT": 5793905801357695657,    # headset / help
    "ADMIN": 5794310013614824017,      # shield / key
    "BACK": 5794342041185949794,       # back arrow
    "OK": 5794170049220581625,         # check
    "WARN": 5794071015864671326,       # warning
    "MONEY": 5794348440687221181,      # money / stars
    "CARD": 5794246418034072201,       # card
    "CRYPTO": 5793932490284472550,     # crypto
    "PAUSE": 5794335744763894508,      # pause
    "PLAY": 5794442693744531795,       # play
    "DELETE": 5818920837645867167,     # trash
    "SOLD": 5983399041197675256,       # sold / done
    "SEARCH": 5985630530111020079,     # search
    "STATS": 5769403330761593044,      # chart
    "BROADCAST": 5891206318353551398,  # megaphone
    "TICKET": 5890838600433536921,     # ticket
    "USER": 5890997763331591703,       # user
    "CLOCK": 5897602448075263134,      # clock
    "PHOTO": 5897488197650223178,      # photo
    "PRICE": 5967591100532134862,      # price tag
    "WAVE": 5931415565955503486,       # wave / hello
    "FIRE": 5778575233422200567,       # fire
    "STAR": 5906995262378741881,       # star
    "LINK": 5958376256788502078,       # link
    "ID": 5960672896060756972,         # id badge
    "PEOPLE": 5875180111744995604,     # people
    "EMPTY": 5841541824803509441,      # empty box
    "EDIT": 5987718983728503684,       # edit
    "LOCK": 5987802868734760945,       # lock / block
    "UNLOCK": 5854776233950188167,     # unlock
}

# Human-readable fallbacks when custom emoji is unavailable
FALLBACK = {
    "AUTO": "🚀",
    "PROFILE": "👤",
    "SUB": "💎",
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
    "MONEY": "⭐",
    "CARD": "💳",
    "CRYPTO": "₿",
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
    "PRICE": "💰",
    "WAVE": "👋",
    "FIRE": "🔥",
    "STAR": "⭐",
    "LINK": "🔗",
    "ID": "🆔",
    "PEOPLE": "👥",
    "EMPTY": "📭",
    "EDIT": "✏️",
    "LOCK": "🔒",
    "UNLOCK": "🔓",
}


def eid(key: str) -> int:
    """Return custom emoji id for a named key."""
    return EMOJI[key]


def tg_emoji(key: str, fallback: str | None = None) -> str:
    """HTML tg-emoji tag for message text."""
    fb = fallback or FALLBACK.get(key, "•")
    return f'<tg-emoji emoji-id="{EMOJI[key]}">{fb}</tg-emoji>'
