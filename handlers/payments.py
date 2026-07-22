from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, PreCheckoutQuery, LabeledPrice, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext

from keyboards import (
    subscription_plans_kb, payment_method_kb,
    pending_payment_user_kb, admin_payment_kb,
)
from database import (
    extend_subscription, save_payment, create_pending_payment,
    get_payment, mark_payment_paid, cancel_payment, update_payment,
    get_promo, promo_is_valid, apply_discount, use_promo,
    get_payment_by_external_id,
)
from utils.emoji import tg_emoji, eid
from config import (
    REFERRAL_BONUS_DAYS, PLANS, ADMIN_IDS,
    PAYMENT_CARD_DETAILS, PAYMENT_CRYPTO_DETAILS,
    SUPPORT_USERNAME, SUPPORT_URL,
)
from services.cryptobot import cryptobot_configured, create_invoice, get_invoice
from states import PromoApply

router = Router()


def _priced(plan: dict, discount: int = 0) -> tuple[int, int]:
    stars = apply_discount(plan["stars"], discount)
    rub = apply_discount(plan["rub"], discount)
    return stars, rub


def price_list_text(discount: int = 0, promo: str | None = None) -> str:
    lines = [f"{tg_emoji('SUB')} <b>Подписка · барахолки Латвии</b> 🇱🇻\n"]
    if promo and discount:
        lines.append(f"🎟 Промокод <code>{promo}</code>: −{discount}%\n")
    for plan in PLANS.values():
        stars, rub = _priced(plan, discount)
        if discount:
            lines.append(
                f"{tg_emoji('STAR')} <b>{plan['title']}</b> — "
                f"<s>{plan['stars']}⭐/{plan['rub']}₽</s> → <b>{stars}⭐ / {rub}₽</b>"
            )
        else:
            lines.append(
                f"{tg_emoji('STAR')} <b>{plan['title']}</b> — "
                f"{plan['stars']} ⭐ / <b>{plan['rub']} ₽</b>"
            )
    auto = "CryptoBot ✅" if cryptobot_configured() else "CryptoBot (нужен токен)"
    lines.append(
        f"\nОплата: Stars сразу · {auto} · карта (ручное подтверждение)\n"
        f"Промокоды: START20, SALE15, VIP30\n"
        f"Саппорт: @{SUPPORT_USERNAME}\n"
        "Выбери план 👇"
    )
    return "\n".join(lines)


def _plans_kb_with_promo():
    return subscription_plans_kb(PLANS, show_promo=True)


@router.message(F.text == "Подписка")
async def show_plans_msg(message: Message, state: FSMContext):
    data = await state.get_data()
    await message.answer(
        price_list_text(data.get("discount_percent", 0), data.get("promo_code")),
        reply_markup=_plans_kb_with_promo(),
    )


