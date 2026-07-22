"""Anti-ban helpers: content checks and human-like text variants.

No system can guarantee zero bans — these rules reduce risk:
interval, daily caps, quiet hours, text variation, flood handling.
"""

from __future__ import annotations

import re
import random

# Soft risk signals (not a ban list of legal goods — only spam patterns)
_SPAM_PHRASES = [
    "пиши в лс всем",
    "гарантия 100%",
    "без предоплаты срочно всем",
    "крипта обмен 1 к 2",
    "накрутка подписчиков",
    "бесплатные звезды",
]

_URL_RE = re.compile(r"https?://\S+|t\.me/\S+|@\w{4,}", re.I)
_PHONE_RE = re.compile(r"\+?\d[\d\-\s()]{8,}\d")
_CAPS_WORD_RE = re.compile(r"\b[A-ZА-ЯЁ]{4,}\b")

_SYNONYMS = [
    (("продаю", "продам", "отдаю", "реализую"), ("Продаю", "Продам", "Отдаю")),
    (("состояние", "сост."), ("состояние", "сост.")),
    (("торг", "возможен торг", "торг уместен"), ("торг", "возможен торг")),
    (("самовывоз", "забрать лично", "забрать самому"), ("самовывоз", "забрать лично")),
    (("город", "г."), ("город", "г.")),
]


def validate_ad_text(text: str) -> str | None:
    """Return error message if text looks too spammy for flea markets, else None."""
    raw = (text or "").strip()
    if len(raw) < 15:
        return "Текст слишком короткий (минимум ~15 символов)."
    if len(raw) > 3500:
        return "Текст слишком длинный для барахолки."

    lower = raw.lower()
    for phrase in _SPAM_PHRASES:
        if phrase in lower:
            return f"Похоже на спам («{phrase}»). Перепиши объявление."

    urls = _URL_RE.findall(raw)
    if len(urls) > 2:
        return "Слишком много ссылок/упоминаний (макс. 2). Так банят чаще."

    phones = _PHONE_RE.findall(raw)
    if len(phones) > 2:
        return "Слишком много номеров в тексте (макс. 2)."

    caps = _CAPS_WORD_RE.findall(raw)
    if len(caps) >= 8:
        return "Слишком много КАПСА — модераторы барахолок режут такое."

    # Same line repeated
    lines = [ln.strip() for ln in raw.splitlines() if ln.strip()]
    if len(lines) >= 2 and len(set(lines)) == 1:
        return "Не дублируй одну и ту же строку много раз."

    return None


def build_ad_variants(text: str, price: str | None, seed: int) -> str:
    """Build a lightly varied post so repeats look less robotic."""
    rng = random.Random(seed)
    lines = [ln for ln in text.strip().splitlines() if ln.strip()]
    if not lines:
        body = text.strip()
    else:
        head, rest = lines[0], lines[1:]
        # Light synonym swap on first line only
        head_l = head
        for group, _ in _SYNONYMS:
            for word in group:
                if word.lower() in head_l.lower():
                    repl = rng.choice(group)
                    # case-insensitive replace once
                    pattern = re.compile(re.escape(word), re.I)
                    head_l = pattern.sub(repl, head_l, count=1)
                    break
        if len(rest) > 1 and seed % 3 == 0:
            rest = rest[:]
            rng.shuffle(rest)
        body = "\n".join([head_l] + rest)

    tags = [
        "#pardosana", "#sludinajums", "#baraholka", "#riga", "#latvija",
        "#продажа", "#объявление", "#товар",
    ]
    # Sometimes skip tag entirely (seed % 5 == 0) — less fingerprint
    tag = None if seed % 5 == 0 else tags[seed % len(tags)]

    parts = [body]
    if price:
        price_forms = [
            f"Цена: {price}",
            f"Стоимость: {price}",
            f"{price}",
            f"💰 {price}",
        ]
        parts.append(price_forms[seed % len(price_forms)])

    if tag:
        if seed % 2 == 0:
            parts.append(tag)
        else:
            parts.insert(0, tag)

    # Tiny whitespace fingerprint (1–3 spaces at end) — low risk
    spacer = " " * ((seed % 3) + 1)
    # Occasional extra blank line
    joiner = "\n\n\n" if seed % 7 == 0 else "\n\n"
    return joiner.join(parts) + spacer


def safety_disclaimer() -> str:
    return (
        "⚠️ <b>Важно про баны</b>\n"
        "Посты идут <b>от твоего аккаунта</b> в барахолки Латвии. "
        "100% защиты от бана нет — решают правила каждой группы.\n\n"
        "Мы снижаем риск:\n"
        "• интервал и джиттер\n"
        "• лимит постов в сутки на группу\n"
        "• тихие часы\n"
        "• вариации текста\n"
        "• пауза при FloodWait\n"
        "• стоп группы после ошибок\n\n"
        "Сам проверяй правила группы (Rīga / LV marketplace) и не шли запрещённый товар."
    )
