from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, PreCheckoutQuery, LabeledPrice

from keyboards import (
    subscription_plans_kb, payment_method_kb,
    pending_payment_user_kb, admin_payment_kb,
)
from database import (
    extend_subscription, save_payment, create_pending_payment,
    get_payment, mark_payment_paid, cancel_payment,
)
from utils.emoji import tg_emoji
from config import (
    REFERRAL_BONUS_DAYS, PLANS, ADMIN_IDS,
    PAYMENT_CARD_DETAILS, PAYMENT_CRYPTO_DETAILS,
    SUPPORT_USERNAME,
)

router = Router()


def price_list_text() -> str:
    lines = [f"{tg_emoji('SUB')} <b>Подписка на автопостинг</b>\n"]
    for plan in PLANS.values():
        lines.append(
            f"{tg_emoji('STAR')} <b>{plan['title']}</b> — "
            f"{plan['stars']} ⭐ / <b>{plan['rub']} ₽</b>"
        )
    lines.append(
        "\nОплата: Stars сразу · карта/крипта — заявка + подтверждение админа.\n"
        f"Вопросы: @{SUPPORT_USERNAME}\n"
        "Выбери план 👇"
    )
    return "\n".join(lines)


@router.message(F.text == "Подписка")
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
        f"{tg_emoji('SUB')} <b>{plan['title']}</b>\n"
        f"{plan['stars']} ⭐ или {plan['rub']} ₽ · {plan['days']} дней\n\n"
        "Выбери способ оплаты:",
        reply_markup=payment_method_kb(plan_key),
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
        description=f"Автопостинг в барахолки на {plan['days']} дней",
        payload=f"sub:{plan_key}",
        provider_token="",
        currency="XTR",
        prices=[LabeledPrice(label=plan["title"], amount=plan["stars"])],
    )
    await callback.answer()


async def _start_manual_payment(callback: CallbackQuery, method: str):
    plan_key = callback.data.removeprefix(f"pay_{method}_")
    plan = PLANS.get(plan_key)
    if not plan:
        await callback.answer("План не найден", show_alert=True)
        return

    details = PAYMENT_CARD_DETAILS if method == "card" else PAYMENT_CRYPTO_DETAILS
    method_title = "Карта" if method == "card" else "Крипта"

    payment = await create_pending_payment(
        callback.from_user.id,
        plan_key,
        plan["stars"],
        plan["rub"],
        method,
    )

    text = (
        f"{tg_emoji('MONEY')} <b>Оплата: {method_title}</b>\n\n"
        f"План: <b>{plan['title']}</b> ({plan['days']} дн.)\n"
        f"Сумма: <b>{plan['rub']} ₽</b>\n"
        f"Заявка: <code>#{payment.id}</code>\n\n"
        f"<b>Реквизиты:</b>\n{details}\n\n"
        "1. Переведи сумму\n"
        "2. Нажми «Я оплатил»\n"
        "3. Админ подтвердит — подписка активируется\n\n"
        f"Или напиши @{SUPPORT_USERNAME} с номером заявки."
    )
    await callback.message.edit_text(text, reply_markup=pending_payment_user_kb(payment.id))
    await callback.answer()


@router.callback_query(F.data.startswith("pay_card_"))
async def pay_with_card(callback: CallbackQuery):
    await _start_manual_payment(callback, "card")


@router.callback_query(F.data.startswith("pay_crypto_"))
async def pay_with_crypto(callback: CallbackQuery):
    await _start_manual_payment(callback, "crypto")


@router.callback_query(F.data.startswith("pay_done_"))
async def pay_user_done(callback: CallbackQuery, bot: Bot):
    payment_id = int(callback.data.removeprefix("pay_done_"))
    payment = await get_payment(payment_id)
    if not payment or payment.telegram_id != callback.from_user.id:
        await callback.answer("Заявка не найдена", show_alert=True)
        return
    if payment.status != "pending":
        await callback.answer(f"Статус: {payment.status}", show_alert=True)
        return

    plan = PLANS.get(payment.plan, {})
    uname = f"@{callback.from_user.username}" if callback.from_user.username else "—"
    admin_text = (
        f"{tg_emoji('MONEY')} <b>Ожидает подтверждения</b>\n"
        f"Заявка <code>#{payment.id}</code>\n"
        f"Юзер: {uname} (<code>{payment.telegram_id}</code>)\n"
        f"План: {plan.get('title', payment.plan)} · {payment.method}\n"
        f"Сумма: {payment.amount_rub} ₽ / {payment.amount_stars} ⭐"
    )
    for admin_id in ADMIN_IDS:
        try:
            await bot.send_message(
                admin_id,
                admin_text,
                reply_markup=admin_payment_kb(payment.id),
            )
        except Exception:
            pass

    await callback.message.edit_text(
        f"{tg_emoji('OK')} Заявка #{payment.id} отправлена админу.\n"
        "Подписка включится после проверки оплаты.\n"
        f"Можно написать @{SUPPORT_USERNAME}."
    )
    await callback.answer("Отправлено админу")


