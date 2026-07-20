from aiogram.types import (
    ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton,
    KeyboardButtonRequestChat,
)
from utils.emoji import eid

# request_id for chat picker (returned in chat_shared)
REQ_GROUP_ANY = 102


# ── Reply menus ────────────────────────────────────────────────────────────

main_menu = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton(text="Автопостинг", icon_custom_emoji_id=eid("AUTO")),
            KeyboardButton(text="Профиль", icon_custom_emoji_id=eid("PROFILE")),
        ],
        [
            KeyboardButton(text="Подписка", icon_custom_emoji_id=eid("SUB")),
            KeyboardButton(text="Рефералка", icon_custom_emoji_id=eid("REF")),
        ],
        [
            KeyboardButton(text="Мои объявления", icon_custom_emoji_id=eid("ADS")),
            KeyboardButton(text="Добавить объявление", icon_custom_emoji_id=eid("ADD")),
        ],
        [
            KeyboardButton(text="Мои группы", icon_custom_emoji_id=eid("GROUPS")),
            KeyboardButton(text="Мой аккаунт", icon_custom_emoji_id=eid("USER")),
        ],
        [
            KeyboardButton(text="Настройки", icon_custom_emoji_id=eid("SETTINGS")),
            KeyboardButton(text="Поддержка", icon_custom_emoji_id=eid("SUPPORT")),
        ],
    ],
    resize_keyboard=True,
)

cancel_kb = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text="Отмена")]],
    resize_keyboard=True,
)


