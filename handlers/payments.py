from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, PreCheckoutQuery, LabeledPrice

from keyboards import subscription_plans_kb, payment_method_kb
from database import extend_subscription, save_payment

router = Router()

PLANS = {
    "week":    {"title": "Неделя",   "emoji": "🔹", "days": 7,  "stars": 150},
    "month":   {"title": "Месяц",    "emoji": "💠", "days": 30, "stars": 450},
    "quarter": {"title": "3 месяца", "emoji": "💎", "days": 90, "stars": 1100},
}


def price_list_text() -> str:
    lines = ["💎 <b>Прайс-лист подписки</b>\n"]
    for plan in PLANS.values():
        lines.append(f"{plan['emoji']} {plan['title']} — <b>{plan['stars']} ⭐</b>")
    lines.append("\nВыбери план ниже 👇")
    return "\n".join(lines)


@router.message(F.text == "💎 Подписка")
async def show_plans_msg(message: Message):
    await message.answer(price_list_text(), reply_markup=subscription_plans_kb(PLANS))


@router.callback_query(F.data == "sub_menu")
async def show_plans_cb(callback: CallbackQuery):
    await callback.message.edit_text(price_list_text(), reply_markup=subscription_plans_kb(PLANS))
    await callback.answer()


@router.callback_query(F.data.startswith("plan_"))
async def choose_payment_method(callback: CallbackQuery):
    plan_key = callback.data.removeprefix("plan_")
    plan = PLANS.get(plan_key)
    if not plan:
        await callback.answer("План не найден", show_alert=True)
        return

    await callback.message.edit_text(
        f"{plan['emoji']} <b>{plan['title']}</b> — {plan['stars']} ⭐\n\n"
        "Выбери способ оплаты:",
        reply_markup=payment_method_kb(plan_key)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("pay_stars_"))
async def pay_with_stars(callback: CallbackQuery):
    plan_key = callback.data.removeprefix("pay_stars_")
    plan = PLANS.get(plan_key)
    if not plan:
        await callback.answer("План не найден", show_alert=True)
        return

    await callback.message.answer_invoice(
        title=f"Подписка «{plan['title']}»",
        description=f"Доступ к автопостингу на {plan['days']} дней",
        payload=f"sub:{plan_key}",
        provider_token="",
        currency="XTR",
        prices=[LabeledPrice(label=plan["title"], amount=plan["stars"])],
    )
    await callback.answer()


@router.callback_query(F.data.startswith("pay_card_"))
async def pay_with_card(callback: CallbackQuery):
    await callback.answer(
        "💳 Оплата картой скоро будет подключена. Пока напиши админу для ручной оплаты.",
        show_alert=True
    )


@router.callback_query(F.data.startswith("pay_crypto_"))
async def pay_with_crypto(callback: CallbackQuery):
    await callback.answer(
        "₿ Оплата криптовалютой скоро будет подключена. Пока напиши админу для ручной оплаты.",
        show_alert=True
    )


@router.pre_checkout_query()
async def process_pre_checkout(pre_checkout_query: PreCheckoutQuery):
    await pre_checkout_query.answer(ok=True)


@router.message(F.successful_payment)
async def process_successful_payment(message: Message):
    payload = message.successful_payment.invoice_payload
    plan_key = payload.split(":")[1] if ":" in payload else None
    plan = PLANS.get(plan_key)

    if not plan:
        await message.answer("Оплата прошла, но план не распознан. Напиши админу — разберёмся.")
        return

    stars_paid = message.successful_payment.total_amount
    await save_payment(message.from_user.id, plan_key, stars_paid, method="stars")
    user = await extend_subscription(message.from_user.id, plan_key, plan["days"])

    await message.answer(
        f"✅ Оплата на {stars_paid} ⭐ прошла успешно!\n"
        f"Подписка «{plan['title']}» активна до "
        f"<b>{user.subscription_end.strftime('%d.%m.%Y')}</b>\n\n"
        "Спасибо, что пользуешься ботом! 🚀"
    )

    if user.referrer_id:
        try:
            await message.bot.send_message(
                user.referrer_id,
                "🎉 Твой реферал оплатил подписку!\n"
                "В благодарность тебе начислено <b>+3 дня</b> подписки."
            )
            await extend_subscription(user.referrer_id, "bonus", 3)
        except Exception:
            pass
