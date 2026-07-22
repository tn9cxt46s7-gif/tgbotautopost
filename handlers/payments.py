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
    get_payment_by_external_id, get_user,
)
from utils.emoji import tg_emoji
from utils.i18n import t, plan_title, all_btn
from config import (
    REFERRAL_BONUS_DAYS, PLANS, ADMIN_IDS,
    PAYMENT_CARD_DETAILS, PAYMENT_CRYPTO_DETAILS, PAYMENT_BANKS_OTHER,
    SUPPORT_USERNAME, SUPPORT_URL,
)
from services.cryptobot import cryptobot_configured, create_invoice, get_invoice
from states import PromoApply

router = Router()


async def _ulang(telegram_id: int) -> str:
    user = await get_user(telegram_id)
    return (user.language if user and user.language else "ru")


def _priced(plan: dict, discount: int = 0) -> tuple[int, int]:
    """Return (stars, eur). amount_rub DB column stores EUR."""
    stars = apply_discount(plan["stars"], discount)
    eur = apply_discount(plan.get("eur") or plan["rub"], discount)
    return stars, eur


def price_list_text(discount: int = 0, promo: str | None = None, lang: str = "ru") -> str:
    crown = tg_emoji("CROWN", force=True)
    cash = tg_emoji("CASH", force=True)
    lines = [
        f"{crown} <b>Premium · Latvia</b> 🇱🇻\n"
        f"{cash} EUR\n"
    ]
    # keep i18n header nuance
    header = t("price_header", lang)
    # replace plain crown if present — header already has 👑
    lines = [header.replace("👑", crown).replace("💎", crown)]
    if promo and discount:
        lines.append(f"{tg_emoji('PROMO', force=True)} <code>{promo}</code>: −{discount}%\n")
    for key, plan in PLANS.items():
        _, eur = _priced(plan, discount)
        title = plan_title(key, lang)
        base_eur = plan.get("eur") or plan["rub"]
        icon_key = {"week": "PLAN_WEEK", "month": "PLAN_MONTH", "quarter": "PLAN_QUARTER"}.get(key, "GEM")
        icon = tg_emoji(icon_key, force=True)
        if discount:
            lines.append(
                f"{icon} <b>{title}</b> — <s>{base_eur} €</s> → <b>{eur} €</b>"
            )
        else:
            lines.append(f"{icon} <b>{title}</b> — <b>{eur} €</b>")
    auto = f"{tg_emoji('CRYPTOBOT', force=True)} CryptoBot ✅" if cryptobot_configured() else f"{tg_emoji('CRYPTOBOT', force=True)} CryptoBot"
    lines.append(
        f"\n{auto}\n"
        + t("pay_methods_hint", lang, support=SUPPORT_USERNAME)
        + "\n"
        + t("choose_plan", lang)
    )
    return "\n".join(lines)


def _plans_kb_with_promo(lang: str = "ru"):
    return subscription_plans_kb(PLANS, show_promo=True, lang=lang)


@router.message(F.text.in_(all_btn("sub")))
async def show_plans_msg(message: Message, state: FSMContext):
    lang = await _ulang(message.from_user.id)
    data = await state.get_data()
    await message.answer(
        price_list_text(data.get("discount_percent", 0), data.get("promo_code"), lang),
        reply_markup=_plans_kb_with_promo(lang),
    )


@router.callback_query(F.data == "sub_menu")
async def show_plans_cb(callback: CallbackQuery, state: FSMContext):
    lang = await _ulang(callback.from_user.id)
    data = await state.get_data()
    await callback.answer()
    await callback.message.edit_text(
        price_list_text(data.get("discount_percent", 0), data.get("promo_code"), lang),
        reply_markup=_plans_kb_with_promo(lang),
    )


@router.callback_query(F.data == "promo_enter")
async def promo_enter(callback: CallbackQuery, state: FSMContext):
    await state.set_state(PromoApply.waiting)
    await callback.answer()
    await callback.message.answer(f"{tg_emoji('FIRE')} Promo code (e.g. <code>START20</code>):")


@router.message(PromoApply.waiting)
async def promo_apply(message: Message, state: FSMContext):
    lang = await _ulang(message.from_user.id)
    code = (message.text or "").strip().upper()
    promo = await get_promo(code)
    ok, reason = promo_is_valid(promo)
    if not ok:
        await message.answer(f"{tg_emoji('WARN')} {reason}")
        return
    await state.update_data(promo_code=promo.code, discount_percent=promo.discount_percent)
    await state.set_state(None)
    await message.answer(
        f"{tg_emoji('OK')} <b>{promo.code}</b> −{promo.discount_percent}%\n"
        + t("choose_plan", lang),
        reply_markup=_plans_kb_with_promo(lang),
    )
    await message.answer(price_list_text(promo.discount_percent, promo.code, lang))


