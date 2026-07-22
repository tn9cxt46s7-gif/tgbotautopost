"""Bot keyboards — reply menus without custom emoji (avoids client lag)."""

from aiogram.types import (
    ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton,
    KeyboardButtonRequestChat,
)
from utils.emoji import eid
from utils.i18n import btn, LANGS, LANG_LABELS, plan_title
from config import SUPPORT_URL, SUPPORT_USERNAME
from utils.channel import channel_url

REQ_GROUP_ANY = 102


# ── Reply menus (no icon_custom_emoji_id — major lag fix) ──────────────────

def main_menu_kb(lang: str = "ru") -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=btn("autopost", lang)), KeyboardButton(text=btn("profile", lang))],
            [KeyboardButton(text=btn("sub", lang)), KeyboardButton(text=btn("ref", lang))],
            [KeyboardButton(text=btn("ads", lang)), KeyboardButton(text=btn("add_ad", lang))],
            [KeyboardButton(text=btn("groups", lang)), KeyboardButton(text=btn("account", lang))],
            [KeyboardButton(text=btn("guide", lang)), KeyboardButton(text=btn("templates", lang))],
            [KeyboardButton(text=btn("settings", lang)), KeyboardButton(text=btn("support", lang))],
            [KeyboardButton(text=btn("language", lang))],
        ],
        resize_keyboard=True,
    )


# Backward-compatible default (RU)
main_menu = main_menu_kb("ru")


def cancel_kb_for(lang: str = "ru") -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=btn("cancel", lang))]],
        resize_keyboard=True,
    )


cancel_kb = cancel_kb_for("ru")


def group_pick_kb(lang: str = "ru") -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(
                    text=btn("pick_group", lang),
                    request_chat=KeyboardButtonRequestChat(
                        request_id=REQ_GROUP_ANY,
                        chat_is_channel=False,
                        request_title=True,
                        request_username=True,
                    ),
                )
            ],
            [KeyboardButton(text=btn("cancel", lang))],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def support_exit_kb_for(lang: str = "ru") -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=btn("end_chat", lang))]],
        resize_keyboard=True,
    )


support_exit_kb = support_exit_kb_for("ru")


def language_kb() -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text=LANG_LABELS[code], callback_data=f"lang_{code}")]
        for code in LANGS
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def channel_gate_kb(lang: str = "ru") -> InlineKeyboardMarkup:
    labels = {
        "ru": ("Подписаться", "Проверить подписку"),
        "en": ("Subscribe", "Check subscription"),
        "lt": ("Prenumeruoti", "Tikrinti prenumeratą"),
        "et": ("Telli", "Kontrolli tellimust"),
    }
    sub_l, check_l = labels.get(lang, labels["ru"])
    rows = []
    url = channel_url()
    if url:
        rows.append([InlineKeyboardButton(text=sub_l, url=url)])
    rows.append([InlineKeyboardButton(text=check_l, callback_data="channel_check")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


# ── Profile / common ───────────────────────────────────────────────────────

def profile_menu_kb(lang: str = "ru") -> InlineKeyboardMarkup:
    labels = {
        "ru": ("Мой аккаунт", "Купить подписку", "Реферальная программа", "Пробный день"),
        "en": ("My account", "Buy subscription", "Referral program", "Trial day"),
        "lt": ("Mano paskyra", "Pirkti prenumeratą", "Rekomendacijos", "Bandomoji diena"),
        "et": ("Minu konto", "Osta tellimus", "Soovitusprogramm", "Proovipäev"),
    }
    a, s, r, tr = labels.get(lang, labels["ru"])
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=a, callback_data="account_menu")],
        [InlineKeyboardButton(text=s, callback_data="sub_menu")],
        [InlineKeyboardButton(text=r, callback_data="ref_menu")],
        [InlineKeyboardButton(text=tr, callback_data="trial_start")],
        [InlineKeyboardButton(text=f"Support @{SUPPORT_USERNAME}", url=SUPPORT_URL)],
        [InlineKeyboardButton(text=btn("language", lang), callback_data="lang_menu")],
    ])


profile_menu = profile_menu_kb("ru")


def support_menu_kb(lang: str = "ru") -> InlineKeyboardMarkup:
    labels = {
        "ru": "Чат в боте (тикет)",
        "en": "In-bot ticket",
        "lt": "Pokalbys bote (bilietas)",
        "et": "Vestlus botis (pilet)",
    }
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"@{SUPPORT_USERNAME}", url=SUPPORT_URL)],
        [InlineKeyboardButton(text=labels.get(lang, labels["ru"]), callback_data="support_ticket")],
    ])