@router.callback_query(F.data == "sub_menu")
async def show_plans_cb(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    await callback.message.edit_text(
        price_list_text(data.get("discount_percent", 0), data.get("promo_code")),
        reply_markup=_plans_kb_with_promo(),
    )
    await callback.answer()


@router.callback_query(F.data == "promo_enter")
async def promo_enter(callback: CallbackQuery, state: FSMContext):
    await state.set_state(PromoApply.waiting)
    await callback.message.answer(
        f"{tg_emoji('FIRE')} Введи промокод (например <code>START20</code>):"
    )
    await callback.answer()


@router.message(PromoApply.waiting)
async def promo_apply(message: Message, state: FSMContext):
    code = (message.text or "").strip().upper()
    promo = await get_promo(code)
    ok, reason = promo_is_valid(promo)
    if not ok:
        await message.answer(f"{tg_emoji('WARN')} {reason}")
        return
    await state.update_data(promo_code=promo.code, discount_percent=promo.discount_percent)
    await state.set_state(None)
    await message.answer(
        f"{tg_emoji('OK')} Промокод <b>{promo.code}</b> −{promo.discount_percent}%!\n"
        "Выбери план:",
        reply_markup=_plans_kb_with_promo(),
    )
    await message.answer(price_list_text(promo.discount_percent, promo.code))


@router.callback_query(F.data.startswith("plan_"))
async def choose_payment_method(callback: CallbackQuery, state: FSMContext):
    plan_key = callback.data.removeprefix("plan_")
    plan = PLANS.get(plan_key)
    if not plan:
        await callback.answer("План не найден", show_alert=True)
        return

    data = await state.get_data()
    discount = int(data.get("discount_percent") or 0)
    promo = data.get("promo_code")
    if promo:
        p = await get_promo(promo)
        ok, reason = promo_is_valid(p, plan_key)
        if not ok:
            discount = 0
            promo = None
            await state.update_data(promo_code=None, discount_percent=0)

    stars, rub = _priced(plan, discount)
    disc_line = f"\n🎟 Скидка {discount}% → <b>{stars}⭐ / {rub}₽</b>" if discount else ""

    await callback.message.edit_text(
        f"{tg_emoji('SUB')} <b>{plan['title']}</b>\n"
        f"{plan['stars']} ⭐ / {plan['rub']} ₽ · {plan['days']} дней{disc_line}\n\n"
        "Выбери способ оплаты:",
        reply_markup=payment_method_kb(plan_key, cryptobot=cryptobot_configured()),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("pay_stars_"))
async def pay_with_stars(callback: CallbackQuery, state: FSMContext):
    plan_key = callback.data.removeprefix("pay_stars_")
    plan = PLANS.get(plan_key)
    if not plan:
        await callback.answer("План не найден", show_alert=True)
        return
    data = await state.get_data()
    discount = int(data.get("discount_percent") or 0)
    stars, _ = _priced(plan, discount)
    promo = data.get("promo_code") or ""
    payload = f"sub:{plan_key}:{discount}:{promo}"

    await callback.message.answer_invoice(
        title=f"Подписка «{plan['title']}»",
        description=f"Автопостинг на {plan['days']} дней" + (f" (−{discount}%)" if discount else ""),
        payload=payload,
        provider_token="",
        currency="XTR",
        prices=[LabeledPrice(label=plan["title"], amount=stars)],
    )
    await callback.answer()


@router.callback_query(F.data.startswith("pay_cryptobot_"))
async def pay_with_cryptobot(callback: CallbackQuery, state: FSMContext, bot: Bot):
    if not cryptobot_configured():
        await callback.answer("CryptoBot ещё не подключён. Напиши @eb_support", show_alert=True)
        return
    plan_key = callback.data.removeprefix("pay_cryptobot_")
    plan = PLANS.get(plan_key)
    if not plan:
        await callback.answer("План не найден", show_alert=True)
        return

    data = await state.get_data()
    discount = int(data.get("discount_percent") or 0)
    promo = data.get("promo_code")
    stars, rub = _priced(plan, discount)

    payment = await create_pending_payment(
        callback.from_user.id,
        plan_key,
        stars,
        rub,
        "cryptobot",
        promo_code=promo,
        discount_percent=discount,
    )

    me = await bot.get_me()
    try:
        invoice = await create_invoice(
            amount_rub=rub,
            description=f"{plan['title']} · {plan['days']}д · #{payment.id}",
            payload=f"pay:{payment.id}:{callback.from_user.id}:{plan_key}",
            paid_btn_url=f"https://t.me/{me.username}",
        )
    except Exception as e:
        await cancel_payment(payment.id)
        await callback.answer(f"Ошибка CryptoBot: {e}", show_alert=True)
        return

    invoice_id = str(invoice.get("invoice_id") or invoice.get("id") or "")
    pay_url = invoice.get("bot_invoice_url") or invoice.get("pay_url") or invoice.get("mini_app_invoice_url")
    await update_payment(payment.id, external_id=invoice_id, pay_url=pay_url)

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Оплатить в CryptoBot", url=pay_url)],
        [InlineKeyboardButton(
            text="Проверить оплату",
            callback_data=f"pay_check_{payment.id}",
            icon_custom_emoji_id=eid("OK"),
        )],
        [InlineKeyboardButton(
            text=f"Support @{SUPPORT_USERNAME}",
            url=SUPPORT_URL,
        )],
    ])
    await callback.message.edit_text(
        f"{tg_emoji('CRYPTO')} <b>CryptoBot · автооплата</b>\n\n"
        f"План: <b>{plan['title']}</b>\n"
        f"К оплате: <b>{rub} ₽</b>"
        + (f" (−{discount}%)" if discount else "")
        + f"\nЗаявка: <code>#{payment.id}</code>\n\n"
        "1. Нажми «Оплатить в CryptoBot»\n"
        "2. Оплати USDT / TON\n"
        "3. Подписка активируется сама (или нажми «Проверить оплату»)",
        reply_markup=kb,
    )
    await callback.answer()