@router.callback_query(F.data.startswith("pay_cancel_"))
async def pay_user_cancel(callback: CallbackQuery):
    payment_id = int(callback.data.removeprefix("pay_cancel_"))
    payment = await get_payment(payment_id)
    if not payment or payment.telegram_id != callback.from_user.id:
        await callback.answer("Не найдено", show_alert=True)
        return
    if payment.status != "pending":
        await callback.answer("Уже обработана", show_alert=True)
        return
    await cancel_payment(payment_id)
    await callback.message.edit_text(f"{tg_emoji('OK')} Заявка #{payment_id} отменена.")
    await callback.answer("Отменено")


@router.callback_query(F.data.startswith("adm_pay_ok_"))
async def admin_confirm_payment(callback: CallbackQuery, bot: Bot):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("Нет доступа", show_alert=True)
        return
    payment_id = int(callback.data.removeprefix("adm_pay_ok_"))
    payment = await get_payment(payment_id)
    if not payment or payment.status != "pending":
        await callback.answer("Заявка недоступна", show_alert=True)
        return

    plan = PLANS.get(payment.plan)
    if not plan:
        await callback.answer("План неизвестен", show_alert=True)
        return

    await mark_payment_paid(payment_id)
    user = await extend_subscription(payment.telegram_id, payment.plan, plan["days"])

    try:
        await bot.send_message(
            payment.telegram_id,
            f"{tg_emoji('OK')} Оплата подтверждена!\n"
            f"Подписка «{plan['title']}» до "
            f"<b>{user.subscription_end.strftime('%d.%m.%Y')}</b>\n"
            "Можно запускать автопостинг.",
        )
    except Exception:
        pass

    if user and user.referrer_id:
        try:
            await extend_subscription(user.referrer_id, "bonus", REFERRAL_BONUS_DAYS)
            await bot.send_message(
                user.referrer_id,
                f"{tg_emoji('FIRE')} Реферал оплатил подписку! +{REFERRAL_BONUS_DAYS} дня.",
            )
        except Exception:
            pass

    await callback.message.edit_text(
        callback.message.text + f"\n\n✅ Подтверждено ({callback.from_user.id})"
    )
    await callback.answer("Подписка выдана")


@router.callback_query(F.data.startswith("adm_pay_no_"))
async def admin_reject_payment(callback: CallbackQuery, bot: Bot):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("Нет доступа", show_alert=True)
        return
    payment_id = int(callback.data.removeprefix("adm_pay_no_"))
    payment = await get_payment(payment_id)
    if not payment or payment.status != "pending":
        await callback.answer("Заявка недоступна", show_alert=True)
        return
    await cancel_payment(payment_id)
    try:
        await bot.send_message(
            payment.telegram_id,
            f"{tg_emoji('WARN')} Заявка #{payment_id} отклонена.\n"
            f"Напиши @{SUPPORT_USERNAME}, если это ошибка.",
        )
    except Exception:
        pass
    await callback.message.edit_text(
        callback.message.text + f"\n\n❌ Отклонено ({callback.from_user.id})"
    )
    await callback.answer("Отклонено")


@router.pre_checkout_query()
async def process_pre_checkout(pre_checkout_query: PreCheckoutQuery):
    await pre_checkout_query.answer(ok=True)


@router.message(F.successful_payment)
async def process_successful_payment(message: Message):
    payload = message.successful_payment.invoice_payload
    plan_key = payload.split(":")[1] if ":" in payload else None
    plan = PLANS.get(plan_key)

    if not plan:
        await message.answer(
            f"Оплата прошла, но план не распознан. Напиши @{SUPPORT_USERNAME}."
        )
        return

    stars_paid = message.successful_payment.total_amount
    await save_payment(
        message.from_user.id,
        plan_key,
        stars_paid,
        method="stars",
        amount_rub=plan.get("rub", 0),
        status="paid",
    )
    user = await extend_subscription(message.from_user.id, plan_key, plan["days"])

    await message.answer(
        f"{tg_emoji('OK')} Оплата на {stars_paid} ⭐ прошла успешно!\n"
        f"Подписка «{plan['title']}» активна до "
        f"<b>{user.subscription_end.strftime('%d.%m.%Y')}</b>\n\n"
        f"{tg_emoji('AUTO')} Можно запускать автопостинг!"
    )

    if user and user.referrer_id:
        try:
            await message.bot.send_message(
                user.referrer_id,
                f"{tg_emoji('FIRE')} Твой реферал оплатил подписку!\n"
                f"Начислено <b>+{REFERRAL_BONUS_DAYS} дня</b> подписки.",
            )
            await extend_subscription(user.referrer_id, "bonus", REFERRAL_BONUS_DAYS)
        except Exception:
            pass
