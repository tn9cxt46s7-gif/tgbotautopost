from aiogram.types import (
    ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton
)

main_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🚀 Автопостинг"), KeyboardButton(text="👤 Профиль")],
        [KeyboardButton(text="💎 Подписка"), KeyboardButton(text="🔗 Рефералка")],
        [KeyboardButton(text="📝 Мои объявления"), KeyboardButton(text="➕ Добавить объявление")],
        [KeyboardButton(text="👥 Мои группы"), KeyboardButton(text="⚙️ Настройки")],
    ],
    resize_keyboard=True
)

admin_menu = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="👥 Пользователи", callback_data="admin_users")],
    [InlineKeyboardButton(text="💰 Выдать подписку", callback_data="admin_give_sub")]
])

profile_menu = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="💎 Купить подписку", callback_data="sub_menu")],
    [InlineKeyboardButton(text="🔗 Реферальная программа", callback_data="ref_menu")],
])

back_to_menu_kb = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="◀️ В профиль", callback_data="back_to_profile")]
])


def subscription_plans_kb(plans: dict) -> InlineKeyboardMarkup:
    rows = []
    for key, plan in plans.items():
        rows.append([InlineKeyboardButton(
            text=f"{plan['emoji']} {plan['title']} — {plan['stars']} ⭐",
            callback_data=f"plan_{key}"
        )])
    rows.append([InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_profile")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def payment_method_kb(plan_key: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⭐ Telegram Stars", callback_data=f"pay_stars_{plan_key}")],
        [InlineKeyboardButton(text="💳 Банковская карта", callback_data=f"pay_card_{plan_key}")],
        [InlineKeyboardButton(text="₿ Криптовалюта", callback_data=f"pay_crypto_{plan_key}")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="sub_menu")],
    ])
