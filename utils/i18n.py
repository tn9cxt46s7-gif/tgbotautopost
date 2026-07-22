"""Lightweight i18n: RU / EN / LT / ET for Baltic EU users."""

from __future__ import annotations

LANGS = ("ru", "en", "lt", "et")
LANG_LABELS = {
    "ru": "Русский",
    "en": "English",
    "lt": "Lietuvių",
    "et": "Eesti",
}

# Reply-keyboard button labels per language
BTN = {
    "autopost": {"ru": "Автопостинг", "en": "Autopost", "lt": "Autopostas", "et": "Autopostitus"},
    "profile": {"ru": "Профиль", "en": "Profile", "lt": "Profilis", "et": "Profiil"},
    "sub": {"ru": "Подписка", "en": "Subscription", "lt": "Prenumerata", "et": "Tellimus"},
    "ref": {"ru": "Рефералка", "en": "Referral", "lt": "Rekomendacijos", "et": "Soovitused"},
    "ads": {"ru": "Мои объявления", "en": "My ads", "lt": "Mano skelbimai", "et": "Minu kuulutused"},
    "add_ad": {"ru": "Добавить объявление", "en": "Add ad", "lt": "Pridėti skelbimą", "et": "Lisa kuulutus"},
    "groups": {"ru": "Мои группы", "en": "My groups", "lt": "Mano grupės", "et": "Minu grupid"},
    "account": {"ru": "Мой аккаунт", "en": "My account", "lt": "Mano paskyra", "et": "Minu konto"},
    "guide": {"ru": "Инструкция", "en": "Guide", "lt": "Instrukcija", "et": "Juhend"},
    "templates": {"ru": "Шаблоны", "en": "Templates", "lt": "Šablonai", "et": "Mallid"},
    "settings": {"ru": "Настройки", "en": "Settings", "lt": "Nustatymai", "et": "Seaded"},
    "support": {"ru": "Поддержка", "en": "Support", "lt": "Pagalba", "et": "Tugi"},
    "cancel": {"ru": "Отмена", "en": "Cancel", "lt": "Atšaukti", "et": "Tühista"},
    "pick_group": {"ru": "Выбрать группу", "en": "Pick group", "lt": "Pasirinkti grupę", "et": "Vali grupp"},
    "end_chat": {"ru": "Завершить диалог", "en": "End chat", "lt": "Baigti pokalbį", "et": "Lõpeta vestlus"},
    "language": {"ru": "Язык", "en": "Language", "lt": "Kalba", "et": "Keel"},
}


def btn(key: str, lang: str = "ru") -> str:
    row = BTN.get(key) or {}
    return row.get(lang) or row.get("ru") or key


def all_btn(key: str) -> set[str]:
    row = BTN.get(key) or {}
    return set(row.values())