@router.callback_query(F.data.startswith("pay_check_"))
async def pay_check_cryptobot(callback: CallbackQuery, bot: Bot, state: FSMContext):
    payment_id = int(callback.data.removeprefix("pay_check_"))
    payment = await get_payment(payment_id)
    if not payment or payment.telegram_id != callback.from_user.id:
        await callback.answer("Не найдено", show_alert=True)
        return
    if payment.status == "paid":
        await callback.answer("Уже оплачено ✅", show_alert=True)
        return
    if not payment.external_id:
        await callback.answer("Нет invoice", show_alert=True)
        return
    try:
        inv = await get_invoice(payment.external_id)
    except Exception as e:
        await callback.answer(f"Ошибка: {e}", show_alert=True)
        return
    if not inv or inv.get("status") != "paid":
        await callback.answer("Пока не оплачено. Подожди минуту.", show_alert=True)
        return
    await _activate_paid(bot, payment, state)
    await callback.answer("Оплата найдена!", show_alert=True)
    await callback.message.edit_text(
        f"{tg_emoji('OK')} Оплата CryptoBot подтверждена. Подписка активна!"
    )


async def _start_manual_payment(callback: CallbackQuery, method: str, state: FSMContext):
    plan_key = callback.data.removeprefix(f"pay_{method}_")
    plan = PLANS.get(plan_key)
    if not plan:
        await callback.answer("План не найден", show_alert=True)
        return

    data = await state.get_data()
    discount = int(data.get("discount_percent") or 0)
    promo = data.get("promo_code")
    stars, rub = _priced(plan, discount)

    details = PAYMENT_CARD_DETAILS if method == "card" else PAYMENT_CRYPTO_DETAILS
    method_title = "Карта" if method == "card" else "Крипта (ручная)"

    payment = await create_pending_payment(
        callback.from_user.id,
        plan_key,
        stars,
        rub,
        method,
        promo_code=promo,
        discount_percent=discount,
    )

    text = (
        f"{tg_emoji('MONEY')} <b>Оплата: {method_title}</b>\n\n"
        f"План: <b>{plan['title']}</b> ({plan['days']} дн.)\n"
        f"Сумма: <b>{rub} ₽</b>"
        + (f" (−{discount}%)" if discount else "")
        + f"\nЗаявка: <code>#{payment.id}</code>\n\n"
        f"<b>Реквизиты:</b>\n{details}\n\n"
        "1. Переведи сумму\n"
        "2. Нажми «Я оплатил»\n"
        "3. Админ подтвердит\n\n"
        f"Или @{SUPPORT_USERNAME} с номером заявки."
    )
    await callback.message.edit_text(text, reply_markup=pending_payment_user_kb(payment.id))
    await callback.answer()


@router.callback_query(F.data.startswith("pay_card_"))
async def pay_with_card(callback: CallbackQuery, state: FSMContext):
    await _start_manual_payment(callback, "card", state)


