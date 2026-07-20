from aiogram.types import (
    ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton
)

# ВАЖНО: Замените 'ВАШ_EMOJI_ID' на числовые ID эмодзи, 
# полученные из пака TgAndroidIcons (через бот @ShowJsonBot).

# Главное меню
main_menu = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton(text="Автопостинг", icon_custom_emoji_id="8414329140"),
            KeyboardButton(text="Профиль", icon_custom_emoji_id="ВАШ_EMOJI_ID")
        ],
        [
            KeyboardButton(text="Подписка", icon_custom_emoji_id="ВАШ_EMOJI_ID"),
            KeyboardButton(text="Рефералка", icon_custom_emoji_id="ВАШ_EMOJI_ID")
        ],
        [
            KeyboardButton(text="Мои объявления", icon_custom_emoji_id="ВАШ_EMOJI_ID"),
            KeyboardButton(text="Добавить объявление", icon_custom_emoji_id="ВАШ_EMOJI_ID")
        ],
        [
            KeyboardButton(text="Мои группы", icon_custom_emoji_id="ВАШ_EMOJI_ID"),
            KeyboardButton(text="Настройки", icon_custom_emoji_id="ВАШ_EMOJI_ID")
        ],
    ],
    resize_keyboard=True
)

admin_menu = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="Пользователи", callback_data="admin_users", icon_custom_emoji_id="ВАШ_EMOJI_ID")],
    [InlineKeyboardButton(text="Выдать подписку", callback_data="admin_give_sub", icon_custom_emoji_id="ВАШ_EMOJI_ID")]
])

profile_menu = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="Купить подписку", callback_data="sub_menu", icon_custom_emoji_id="ВАШ_EMOJI_ID")],
    [InlineKeyboardButton(text="Реферальная программа", callback_data="ref_menu", icon_custom_emoji_id="ВАШ_EMOJI_ID")],
])

back_to_menu_kb = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="Назад в профиль", callback_data="back_to_profile", icon_custom_emoji_id="ВАШ_EMOJI_ID")]
])

def subscription_plans_kb(plans: dict) -> InlineKeyboardMarkup:
    rows = []
    for key, plan in plans.items():
        rows.append([InlineKeyboardButton(
            text=f"{plan['title']} — {plan['stars']} ⭐",
            callback_data=f"plan_{key}",
            icon_custom_emoji_id=plan.get("custom_emoji_id", "ВАШ_EMOJI_ID")
        )])
    rows.append([InlineKeyboardButton(text="Назад", callback_data="back_to_profile", icon_custom_emoji_id="ВАШ_EMOJI_ID")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def payment_method_kb(plan_key: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Telegram Stars", callback_data=f"pay_stars_{plan_key}", icon_custom_emoji_id="ВАШ_EMOJI_ID")],
        [InlineKeyboardButton(text="Банковская карта", callback_data=f"pay_card_{plan_key}", icon_custom_emoji_id="ВАШ_EMOJI_ID")],
        [InlineKeyboardButton(text="Криптовалюта", callback_data=f"pay_crypto_{plan_key}", icon_custom_emoji_id="ВАШ_EMOJI_ID")],
        [InlineKeyboardButton(text="Назад", callback_data="sub_menu", icon_custom_emoji_id="ВАШ_EMOJI_ID")],
    ])