def account_kb(linked: bool, serverless: bool = False, lang: str = "ru") -> InlineKeyboardMarkup:
    labels = {
        "ru": {
            "unlink": "Отключить полный автопост",
            "phone": "Подключить по номеру",
            "qr": "Подключить через QR",
            "phone_v": "Подключить по номеру (Vercel)",
            "qr_try": "Попробовать QR",
            "back": "Назад в профиль",
        },
        "en": {
            "unlink": "Unlink account",
            "phone": "Link by phone",
            "qr": "Link via QR",
            "phone_v": "Link by phone (Vercel)",
            "qr_try": "Try QR",
            "back": "Back to profile",
        },
        "lt": {
            "unlink": "Atjungti paskyrą",
            "phone": "Prijungti telefonu",
            "qr": "Prijungti per QR",
            "phone_v": "Prijungti telefonu (Vercel)",
            "qr_try": "Bandyti QR",
            "back": "Atgal į profilį",
        },
        "et": {
            "unlink": "Lahuta konto",
            "phone": "Ühenda telefoniga",
            "qr": "Ühenda QR-iga",
            "phone_v": "Ühenda telefoniga (Vercel)",
            "qr_try": "Proovi QR",
            "back": "Tagasi profiili",
        },
    }
    L = labels.get(lang, labels["ru"])
    if linked:
        rows = [[InlineKeyboardButton(text=L["unlink"], callback_data="account_unlink")]]
    else:
        rows = []
        if serverless:
            rows.append([InlineKeyboardButton(text=L["phone_v"], callback_data="account_link_phone")])
            rows.append([InlineKeyboardButton(text=L["qr_try"], callback_data="account_link")])
        else:
            rows.append([InlineKeyboardButton(text=L["qr"], callback_data="account_link")])
            rows.append([InlineKeyboardButton(text=L["phone"], callback_data="account_link_phone")])
    rows.append([InlineKeyboardButton(text=L["back"], callback_data="back_to_profile")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def back_to_menu_kb_for(lang: str = "ru") -> InlineKeyboardMarkup:
    labels = {
        "ru": "Назад в профиль",
        "en": "Back to profile",
        "lt": "Atgal į profilį",
        "et": "Tagasi profiili",
    }
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=labels.get(lang, labels["ru"]), callback_data="back_to_profile")],
    ])


back_to_menu_kb = back_to_menu_kb_for("ru")


def subscription_plans_kb(plans: dict, show_promo: bool = False, lang: str = "ru") -> InlineKeyboardMarkup:
    rows = []
    for key, plan in plans.items():
        eur = plan.get("eur") or plan.get("rub")
        title = plan_title(key, lang)
        label = f"{title} — {eur} €"
        rows.append([InlineKeyboardButton(text=label, callback_data=f"plan_{key}")])
    promo_labels = {
        "ru": "🎟 Ввести промокод",
        "en": "🎟 Enter promo",
        "lt": "🎟 Įvesti promo kodą",
        "et": "🎟 Sisesta sooduskood",
    }
    back_labels = {"ru": "Назад", "en": "Back", "lt": "Atgal", "et": "Tagasi"}
    if show_promo:
        rows.append([InlineKeyboardButton(
            text=promo_labels.get(lang, promo_labels["ru"]),
            callback_data="promo_enter",
        )])
    rows.append([InlineKeyboardButton(
        text=back_labels.get(lang, "Back"),
        callback_data="back_to_profile",
    )])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def payment_method_kb(plan_key: str, cryptobot: bool = False, lang: str = "ru") -> InlineKeyboardMarkup:
    """EU payment methods — EUR first, Stars last (optional)."""
    L = {
        "ru": {
            "card": "💳 SEPA / карта (EUR)",
            "banks": "🏦 Другие банки (EUR)",
            "cb": "CryptoBot USDT (авто)",
            "crypto": "Крипта вручную",
            "stars": "Telegram Stars (опц.)",
            "back": "Назад",
        },
        "en": {
            "card": "💳 SEPA / card (EUR)",
            "banks": "🏦 Other banks (EUR)",
            "cb": "CryptoBot USDT (auto)",
            "crypto": "Crypto manual",
            "stars": "Telegram Stars (opt.)",
            "back": "Back",
        },
        "lt": {
            "card": "💳 SEPA / kortelė (EUR)",
            "banks": "🏦 Kiti bankai (EUR)",
            "cb": "CryptoBot USDT (auto)",
            "crypto": "Kriptovaliuta rankiniu",
            "stars": "Telegram Stars (pasir.)",
            "back": "Atgal",
        },
        "et": {
            "card": "💳 SEPA / kaart (EUR)",
            "banks": "🏦 Teised pangad (EUR)",
            "cb": "CryptoBot USDT (auto)",
            "crypto": "Krüpto käsitsi",
            "stars": "Telegram Stars (valik)",
            "back": "Tagasi",
        },
    }[lang if lang in ("ru", "en", "lt", "et") else "ru"]

    rows = [
        [InlineKeyboardButton(text=L["card"], callback_data=f"pay_card_{plan_key}")],
        [InlineKeyboardButton(text=L["banks"], callback_data=f"pay_banks_{plan_key}")],
    ]
    if cryptobot:
        rows.append([InlineKeyboardButton(text=L["cb"], callback_data=f"pay_cryptobot_{plan_key}")])
    rows.extend([
        [InlineKeyboardButton(text=L["crypto"], callback_data=f"pay_crypto_{plan_key}")],
        [InlineKeyboardButton(text=L["stars"], callback_data=f"pay_stars_{plan_key}")],
        [InlineKeyboardButton(text=f"@{SUPPORT_USERNAME}", url=SUPPORT_URL)],
        [InlineKeyboardButton(text=L["back"], callback_data="sub_menu")],
    ])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def pending_payment_user_kb(payment_id: int, lang: str = "ru") -> InlineKeyboardMarkup:
    L = {
        "ru": ("Я оплатил ✅", "Отменить заявку"),
        "en": ("I paid ✅", "Cancel request"),
        "lt": ("Sumokėjau ✅", "Atšaukti"),
        "et": ("Maksin ✅", "Tühista"),
    }.get(lang, ("Я оплатил ✅", "Отменить заявку"))
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=L[0], callback_data=f"pay_done_{payment_id}")],
        [InlineKeyboardButton(text=L[1], callback_data=f"pay_cancel_{payment_id}")],
        [InlineKeyboardButton(text=f"@{SUPPORT_USERNAME}", url=SUPPORT_URL)],
    ])