@router.callback_query(F.data.startswith("pay_crypto_"))
async def pay_with_crypto(callback: CallbackQuery, state: FSMContext):
    await _start_manual_payment(callback, "crypto", state)


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
        f"Сумма: {payment.amount_rub} ₽"
        + (f" (−{payment.discount_percent}%)" if payment.discount_percent else "")
    )
    for admin_id in ADMIN_IDS:
        try:
            await bot.send_message(admin_id, admin_text, reply_markup=admin_payment_kb(payment.id))
        except Exception:
            pass

    await callback.message.edit_text(
        f"{tg_emoji('OK')} Заявка #{payment.id} отправлена админу.\n"
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


async def _activate_paid(bot: Bot, payment, state: FSMContext | None = None):
    if payment.status == "paid":
        return
    plan = PLANS.get(payment.plan)
    if not plan:
        return
    await mark_payment_paid(payment.id)
    if payment.promo_code:
        await use_promo(payment.promo_code)
    user = await extend_subscription(payment.telegram_id, payment.plan, plan["days"])
    if state:
        await state.update_data(promo_code=None, discount_percent=0)
    try:
        await bot.send_message(
            payment.telegram_id,
            f"{tg_emoji('OK')} Оплата подтверждена!\n"
            f"Подписка «{plan['title']}» до "
            f"<b>{user.subscription_end.strftime('%d.%m.%Y')}</b>",
        )
    except Exception:
        pass
    if user and user.referrer_id:
        try:
            await extend_subscription(user.referrer_id, "bonus", REFERRAL_BONUS_DAYS)
            await bot.send_message(
                user.referrer_id,
                f"{tg_emoji('FIRE')} Реферал оплатил! +{REFERRAL_BONUS_DAYS} дня.",
            )
        except Exception:
            pass


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
    await _activate_paid(bot, payment)
    await callback.message.edit_text(
        (callback.message.text or "") + f"\n\n✅ Подтверждено ({callback.from_user.id})"
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
            f"Напиши @{SUPPORT_USERNAME}.",
        )
    except Exception:
        pass
    await callback.message.edit_text(
        (callback.message.text or "") + f"\n\n❌ Отклонено ({callback.from_user.id})"
    )
    await callback.answer("Отклонено")


@router.pre_checkout_query()
async def process_pre_checkout(pre_checkout_query: PreCheckoutQuery):
    await pre_checkout_query.answer(ok=True)


@router.message(F.successful_payment)
async def process_successful_payment(message: Message, state: FSMContext):
    payload = message.successful_payment.invoice_payload or ""
    parts = payload.split(":")
    plan_key = parts[1] if len(parts) > 1 else None
    discount = int(parts[2]) if len(parts) > 2 and parts[2].isdigit() else 0
    promo = parts[3] if len(parts) > 3 and parts[3] else None
    plan = PLANS.get(plan_key)

    if not plan:
        await message.answer(f"Оплата прошла, план не распознан. @{SUPPORT_USERNAME}")
        return

    stars_paid = message.successful_payment.total_amount
    rub = apply_discount(plan["rub"], discount)
    await save_payment(
        message.from_user.id,
        plan_key,
        stars_paid,
        method="stars",
        amount_rub=rub,
        status="paid",
        promo_code=promo,
        discount_percent=discount,
    )
    if promo:
        await use_promo(promo)
    user = await extend_subscription(message.from_user.id, plan_key, plan["days"])
    await state.update_data(promo_code=None, discount_percent=0)

    await message.answer(
        f"{tg_emoji('OK')} Оплата на {stars_paid} ⭐ успешна!\n"
        f"Подписка «{plan['title']}» до "
        f"<b>{user.subscription_end.strftime('%d.%m.%Y')}</b>"
    )

    if user and user.referrer_id:
        try:
            await message.bot.send_message(
                user.referrer_id,
                f"{tg_emoji('FIRE')} Реферал оплатил! +{REFERRAL_BONUS_DAYS} дня.",
            )
            await extend_subscription(user.referrer_id, "bonus", REFERRAL_BONUS_DAYS)
        except Exception:
            pass


async def activate_from_cryptobot_webhook(bot: Bot, invoice: dict) -> bool:
    """Called from /cryptobot-webhook when invoice_paid."""
    payload = invoice.get("payload") or ""
    # pay:{payment_id}:{user_id}:{plan}
    if payload.startswith("pay:"):
        parts = payload.split(":")
        payment_id = int(parts[1])
        payment = await get_payment(payment_id)
    else:
        payment = await get_payment_by_external_id(str(invoice.get("invoice_id")))
    if not payment or payment.status == "paid":
        return False
    await _activate_paid(bot, payment)
    return True