@router.callback_query(F.data.startswith("plan_"))
async def choose_payment_method(callback: CallbackQuery, state: FSMContext):
    await callback.answer()  # fast ack — reduces perceived lag
    plan_key = callback.data.removeprefix("plan_")
    plan = PLANS.get(plan_key)
    if not plan:
        return
    lang = await _ulang(callback.from_user.id)

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

    _, eur = _priced(plan, discount)
    title = plan_title(plan_key, lang)
    base = plan.get("eur") or plan["rub"]
    disc_line = f"\n🎟 −{discount}% → <b>{eur} €</b>" if discount else ""

    await callback.message.edit_text(
        f"{tg_emoji('CROWN', force=True)} <b>{title}</b>\n"
        f"{tg_emoji('CASH', force=True)} <b>{base} €</b> · {plan['days']}d{disc_line}\n\n"
        + t("choose_pay", lang),
        reply_markup=payment_method_kb(plan_key, cryptobot=cryptobot_configured(), lang=lang),
    )


@router.callback_query(F.data.startswith("pay_stars_"))
async def pay_with_stars(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    plan_key = callback.data.removeprefix("pay_stars_")
    plan = PLANS.get(plan_key)
    if not plan:
        return
    lang = await _ulang(callback.from_user.id)
    data = await state.get_data()
    discount = int(data.get("discount_percent") or 0)
    stars, _ = _priced(plan, discount)
    promo = data.get("promo_code") or ""
    payload = f"sub:{plan_key}:{discount}:{promo}"
    title = plan_title(plan_key, lang)

    await callback.message.answer_invoice(
        title=f"{title}",
        description=f"Autopost {plan['days']}d" + (f" (−{discount}%)" if discount else ""),
        payload=payload,
        provider_token="",
        currency="XTR",
        prices=[LabeledPrice(label=title, amount=stars)],
    )


@router.callback_query(F.data.startswith("pay_cryptobot_"))
async def pay_with_cryptobot(callback: CallbackQuery, state: FSMContext, bot: Bot):
    await callback.answer()
    if not cryptobot_configured():
        await callback.message.answer(f"CryptoBot: @{SUPPORT_USERNAME}")
        return
    plan_key = callback.data.removeprefix("pay_cryptobot_")
    plan = PLANS.get(plan_key)
    if not plan:
        return
    lang = await _ulang(callback.from_user.id)

    data = await state.get_data()
    discount = int(data.get("discount_percent") or 0)
    promo = data.get("promo_code")
    stars, eur = _priced(plan, discount)
    title = plan_title(plan_key, lang)

    payment = await create_pending_payment(
        callback.from_user.id,
        plan_key,
        stars,
        eur,
        "cryptobot",
        promo_code=promo,
        discount_percent=discount,
    )

    me = await bot.get_me()
    try:
        invoice = await create_invoice(
            amount_eur=eur,
            description=f"{title} · {plan['days']}d · #{payment.id}",
            payload=f"pay:{payment.id}:{callback.from_user.id}:{plan_key}",
            paid_btn_url=f"https://t.me/{me.username}",
        )
    except Exception as e:
        await cancel_payment(payment.id)
        await callback.message.answer(f"CryptoBot error: {e}")
        return

    invoice_id = str(invoice.get("invoice_id") or invoice.get("id") or "")
    pay_url = invoice.get("bot_invoice_url") or invoice.get("pay_url") or invoice.get("mini_app_invoice_url")
    await update_payment(payment.id, external_id=invoice_id, pay_url=pay_url)

    check_l = {"ru": "Проверить оплату", "en": "Check payment", "lt": "Tikrinti", "et": "Kontrolli"}.get(lang, "Check")
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="CryptoBot ➜", url=pay_url)],
        [InlineKeyboardButton(text=check_l, callback_data=f"pay_check_{payment.id}")],
        [InlineKeyboardButton(text=f"@{SUPPORT_USERNAME}", url=SUPPORT_URL)],
    ])
    await callback.message.edit_text(
        f"{tg_emoji('CRYPTO')} <b>CryptoBot</b>\n\n"
        f"{title}\n"
        f"<b>{eur} €</b>"
        + (f" (−{discount}%)" if discount else "")
        + f"\n#{payment.id}\n\n"
        "1. Pay USDT / TON\n"
        "2. Subscription activates automatically",
        reply_markup=kb,
    )