def admin_payment_kb(payment_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Подтвердить оплату", callback_data=f"adm_pay_ok_{payment_id}")],
        [InlineKeyboardButton(text="Отклонить", callback_data=f"adm_pay_no_{payment_id}")],
    ])


# ── Ads ────────────────────────────────────────────────────────────────────

def skip_photo_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Без фото", callback_data="ad_skip_photo")],
        [InlineKeyboardButton(text="Отмена", callback_data="ad_cancel")],
    ])


def skip_price_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Без цены", callback_data="ad_skip_price")],
        [InlineKeyboardButton(text="Отмена", callback_data="ad_cancel")],
    ])


def ads_list_kb(ads: list) -> InlineKeyboardMarkup:
    rows = []
    status_icon = {"active": "▶️", "paused": "⏸", "draft": "📝", "sold": "🏷"}
    for ad in ads:
        mark = status_icon.get(ad.status, "•")
        title = (ad.title or ad.text[:40])[:40]
        rows.append([InlineKeyboardButton(
            text=f"{mark} #{ad.id} {title}",
            callback_data=f"ad_view_{ad.id}",
        )])
    rows.append([InlineKeyboardButton(text="Добавить", callback_data="ad_create")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def ad_card_kb(ad) -> InlineKeyboardMarkup:
    rows = []
    if ad.status in ("draft", "paused"):
        rows.append([InlineKeyboardButton(text="Запустить", callback_data=f"ad_start_{ad.id}")])
    if ad.status == "active":
        rows.append([InlineKeyboardButton(text="Пауза", callback_data=f"ad_pause_{ad.id}")])
    if ad.status != "sold":
        rows.append([InlineKeyboardButton(text="Продано", callback_data=f"ad_sold_{ad.id}")])
    rows.append([
        InlineKeyboardButton(text="Изменить текст", callback_data=f"ad_edit_text_{ad.id}"),
        InlineKeyboardButton(text="Цена", callback_data=f"ad_edit_price_{ad.id}"),
    ])
    rows.append([InlineKeyboardButton(text="Удалить", callback_data=f"ad_del_{ad.id}")])
    rows.append([InlineKeyboardButton(text="К списку", callback_data="ads_list")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


# ── Groups ─────────────────────────────────────────────────────────────────

def groups_list_kb(groups: list) -> InlineKeyboardMarkup:
    rows = []
    for g in groups:
        mark = "✅" if g.active else "⛔"
        title = (g.title or str(g.chat_id))[:40]
        rows.append([InlineKeyboardButton(
            text=f"{mark} {title}",
            callback_data=f"grp_view_{g.id}",
        )])
    rows.append([InlineKeyboardButton(text="➕ Добавить группу", callback_data="grp_add")])
    rows.append([InlineKeyboardButton(text="Как добавить группу?", callback_data="grp_help")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def group_card_kb(group) -> InlineKeyboardMarkup:
    toggle = "Выключить" if group.active else "Включить"
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=toggle, callback_data=f"grp_toggle_{group.id}")],
        [InlineKeyboardButton(text="Интервал", callback_data=f"grp_interval_{group.id}")],
        [InlineKeyboardButton(text="Удалить", callback_data=f"grp_del_{group.id}")],
        [InlineKeyboardButton(text="К списку", callback_data="groups_list")],
    ])


# ── Autopost ───────────────────────────────────────────────────────────────

def autopost_kb(enabled: bool) -> InlineKeyboardMarkup:
    if enabled:
        btn_ap = InlineKeyboardButton(text="Остановить", callback_data="ap_stop")
    else:
        btn_ap = InlineKeyboardButton(text="Запустить", callback_data="ap_start")
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Запостить сейчас в группы", callback_data="ap_now")],
        [btn_ap],
        [InlineKeyboardButton(text="Мой аккаунт", callback_data="account_menu")],
        [InlineKeyboardButton(text="Мои объявления", callback_data="ads_list")],
        [InlineKeyboardButton(text="Мои группы", callback_data="groups_list")],
    ])


