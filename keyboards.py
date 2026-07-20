from aiogram.types import (
    ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton
)

# Пул реальных ID кастомных эмодзи (пак TgAndroidIcons, через @ShowJsonBot).
# ВАЖНО: значения — int, БЕЗ кавычек. Telegram Bot API 9.4 требует
# icon_custom_emoji_id как число, а не строку.
EMOJI_POOL = [
    5983399041197675256, 5794182096603847292, 5794303034292968945, 5794031944547178894,
    5793901252987330401, 5794066823976592976, 5794235255414069703, 5794030595927448202,
    5794426162415409242, 5793905801357695657, 5794310013614824017, 5794342041185949794,
    5794170049220581625, 5794071015864671326, 5794348440687221181, 5794246418034072201,
    5793932490284472550, 5794335744763894508, 5794442693744531795, 5818920837645867167,
    5985630530111020079, 5769403330761593044, 5891206318353551398, 5890838600433536921,
    5890997763331591703, 5897602448075263134, 5897488197650223178, 5967591100532134862,
    5931415565955503486, 5778575233422200567, 5906995262378741881, 5958376256788502078,
    5960672896060756972, 5875180111744995604, 5841541824803509441, 5987718983728503684,
    5987802868734760945, 5854776233950188167, 5877307202888273539, 5967456680940671207,
    5877680341057015789, 5967816500415827773, 5877318502947229960, 5877396173135811032,
    5875206779196935950, 5877495434124988415, 5877738786971979125, 5891243564309942507,
    5861478929847554755, 5890741826230423364, 5897607722295103204, 5913787972200698358,
    5895434906929991182, 5897854227648090069, 5985773896119357867, 5864128984798730231,
    6008104758236156926, 5913384919584741274, 5985525909002653959, 5897846616966041652,
    5897763775636836928, 5985568880150450900, 5935968647901089910, 5988023995125993550,
    5935938364086685805, 5963213811597970978, 5985472565508838112, 5994502837327892086,
    5994485571559362460, 5992157823838984339, 5967389567781703494, 5967822972931542886,
    5927266769281487788, 5994323406479167187, 5935847413859225147, 5936130851635990622,
    5935795874251674052, 5994324703559290598, 5870734657384877785, 5994750571041525522,
    5967574255670399788, 5933768993285345899,
]


def e(i: int) -> int:
    """Возвращает ID кастомного эмодзи из пула по индексу (с циклическим повтором)."""
    return EMOJI_POOL[i % len(EMOJI_POOL)]


# Главное меню
main_menu = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton(text="Автопостинг", icon_custom_emoji_id=e(0)),
            KeyboardButton(text="Профиль", icon_custom_emoji_id=e(1))
        ],
        [
            KeyboardButton(text="Подписка", icon_custom_emoji_id=e(2)),
            KeyboardButton(text="Рефералка", icon_custom_emoji_id=e(3))
        ],
        [
            KeyboardButton(text="Мои объявления", icon_custom_emoji_id=e(4)),
            KeyboardButton(text="Добавить объявление", icon_custom_emoji_id=e(5))
        ],
        [
            KeyboardButton(text="Мои группы", icon_custom_emoji_id=e(6)),
            KeyboardButton(text="Настройки", icon_custom_emoji_id=e(7))
        ],
    ],
    resize_keyboard=True
)

admin_menu = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="Пользователи", callback_data="admin_users", icon_custom_emoji_id=e(8))],
    [InlineKeyboardButton(text="Выдать подписку", callback_data="admin_give_sub", icon_custom_emoji_id=e(9))]
])

profile_menu = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="Купить подписку", callback_data="sub_menu", icon_custom_emoji_id=e(10))],
    [InlineKeyboardButton(text="Реферальная программа", callback_data="ref_menu", icon_custom_emoji_id=e(11))],
])

back_to_menu_kb = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="Назад в профиль", callback_data="back_to_profile", icon_custom_emoji_id=e(12))]
])


def subscription_plans_kb(plans: dict) -> InlineKeyboardMarkup:
    rows = []
    for idx, (key, plan) in enumerate(plans.items()):
        rows.append([InlineKeyboardButton(
            text=f"{plan['title']} — {plan['stars']} ⭐",
            callback_data=f"plan_{key}",
            icon_custom_emoji_id=plan.get("custom_emoji_id", e(13 + idx))
        )])
    rows.append([InlineKeyboardButton(text="Назад", callback_data="back_to_profile", icon_custom_emoji_id=e(20))])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def payment_method_kb(plan_key: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Telegram Stars", callback_data=f"pay_stars_{plan_key}", icon_custom_emoji_id=e(21))],
        [InlineKeyboardButton(text="Банковская карта", callback_data=f"pay_card_{plan_key}", icon_custom_emoji_id=e(22))],
        [InlineKeyboardButton(text="Криптовалюта", callback_data=f"pay_crypto_{plan_key}", icon_custom_emoji_id=e(23))],
        [InlineKeyboardButton(text="Назад", callback_data="sub_menu", icon_custom_emoji_id=e(24))],
    ])