@router.callback_query(F.data.startswith("pay_check_"))
async def pay_check_cryptobot(callback: CallbackQuery, bot: Bot, state: FSMContext):
    payment_id = int(callback.data.removeprefix("pay_check_"))
    payment = await get_payment(payment_id)
    if not payment or payment.telegram_id != callback.from_user.id:
        await callback.answer("—", show_alert=True)
        return
    if payment.status == "paid":
        await callback.answer("✅", show_alert=True)
        return
    if not payment.external_id:
        await callback.answer("—", show_alert=True)
        return
    try:
        inv = await get_invoice(payment.external_id)
    except Exception as e:
        await callback.answer(str(e)[:180], show_alert=True)
        return
    if not inv or inv.get("status") != "paid":
        await callback.answer("…", show_alert=True)
        return
    await _activate_paid(bot, payment, state)
    await callback.answer("✅", show_alert=True)
    lang = await _ulang(callback.from_user.id)
    user = await get_user(callback.from_user.id)
    until = (
        user.subscription_end.strftime("%d.%m.%Y")
        if user and user.subscription_end
        else "—"
    )
    await callback.message.edit_text(
        t(
            "sub_bought",
            lang,
            plan=plan_title(payment.plan, lang),
            until=until,
        )
    )


async def _start_manual_payment(callback: CallbackQuery, method: str, state: FSMContext):
    await callback.answer()
    plan_key = callback.data.removeprefix(f"pay_{method}_")
    plan = PLANS.get(plan_key)
    if not plan:
        return
    lang = await _ulang(callback.from_user.id)

    data = await state.get_data()
    discount = int(data.get("discount_percent") or 0)
    promo = data.get("promo_code")
    stars, eur = _priced(plan, discount)
    title = plan_title(plan_key, lang)

    if method == "card":
        details = PAYMENT_CARD_DETAILS
        method_title = {"ru": "SEPA / карта", "en": "SEPA / card", "lt": "SEPA / kortelė", "et": "SEPA / kaart"}.get(lang, "SEPA")
    elif method == "banks":
        details = PAYMENT_BANKS_OTHER
        method_title = {"ru": "Другие банки", "en": "Other banks", "lt": "Kiti bankai", "et": "Teised pangad"}.get(lang, "Banks")
    else:
        details = PAYMENT_CRYPTO_DETAILS
        method_title = "Crypto"

    payment = await create_pending_payment(
        callback.from_user.id,
        plan_key,
        stars,
        eur,
        method,
        promo_code=promo,
        discount_percent=discount,
    )

    text = (
        f"{tg_emoji('MONEY')} <b>{method_title}</b>\n\n"
        f"<b>{title}</b> ({plan['days']}d)\n"
        f"<b>{eur} €</b>"
        + (f" (−{discount}%)" if discount else "")
        + f"\n#{payment.id}\n\n"
        f"<b>Details:</b>\n{details}\n\n"
        f"1. Transfer {eur} €\n"
        f"2. Tap paid\n"
        f"3. Admin confirms\n\n"
        f"@{SUPPORT_USERNAME}"
    )
    await callback.message.edit_text(text, reply_markup=pending_payment_user_kb(payment.id, lang))


@router.callback_query(F.data.startswith("pay_card_"))
async def pay_with_card(callback: CallbackQuery, state: FSMContext):
    await _start_manual_payment(callback, "card", state)


@router.callback_query(F.data.startswith("pay_banks_"))
async def pay_with_banks(callback: CallbackQuery, state: FSMContext):
    await _start_manual_payment(callback, "banks", state)


@router.callback_query(F.data.startswith("pay_crypto_"))
async def pay_with_crypto(callback: CallbackQuery, state: FSMContext):
    await _start_manual_payment(callback, "crypto", state)


@router.callback_query(F.data.startswith("pay_done_"))
async def pay_user_done(callback: CallbackQuery, bot: Bot):
    payment_id = int(callback.data.removeprefix("pay_done_"))
    payment = await get_payment(payment_id)
    if not payment or payment.telegram_id != callback.from_user.id:
        await callback.answer("—", show_alert=True)
        return
    if payment.status != "pending":
        await callback.answer(payment.status, show_alert=True)
        return

    plan = PLANS.get(payment.plan, {})
    uname = f"@{callback.from_user.username}" if callback.from_user.username else "—"
    admin_text = (
        f"{tg_emoji('MONEY')} <b>Pending</b>\n"
        f"#{payment.id}\n"
        f"{uname} (<code>{payment.telegram_id}</code>)\n"
        f"{plan.get('title', payment.plan)} · {payment.method}\n"
        f"{payment.amount_rub} €"
        + (f" (−{payment.discount_percent}%)" if payment.discount_percent else "")
    )
    for admin_id in ADMIN_IDS:
        try:
            await bot.send_message(admin_id, admin_text, reply_markup=admin_payment_kb(payment.id))
        except Exception:
            pass

    await callback.message.edit_text(
        f"{tg_emoji('OK')} #{payment.id} → admin\n@{SUPPORT_USERNAME}"
    )
    await callback.answer("OK")