def group_pick_kb() -> ReplyKeyboardMarkup:
    """Native Telegram chat picker — any group/supergroup, bot need not be a member."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(
                    text="Выбрать группу",
                    request_chat=KeyboardButtonRequestChat(
                        request_id=REQ_GROUP_ANY,
                        chat_is_channel=False,
                        request_title=True,
                        request_username=True,
                    ),
                    icon_custom_emoji_id=eid("GROUPS"),
                )
            ],
            [KeyboardButton(text="Отмена")],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )

support_exit_kb = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text="Завершить диалог", icon_custom_emoji_id=eid("OK"))]],
    resize_keyboard=True,
)


# ── Profile / common ───────────────────────────────────────────────────────

profile_menu = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="Мой аккаунт", callback_data="account_menu", icon_custom_emoji_id=eid("USER"))],
    [InlineKeyboardButton(text="Купить подписку", callback_data="sub_menu", icon_custom_emoji_id=eid("SUB"))],
    [InlineKeyboardButton(text="Реферальная программа", callback_data="ref_menu", icon_custom_emoji_id=eid("REF"))],
])


def account_kb(linked: bool) -> InlineKeyboardMarkup:
    if linked:
        rows = [
            [InlineKeyboardButton(
                text="Отключить публикацию",
                callback_data="account_unlink",
                icon_custom_emoji_id=eid("LOCK"),
            )],
        ]
    else:
        rows = [
            [InlineKeyboardButton(
                text="Подключить через QR",
                callback_data="account_link",
                icon_custom_emoji_id=eid("LINK"),
            )],
            [InlineKeyboardButton(
                text="Запасной способ (номер)",
                callback_data="account_link_phone",
                icon_custom_emoji_id=eid("WARN"),
            )],
        ]
    rows.append([InlineKeyboardButton(
        text="Назад в профиль",
        callback_data="back_to_profile",
        icon_custom_emoji_id=eid("BACK"),
    )])
    return InlineKeyboardMarkup(inline_keyboard=rows)

back_to_menu_kb = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="Назад в профиль", callback_data="back_to_profile", icon_custom_emoji_id=eid("BACK"))],
])


def subscription_plans_kb(plans: dict) -> InlineKeyboardMarkup:
    rows = []
    for key, plan in plans.items():
        rows.append([InlineKeyboardButton(
            text=f"{plan['title']} — {plan['stars']} ⭐",
            callback_data=f"plan_{key}",
            icon_custom_emoji_id=eid("SUB"),
        )])
    rows.append([InlineKeyboardButton(text="Назад", callback_data="back_to_profile", icon_custom_emoji_id=eid("BACK"))])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def payment_method_kb(plan_key: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Telegram Stars", callback_data=f"pay_stars_{plan_key}", icon_custom_emoji_id=eid("MONEY"))],
        [InlineKeyboardButton(text="Банковская карта", callback_data=f"pay_card_{plan_key}", icon_custom_emoji_id=eid("CARD"))],
        [InlineKeyboardButton(text="Криптовалюта", callback_data=f"pay_crypto_{plan_key}", icon_custom_emoji_id=eid("CRYPTO"))],
        [InlineKeyboardButton(text="Написать админу", callback_data="support_start", icon_custom_emoji_id=eid("SUPPORT"))],
        [InlineKeyboardButton(text="Назад", callback_data="sub_menu", icon_custom_emoji_id=eid("BACK"))],
    ])


# ── Ads ────────────────────────────────────────────────────────────────────

def skip_photo_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Без фото", callback_data="ad_skip_photo", icon_custom_emoji_id=eid("OK"))],
        [InlineKeyboardButton(text="Отмена", callback_data="ad_cancel", icon_custom_emoji_id=eid("BACK"))],
    ])


def skip_price_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Без цены", callback_data="ad_skip_price", icon_custom_emoji_id=eid("OK"))],
        [InlineKeyboardButton(text="Отмена", callback_data="ad_cancel", icon_custom_emoji_id=eid("BACK"))],
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
            icon_custom_emoji_id=eid("ADS"),
        )])
    rows.append([InlineKeyboardButton(text="Добавить", callback_data="ad_create", icon_custom_emoji_id=eid("ADD"))])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def ad_card_kb(ad) -> InlineKeyboardMarkup:
    rows = []
    if ad.status in ("draft", "paused"):
        rows.append([InlineKeyboardButton(text="Запустить", callback_data=f"ad_start_{ad.id}", icon_custom_emoji_id=eid("PLAY"))])
    if ad.status == "active":
        rows.append([InlineKeyboardButton(text="Пауза", callback_data=f"ad_pause_{ad.id}", icon_custom_emoji_id=eid("PAUSE"))])
    if ad.status != "sold":
        rows.append([InlineKeyboardButton(text="Продано", callback_data=f"ad_sold_{ad.id}", icon_custom_emoji_id=eid("SOLD"))])
    rows.append([
        InlineKeyboardButton(text="Изменить текст", callback_data=f"ad_edit_text_{ad.id}", icon_custom_emoji_id=eid("EDIT")),
        InlineKeyboardButton(text="Цена", callback_data=f"ad_edit_price_{ad.id}", icon_custom_emoji_id=eid("PRICE")),
    ])
    rows.append([InlineKeyboardButton(text="Удалить", callback_data=f"ad_del_{ad.id}", icon_custom_emoji_id=eid("DELETE"))])
    rows.append([InlineKeyboardButton(text="К списку", callback_data="ads_list", icon_custom_emoji_id=eid("BACK"))])
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
            icon_custom_emoji_id=eid("GROUPS"),
        )])
    rows.append([InlineKeyboardButton(
        text="➕ Добавить группу",
        callback_data="grp_add",
        icon_custom_emoji_id=eid("ADD"),
    )])
    rows.append([InlineKeyboardButton(
        text="Как добавить группу?",
        callback_data="grp_help",
        icon_custom_emoji_id=eid("SUPPORT"),
    )])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def group_card_kb(group) -> InlineKeyboardMarkup:
    toggle = "Выключить" if group.active else "Включить"
    toggle_icon = eid("PAUSE") if group.active else eid("PLAY")
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=toggle, callback_data=f"grp_toggle_{group.id}", icon_custom_emoji_id=toggle_icon)],
        [InlineKeyboardButton(text="Интервал", callback_data=f"grp_interval_{group.id}", icon_custom_emoji_id=eid("CLOCK"))],
        [InlineKeyboardButton(text="Удалить", callback_data=f"grp_del_{group.id}", icon_custom_emoji_id=eid("DELETE"))],
        [InlineKeyboardButton(text="К списку", callback_data="groups_list", icon_custom_emoji_id=eid("BACK"))],
    ])


# ── Autopost ───────────────────────────────────────────────────────────────

def autopost_kb(enabled: bool) -> InlineKeyboardMarkup:
    if enabled:
        btn = InlineKeyboardButton(text="Остановить автопостинг", callback_data="ap_stop", icon_custom_emoji_id=eid("PAUSE"))
    else:
        btn = InlineKeyboardButton(text="Запустить автопостинг", callback_data="ap_start", icon_custom_emoji_id=eid("PLAY"))
    return InlineKeyboardMarkup(inline_keyboard=[
        [btn],
        [InlineKeyboardButton(text="Мои объявления", callback_data="ads_list", icon_custom_emoji_id=eid("ADS"))],
        [InlineKeyboardButton(text="Мои группы", callback_data="groups_list", icon_custom_emoji_id=eid("GROUPS"))],
    ])


# ── Settings ───────────────────────────────────────────────────────────────

settings_kb = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="Интервал по умолчанию", callback_data="set_interval", icon_custom_emoji_id=eid("CLOCK"))],
    [InlineKeyboardButton(text="Тихие часы", callback_data="set_quiet", icon_custom_emoji_id=eid("SETTINGS"))],
])


# ── Admin ──────────────────────────────────────────────────────────────────

admin_menu = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="Статистика", callback_data="admin_stats", icon_custom_emoji_id=eid("STATS"))],
    [InlineKeyboardButton(text="Пользователи", callback_data="admin_users", icon_custom_emoji_id=eid("USER"))],
    [InlineKeyboardButton(text="Найти пользователя", callback_data="admin_find", icon_custom_emoji_id=eid("SEARCH"))],
    [InlineKeyboardButton(text="Выдать подписку", callback_data="admin_give_sub", icon_custom_emoji_id=eid("SUB"))],
    [InlineKeyboardButton(text="Объявления", callback_data="admin_ads", icon_custom_emoji_id=eid("ADS"))],
    [InlineKeyboardButton(text="Проблемные группы", callback_data="admin_groups", icon_custom_emoji_id=eid("GROUPS"))],
    [InlineKeyboardButton(text="Рассылка", callback_data="admin_broadcast", icon_custom_emoji_id=eid("BROADCAST"))],
    [InlineKeyboardButton(text="Саппорт", callback_data="admin_support", icon_custom_emoji_id=eid("TICKET"))],
])


def admin_user_kb(telegram_id: int, is_blocked: bool) -> InlineKeyboardMarkup:
    block_btn = (
        InlineKeyboardButton(text="Разблокировать", callback_data=f"adm_unblock_{telegram_id}", icon_custom_emoji_id=eid("UNLOCK"))
        if is_blocked else
        InlineKeyboardButton(text="Заблокировать", callback_data=f"adm_block_{telegram_id}", icon_custom_emoji_id=eid("LOCK"))
    )
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Выдать дни", callback_data=f"adm_give_{telegram_id}", icon_custom_emoji_id=eid("SUB"))],
        [block_btn],
        [InlineKeyboardButton(text="Назад", callback_data="admin_users", icon_custom_emoji_id=eid("BACK"))],
    ])


def admin_users_list_kb(users: list, offset: int = 0) -> InlineKeyboardMarkup:
    rows = []
    for u in users:
        mark = "🔒" if u.is_blocked else ("💎" if u.subscription_end else "•")
        name = f"@{u.username}" if u.username else str(u.telegram_id)
        rows.append([InlineKeyboardButton(
            text=f"{mark} {name}",
            callback_data=f"adm_user_{u.telegram_id}",
            icon_custom_emoji_id=eid("USER"),
        )])
    nav = []
    if offset > 0:
        nav.append(InlineKeyboardButton(text="◀️", callback_data=f"admin_users_{max(0, offset - 20)}"))
    nav.append(InlineKeyboardButton(text="▶️", callback_data=f"admin_users_{offset + 20}"))
    if nav:
        rows.append(nav)
    rows.append([InlineKeyboardButton(text="В админку", callback_data="admin_home", icon_custom_emoji_id=eid("BACK"))])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def support_admin_kb(ticket_id: int, telegram_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Ответить", callback_data=f"sup_reply_{ticket_id}_{telegram_id}", icon_custom_emoji_id=eid("SUPPORT"))],
        [InlineKeyboardButton(text="Закрыть тикет", callback_data=f"sup_close_{ticket_id}", icon_custom_emoji_id=eid("OK"))],
    ])


def broadcast_confirm_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Всем", callback_data="bc_all", icon_custom_emoji_id=eid("BROADCAST"))],
        [InlineKeyboardButton(text="Только с подпиской", callback_data="bc_subs", icon_custom_emoji_id=eid("SUB"))],
        [InlineKeyboardButton(text="Отмена", callback_data="admin_home", icon_custom_emoji_id=eid("BACK"))],
    ])


def admin_back_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="В админку", callback_data="admin_home", icon_custom_emoji_id=eid("BACK"))],
    ])
