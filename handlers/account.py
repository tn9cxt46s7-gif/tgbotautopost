"""Link client's Telegram account for user-side autoposting."""

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from keyboards import main_menu, cancel_kb, account_kb
from database import get_or_create_user, get_user, set_user_tg_session, user_has_tg_account
from utils.emoji import tg_emoji
from states import AccountLink
from services.user_client import (
    AccountError,
    Need2FA,
    api_configured,
    encrypt_session,
    mask_phone,
    start_phone_login,
    complete_phone_login,
)

router = Router()


def account_status_text(user) -> str:
    if user_has_tg_account(user):
        name = user.tg_account_name or "аккаунт"
        phone = mask_phone(user.tg_phone)
        return (
            f"{tg_emoji('OK')} <b>Аккаунт привязан</b>\n"
            f"Имя: <b>{name}</b>\n"
            f"Телефон: <code>{phone}</code>\n\n"
            "Объявления уходят в барахолки <b>от твоего аккаунта</b>, "
            "бота в группы добавлять не нужно."
        )
    return (
        f"{tg_emoji('WARN')} <b>Аккаунт не привязан</b>\n\n"
        "Без привязки автопостинг в барахолки не работает "
        "(туда нельзя добавить бота).\n\n"
        "Нажми «Привязать» → введи номер → код из Telegram/SMS."
    )


@router.message(F.text == "Мой аккаунт")
async def account_menu_msg(message: Message, state: FSMContext):
    await state.clear()
    user = await get_or_create_user(message.from_user.id, message.from_user.username)
    await message.answer(
        f"{tg_emoji('USER')} <b>Telegram-аккаунт</b>\n\n{account_status_text(user)}",
        reply_markup=account_kb(user_has_tg_account(user)),
    )


@router.callback_query(F.data == "account_menu")
async def account_menu_cb(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    user = await get_or_create_user(callback.from_user.id, callback.from_user.username)
    text = f"{tg_emoji('USER')} <b>Telegram-аккаунт</b>\n\n{account_status_text(user)}"
    await callback.message.edit_text(text, reply_markup=account_kb(user_has_tg_account(user)))
    await callback.answer()


@router.callback_query(F.data == "account_link")
async def account_link_start(callback: CallbackQuery, state: FSMContext):
    if not api_configured():
        await callback.answer("Админ ещё не настроил API_ID/API_HASH", show_alert=True)
        return
    await state.set_state(AccountLink.phone)
    await callback.message.answer(
        f"{tg_emoji('LINK')} <b>Привязка аккаунта</b>\n\n"
        "Пришли номер телефона в формате <code>+79001234567</code>\n"
        "(тот же, что в Telegram).\n\n"
        "Код придёт в Telegram или по SMS — введи его боту.\n"
        "Сессия хранится в зашифрованном виде.",
        reply_markup=cancel_kb,
    )
    await callback.answer()


@router.message(AccountLink.phone)
async def account_phone(message: Message, state: FSMContext):
    if message.text == "Отмена":
        await state.clear()
        await message.answer("Отменено.", reply_markup=main_menu)
        return
    try:
        pending, phone_code_hash = await start_phone_login(message.text)
    except AccountError as e:
        await message.answer(f"{tg_emoji('WARN')} {e}")
        return
    except Exception as e:
        await message.answer(f"{tg_emoji('WARN')} Не удалось отправить код: {e}")
        return

    from services.user_client import normalize_phone
    phone = normalize_phone(message.text)
    await state.update_data(
        phone=phone,
        phone_code_hash=phone_code_hash,
        pending_session=pending,
    )
    await state.set_state(AccountLink.code)
    await message.answer(
        f"{tg_emoji('OK')} Код отправлен на {mask_phone(phone)}.\n"
        "Пришли код из Telegram / SMS:",
        reply_markup=cancel_kb,
    )


@router.message(AccountLink.code)
async def account_code(message: Message, state: FSMContext):
    if message.text == "Отмена":
        await state.clear()
        await message.answer("Отменено.", reply_markup=main_menu)
        return

    data = await state.get_data()
    try:
        raw_session, name = await complete_phone_login(
            phone=data["phone"],
            code=message.text or "",
            phone_code_hash=data["phone_code_hash"],
            pending_session=data["pending_session"],
        )
    except Need2FA as e:
        await state.update_data(pending_session=e.pending_session)
        await state.set_state(AccountLink.password)
        await message.answer(
            f"{tg_emoji('LOCK')} Включена двухфакторка.\n"
            "Пришли пароль облачного пароля Telegram:",
            reply_markup=cancel_kb,
        )
        return
    except AccountError as e:
        await message.answer(f"{tg_emoji('WARN')} {e}")
        return
    except Exception as e:
        await message.answer(f"{tg_emoji('WARN')} Ошибка входа: {e}")
        return

    await set_user_tg_session(
        message.from_user.id,
        encrypt_session(raw_session),
        phone=data["phone"],
        account_name=name,
    )
    await state.clear()
    await message.answer(
        f"{tg_emoji('OK')} Аккаунт <b>{name}</b> привязан!\n"
        "Теперь автопостинг идёт от твоего аккаунта.",
        reply_markup=main_menu,
    )


@router.message(AccountLink.password)
async def account_password(message: Message, state: FSMContext):
    if message.text == "Отмена":
        await state.clear()
        await message.answer("Отменено.", reply_markup=main_menu)
        return

    data = await state.get_data()
    try:
        raw_session, name = await complete_phone_login(
            phone=data["phone"],
            code="",  # already consumed; password sign-in
            phone_code_hash=data["phone_code_hash"],
            pending_session=data["pending_session"],
            password=message.text or "",
        )
    except AccountError as e:
        await message.answer(f"{tg_emoji('WARN')} {e}")
        return
    except Exception as e:
        await message.answer(f"{tg_emoji('WARN')} Неверный пароль или ошибка: {e}")
        return

    await set_user_tg_session(
        message.from_user.id,
        encrypt_session(raw_session),
        phone=data["phone"],
        account_name=name,
    )
    await state.clear()
    await message.answer(
        f"{tg_emoji('OK')} Аккаунт <b>{name}</b> привязан!",
        reply_markup=main_menu,
    )


@router.callback_query(F.data == "account_unlink")
async def account_unlink(callback: CallbackQuery):
    await set_user_tg_session(callback.from_user.id, None)
    user = await get_user(callback.from_user.id)
    text = f"{tg_emoji('USER')} <b>Telegram-аккаунт</b>\n\n{account_status_text(user)}"
    await callback.message.edit_text(text, reply_markup=account_kb(False))
    await callback.answer("Аккаунт отвязан")