@router.callback_query(F.data.startswith("pay_cancel_"))
async def pay_user_cancel(callback: CallbackQuery):
    payment_id = int(callback.data.removeprefix("pay_cancel_"))
    payment = await get_payment(payment_id)
    if not payment or payment.telegram_id != callback.from_user.id:
        await callback.answer("—", show_alert=True)
        return
    if payment.status != "pending":
        await callback.answer("—", show_alert=True)
        return
    await cancel_payment(payment_id)
    await callback.message.edit_text(f"{tg_emoji('OK')} #{payment_id} cancelled")
    await callback.answer("OK")


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
    lang = getattr(user, "language", None) or "ru"
    until = user.subscription_end.strftime("%d.%m.%Y") if user and user.subscription_end else "—"
    try:
        await bot.send_message(
            payment.telegram_id,
            t(
                "sub_bought",
                lang,
                plan=plan_title(payment.plan, lang),
                until=until,
            ),
        )
    except Exception:
        pass
    if user and user.referrer_id:
        try:
            await extend_subscription(user.referrer_id, "bonus", REFERRAL_BONUS_DAYS)
            await bot.send_message(
                user.referrer_id,
                f"{tg_emoji('FIRE')} +{REFERRAL_BONUS_DAYS}d referral bonus",
            )
        except Exception:
            pass


@router.callback_query(F.data.startswith("adm_pay_ok_"))
async def admin_confirm_payment(callback: CallbackQuery, bot: Bot):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("—", show_alert=True)
        return
    payment_id = int(callback.data.removeprefix("adm_pay_ok_"))
    payment = await get_payment(payment_id)
    if not payment or payment.status != "pending":
        await callback.answer("—", show_alert=True)
        return
    await _activate_paid(bot, payment)
    await callback.message.edit_text(
        (callback.message.text or "") + f"\n\n✅ OK ({callback.from_user.id})"
    )
    await callback.answer("OK")


@router.callback_query(F.data.startswith("adm_pay_no_"))
async def admin_reject_payment(callback: CallbackQuery, bot: Bot):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("—", show_alert=True)
        return
    payment_id = int(callback.data.removeprefix("adm_pay_no_"))
    payment = await get_payment(payment_id)
    if not payment or payment.status != "pending":
        await callback.answer("—", show_alert=True)
        return
    await cancel_payment(payment_id)
    try:
        await bot.send_message(
            payment.telegram_id,
            f"{tg_emoji('WARN')} #{payment_id} rejected\n@{SUPPORT_USERNAME}",
        )
    except Exception:
        pass
    await callback.message.edit_text(
        (callback.message.text or "") + f"\n\n❌ ({callback.from_user.id})"
    )
    await callback.answer("OK")


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
    lang = await _ulang(message.from_user.id)

    if not plan:
        await message.answer(f"OK pay · @{SUPPORT_USERNAME}")
        return

    stars_paid = message.successful_payment.total_amount
    eur = apply_discount(plan.get("eur") or plan["rub"], discount)
    await save_payment(
        message.from_user.id,
        plan_key,
        stars_paid,
        method="stars",
        amount_rub=eur,
        status="paid",
        promo_code=promo,
        discount_percent=discount,
    )
    if promo:
        await use_promo(promo)
    user = await extend_subscription(message.from_user.id, plan_key, plan["days"])
    await state.update_data(promo_code=None, discount_percent=0)

    until = user.subscription_end.strftime("%d.%m.%Y") if user and user.subscription_end else "—"
    await message.answer(
        t("sub_bought", lang, plan=plan_title(plan_key, lang), until=until)
    )

    if user and user.referrer_id:
        try:
            await message.bot.send_message(
                user.referrer_id,
                f"{tg_emoji('FIRE')} +{REFERRAL_BONUS_DAYS}d referral bonus",
            )
            await extend_subscription(user.referrer_id, "bonus", REFERRAL_BONUS_DAYS)
        except Exception:
            pass


async def activate_from_cryptobot_webhook(bot: Bot, invoice: dict) -> bool:
    """Called from /cryptobot-webhook when invoice_paid."""
    payload = invoice.get("payload") or ""
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