# ── Settings ───────────────────────────────────────────────────────────────

settings_kb = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="Интервал по умолчанию", callback_data="set_interval")],
    [InlineKeyboardButton(text="Тихие часы", callback_data="set_quiet")],
    [InlineKeyboardButton(text="Язык / Language", callback_data="lang_menu")],
])


# ── Admin ──────────────────────────────────────────────────────────────────

admin_menu = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="Статистика", callback_data="admin_stats")],
    [InlineKeyboardButton(text="Оплаты (pending)", callback_data="admin_payments")],
    [InlineKeyboardButton(text="Пользователи", callback_data="admin_users")],
    [InlineKeyboardButton(text="Найти пользователя", callback_data="admin_find")],
    [InlineKeyboardButton(text="Выдать подписку", callback_data="admin_give_sub")],
    [InlineKeyboardButton(text="Объявления", callback_data="admin_ads")],
    [InlineKeyboardButton(text="Проблемные группы", callback_data="admin_groups")],
    [InlineKeyboardButton(text="Рассылка", callback_data="admin_broadcast")],
    [InlineKeyboardButton(text="Саппорт", callback_data="admin_support")],
])


def admin_user_kb(telegram_id: int, is_blocked: bool) -> InlineKeyboardMarkup:
    block_btn = (
        InlineKeyboardButton(text="Разблокировать", callback_data=f"adm_unblock_{telegram_id}")
        if is_blocked else
        InlineKeyboardButton(text="Заблокировать", callback_data=f"adm_block_{telegram_id}")
    )
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Выдать дни", callback_data=f"adm_give_{telegram_id}")],
        [block_btn],
        [InlineKeyboardButton(text="Назад", callback_data="admin_users")],
    ])


def admin_users_list_kb(users: list, offset: int = 0) -> InlineKeyboardMarkup:
    rows = []
    for u in users:
        mark = "🔒" if u.is_blocked else ("💎" if u.subscription_end else "•")
        name = f"@{u.username}" if u.username else str(u.telegram_id)
        rows.append([InlineKeyboardButton(
            text=f"{mark} {name}",
            callback_data=f"adm_user_{u.telegram_id}",
        )])
    nav = []
    if offset > 0:
        nav.append(InlineKeyboardButton(text="◀️", callback_data=f"admin_users_{max(0, offset - 20)}"))
    nav.append(InlineKeyboardButton(text="▶️", callback_data=f"admin_users_{offset + 20}"))
    if nav:
        rows.append(nav)
    rows.append([InlineKeyboardButton(text="В админку", callback_data="admin_home")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def support_admin_kb(ticket_id: int, telegram_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Ответить", callback_data=f"sup_reply_{ticket_id}_{telegram_id}")],
        [InlineKeyboardButton(text="Закрыть тикет", callback_data=f"sup_close_{ticket_id}")],
    ])


def broadcast_confirm_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Всем", callback_data="bc_all")],
        [InlineKeyboardButton(text="Только с подпиской", callback_data="bc_subs")],
        [InlineKeyboardButton(text="Отмена", callback_data="admin_home")],
    ])


def admin_back_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="В админку", callback_data="admin_home")],
    ])
