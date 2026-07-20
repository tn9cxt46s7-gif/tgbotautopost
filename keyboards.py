from aiogram.types import (
    ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton
)

# Реальные ID кастомных эмодзи (из пака TgAndroidIcons, через @ShowJsonBot).
# ВАЖНО: значения передаются как int, БЕЗ кавычек — Telegram Bot API 9.4
# требует icon_custom_emoji_id как число, а не строку.
EMOJI_1 = 5875465628285931233
EMOJI_2 = 5778546023349621090
EMOJI_3 = 5931347928810526429
EMOJI_4 = 5927169041595634481

# Главное меню
main_menu = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton(text="Автопостинг", icon_custom_emoji_id=EMOJI_1),
            KeyboardButton(text="Профиль", icon_custom_emoji_id=EMOJI_2)
        ],
        [
            KeyboardButton(text="Подписка", icon_custom_emoji_id=EMOJI_3),
            KeyboardButton(text="Рефералка", icon_custom_emoji_id=EMOJI_4)
        ],
        [
            KeyboardButton(text="Мои объявления", icon_custom_emoji_id=EMOJI_1),
            KeyboardButton(text="Добавить объявление", icon_custom_emoji_id=EMOJI_2)
        ],
        [
            KeyboardButton(text="Мои группы", icon_custom_emoji_id=EMOJI_3),
            KeyboardButton(text="Настройки", icon_custom_emoji_id=EMOJI_4)
        ],
    ],
    resize_keyboard=True
)

admin_menu = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="Пользователи", callback_data="admin_users", icon_custom_emoji_id=EMOJI_1)],
    [InlineKeyboardButton(text="Выдать подписку", callback_data="admin_give_sub", icon_custom_emoji_id=EMOJI_2)]
])

profile_menu = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="Купить подписку", callback_data="sub_menu", icon_custom_emoji_id=EMOJI_3)],
    [InlineKeyboardButton(text="Реферальная программа", callback_data="ref_menu", icon_custom_emoji_id=EMOJI_4)],
])

back_to_menu_kb = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="Назад в профиль", callback_data="back_to_profile", icon_custom_emoji_id=EMOJI_1)]
])

def subscription_plans_kb(plans: dict) -> InlineKeyboardMarkup:
    rows = []
    for key, plan in plans.items():
        rows.append([InlineKeyboardButton(
            text=f"{plan['title']} — {plan['stars']} ⭐",
            callback_data=f"plan_{key}",
            icon_custom_emoji_id=plan.get("custom_emoji_id", EMOJI_2)
        )])
    rows.append([InlineKeyboardButton(text="Назад", callback_data="back_to_profile", icon_custom_emoji_id=EMOJI_3)])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def payment_method_kb(plan_key: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Telegram Stars", callback_data=f"pay_stars_{plan_key}", icon_custom_emoji_id=EMOJI_4)],
        [InlineKeyboardButton(text="Банковская карта", callback_data=f"pay_card_{plan_key}", icon_custom_emoji_id=EMOJI_1)],
        [InlineKeyboardButton(text="Криптовалюта", callback_data=f"pay_crypto_{plan_key}", icon_custom_emoji_id=EMOJI_2)],
        [InlineKeyboardButton(text="Назад", callback_data="sub_menu", icon_custom_emoji_id=EMOJI_3)],
    ])
