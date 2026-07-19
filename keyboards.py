from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

main_menu = ReplyKeyboardMarkup(keyboard=[
    [KeyboardButton(text="📝 Мои объявления")],
    [KeyboardButton(text="➕ Добавить объявление")],
    [KeyboardButton(text="👥 Мои группы")],
    [KeyboardButton(text="⏰ Настройки интервала")]
], resize_keyboard=True)

admin_menu = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="👥 Пользователи", callback_data="admin_users")],
    [InlineKeyboardButton(text="💰 Выдать подписку", callback_data="admin_give_sub")]
])