TEXTS = {
    "choose_lang": {
        "ru": "🌍 Выбери язык / Choose language",
        "en": "🌍 Choose your language",
        "lt": "🌍 Pasirinkite kalbą",
        "et": "🌍 Vali keel",
    },
    "lang_saved": {
        "ru": "✅ Язык сохранён: Русский",
        "en": "✅ Language saved: English",
        "lt": "✅ Kalba išsaugota: Lietuvių",
        "et": "✅ Keel salvestatud: Eesti",
    },
    "channel_required": {
        "ru": (
            "📢 <b>Подпишись на канал бота</b>\n\n"
            "Без подписки бот недоступен.\n"
            "Нажми «Подписаться», затем «Проверить»."
        ),
        "en": (
            "📢 <b>Subscribe to the bot channel</b>\n\n"
            "Without a subscription the bot is locked.\n"
            "Tap Subscribe, then Check."
        ),
        "lt": (
            "📢 <b>Prenumeruokite botų kanalą</b>\n\n"
            "Be prenumeratos botas nepasiekiamas.\n"
            "Paspauskite Prenumeruoti, tada Tikrinti."
        ),
        "et": (
            "📢 <b>Telli boti kanal</b>\n\n"
            "Ilma tellimuseta bot ei tööta.\n"
            "Vajuta Telli, seejärel Kontrolli."
        ),
    },
    "channel_ok": {
        "ru": "✅ Подписка на канал подтверждена!",
        "en": "✅ Channel subscription confirmed!",
        "lt": "✅ Kanalo prenumerata patvirtinta!",
        "et": "✅ Kanali tellimus kinnitatud!",
    },
    "channel_no": {
        "ru": "❌ Подписка не найдена. Подпишись и нажми «Проверить» ещё раз.",
        "en": "❌ Not subscribed yet. Subscribe and tap Check again.",
        "lt": "❌ Prenumerata nerasta. Prenumeruokite ir spauskite Tikrinti dar kartą.",
        "et": "❌ Tellimust ei leitud. Telli ja vajuta uuesti Kontrolli.",
    },
    "welcome": {
        "ru": (
            "👋 <b>Автопост в барахолки Латвии</b> 🇱🇻 · v{version}\n\n"
            "Посты идут <b>от твоего аккаунта</b>. Бот в группы не заходит.\n"
            "Саппорт @{support}\n\n"
            "Дальше — выбери подписку 👇"
        ),
        "en": (
            "👋 <b>Autopost to Latvia flea markets</b> 🇱🇻 · v{version}\n\n"
            "Posts go <b>from your account</b>. The bot never joins groups.\n"
            "Support @{support}\n\n"
            "Next — pick a subscription 👇"
        ),
        "lt": (
            "👋 <b>Autopostas Latvijos turgeliuose</b> 🇱🇻 · v{version}\n\n"
            "Skelbimai eina <b>iš jūsų paskyros</b>. Botas į grupes neina.\n"
            "Pagalba @{support}\n\n"
            "Toliau — pasirinkite prenumeratą 👇"
        ),
        "et": (
            "👋 <b>Autopost Läti kirbuturgudesse</b> 🇱🇻 · v{version}\n\n"
            "Postitused lähevad <b>sinu kontolt</b>. Bot gruppe ei liitu.\n"
            "Tugi @{support}\n\n"
            "Järgmine — vali tellimus 👇"
        ),
    },
    "blocked": {
        "ru": "🔒 Аккаунт заблокирован.\nНапиши @{support}.",
        "en": "🔒 Account blocked.\nMessage @{support}.",
        "lt": "🔒 Paskyra užblokuota.\nParašykite @{support}.",
        "et": "🔒 Konto on blokeeritud.\nKirjuta @{support}.",
    },
    "sub_bought": {
        "ru": (
            "✅ <b>Подписка куплена!</b>\n\n"
            "План: <b>{plan}</b>\n"
            "Активна до: <b>{until}</b>\n\n"
            "Можно подключать аккаунт, группы и запускать автопостинг."
        ),
        "en": (
            "✅ <b>Subscription purchased!</b>\n\n"
            "Plan: <b>{plan}</b>\n"
            "Active until: <b>{until}</b>\n\n"
            "You can link your account, add groups and start autoposting."
        ),
        "lt": (
            "✅ <b>Prenumerata nupirkta!</b>\n\n"
            "Planas: <b>{plan}</b>\n"
            "Galioja iki: <b>{until}</b>\n\n"
            "Galite prijungti paskyrą, grupes ir paleisti autopostą."
        ),
        "et": (
            "✅ <b>Tellimus ostetud!</b>\n\n"
            "Paket: <b>{plan}</b>\n"
            "Kehtib kuni: <b>{until}</b>\n\n"
            "Saad ühendada konto, lisada gruppe ja käivitada autopostituse."
        ),
    },
    "price_header": {
        "ru": "💎 <b>Подписка · барахолки Латвии</b> 🇱🇻\nЦены в <b>EUR</b> (EU)\n",
        "en": "💎 <b>Subscription · Latvia markets</b> 🇱🇻\nPrices in <b>EUR</b> (EU)\n",
        "lt": "💎 <b>Prenumerata · Latvijos turgeliai</b> 🇱🇻\nKainos <b>EUR</b> (ES)\n",
        "et": "💎 <b>Tellimus · Läti turud</b> 🇱🇻\nHinnad <b>EUR</b> (EL)\n",
    },
    "choose_plan": {
        "ru": "Выбери план 👇",
        "en": "Choose a plan 👇",
        "lt": "Pasirinkite planą 👇",
        "et": "Vali paket 👇",
    },
    "choose_pay": {
        "ru": "Выбери способ оплаты (EUR):",
        "en": "Choose payment method (EUR):",
        "lt": "Pasirinkite mokėjimo būdą (EUR):",
        "et": "Vali makseviis (EUR):",
    },
    "pay_methods_hint": {
        "ru": "Оплата: SEPA/карта · другие банки · CryptoBot · Stars\nПромо: START20, SALE15, VIP30\nСаппорт: @{support}",
        "en": "Pay: SEPA/card · other banks · CryptoBot · Stars\nPromos: START20, SALE15, VIP30\nSupport: @{support}",
        "lt": "Mokėjimas: SEPA/kortelė · kiti bankai · CryptoBot · Stars\nPromo: START20, SALE15, VIP30\nPagalba: @{support}",
        "et": "Makse: SEPA/kaart · teised pangad · CryptoBot · Stars\nPromo: START20, SALE15, VIP30\nTugi: @{support}",
    },
}


def t(key: str, lang: str = "ru", **kwargs) -> str:
    row = TEXTS.get(key) or {}
    text = row.get(lang) or row.get("ru") or key
    if kwargs:
        try:
            return text.format(**kwargs)
        except Exception:
            return text
    return text


PLAN_TITLES = {
    "week": {"ru": "Неделя", "en": "Week", "lt": "Savaitė", "et": "Nädal"},
    "month": {"ru": "Месяц", "en": "Month", "lt": "Mėnuo", "et": "Kuu"},
    "quarter": {"ru": "3 месяца", "en": "3 months", "lt": "3 mėnesiai", "et": "3 kuud"},
}


def plan_title(plan_key: str, lang: str = "ru") -> str:
    row = PLAN_TITLES.get(plan_key) or {}
    return row.get(lang) or row.get("ru") or plan_key
