"""Connect client's Telegram account for user-side autoposting.

On always-on hosts (main.py): QR login like Telegram Desktop.
On Vercel serverless: phone + code (request-based; QR background wait does not work).
"""

import asyncio
import logging
import os

from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, BufferedInputFile
from aiogram.fsm.context import FSMContext

from keyboards import main_menu, cancel_kb, account_kb
from database import get_or_create_user, get_user, set_user_tg_session, user_has_tg_account
from utils.emoji import tg_emoji
from states import AccountLink
from config import is_admin, IS_VERCEL
from services.user_client import (
    AccountError,
    Need2FA,
    api_configured,
    encrypt_session,
    mask_phone,
    begin_qr_login,
    wait_qr_login,
    cancel_qr_login,
    finish_password_login,
    start_phone_login,
    complete_phone_login,
)

router = Router()
logger = logging.getLogger(__name__)

_qr_tasks: dict[int, asyncio.Task] = {}


def _serverless() -> bool:
    return IS_VERCEL or bool(os.getenv("VERCEL"))


def account_status_text(user) -> str:
    if user_has_tg_account(user):
        name = user.tg_account_name or "аккаунт"
        phone = mask_phone(user.tg_phone)
        extra = f"\nТелефон: <code>{phone}</code>" if user.tg_phone else ""
        return (
            f"{tg_emoji('OK')} <b>Публикация подключена</b>\n"
            f"Аккаунт: <b>{name}</b>{extra}\n\n"
            "Объявления уходят <b>от твоего имени</b> в выбранные барахолки.\n"
            "Бот в группы не заходит. Отключить можно здесь или в "
            "Telegram → Настройки → Устройства."
        )
    vercel_hint = (
        "На Vercel надёжнее вход <b>по номеру</b> (QR здесь нестабилен).\n\n"
        if _serverless()
        else "Можно через <b>QR</b> (как Desktop) или по номеру.\n\n"
    )
    return (
        f"{tg_emoji('WARN')} <b>Аккаунт не подключён</b>\n\n"
        f"{vercel_hint}"
        "Без твоего аккаунта рассылка невозможна: бот не становится админом "
        "в барахолках и не пишет от своего имени.\n\n"
        "Подключи Telegram — посты пойдут как обычные объявления от тебя."
    )


def _api_missing_alert(telegram_id: int) -> str:
    if is_admin(telegram_id):
        return (
            "Нужны TG_API_ID и TG_API_HASH в Environment Variables "
            "(my.telegram.org → Create application)."
        )
    return "Подключение временно недоступно. Напиши в поддержку."


async def _save_linked(telegram_id: int, raw_session: str, name: str | None, phone: str | None = None):
    await set_user_tg_session(
        telegram_id,
        encrypt_session(raw_session),
        phone=phone,
        account_name=name,
    )


@router.message(F.text == "Мой аккаунт")
async def account_menu_msg(message: Message, state: FSMContext):
    await state.clear()
    await cancel_qr_login(message.from_user.id)
    user = await get_or_create_user(message.from_user.id, message.from_user.username)
    await message.answer(
        f"{tg_emoji('USER')} <b>Публикация от аккаунта</b>\n\n{account_status_text(user)}",
        reply_markup=account_kb(user_has_tg_account(user), serverless=_serverless()),
    )


@router.callback_query(F.data == "account_menu")
async def account_menu_cb(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await cancel_qr_login(callback.from_user.id)
    user = await get_or_create_user(callback.from_user.id, callback.from_user.username)
    text = f"{tg_emoji('USER')} <b>Публикация от аккаунта</b>\n\n{account_status_text(user)}"
    kb = account_kb(user_has_tg_account(user), serverless=_serverless())
    try:
        await callback.message.edit_text(text, reply_markup=kb)
    except Exception:
        await callback.message.answer(text, reply_markup=kb)
    await callback.answer()


@router.callback_query(F.data == "account_link")
async def account_link_qr(callback: CallbackQuery, state: FSMContext, bot: Bot):
    """QR like Telegram Desktop — needs long-lived process (not reliable on Vercel)."""
    if not api_configured():
        await callback.answer(_api_missing_alert(callback.from_user.id), show_alert=True)
        return

    if _serverless():
        await callback.answer(
            "На Vercel QR нестабилен. Используй «Подключить по номеру».",
            show_alert=True,
        )
        return

    await callback.answer()
    uid = callback.from_user.id
    old = _qr_tasks.pop(uid, None)
    if old and not old.done():
        old.cancel()
    await cancel_qr_login(uid)
    await state.set_state(AccountLink.qr_wait)

    try:
        url, png = await begin_qr_login(uid)
    except AccountError as e:
        await state.clear()
        await callback.message.answer(f"{tg_emoji('WARN')} {e}", reply_markup=main_menu)
        return
    except Exception as e:
        await state.clear()
        logger.exception("QR begin failed")
        await callback.message.answer(f"{tg_emoji('WARN')} Не удалось создать QR: {e}", reply_markup=main_menu)
        return

    photo = BufferedInputFile(png, filename="qr.png")
    await callback.message.answer_photo(
        photo,
        caption=(
            f"{tg_emoji('LINK')} <b>Подключение публикации</b>\n\n"
            "1. Открой Telegram на телефоне\n"
            "2. <b>Настройки → Устройства → Подключить устройство</b>\n"
            "3. Наведи камеру на этот QR\n\n"
            "Это официальный вход Telegram (как Desktop).\n"
            "QR действует ~1.5 мин.\n\n"
            f"Или открой ссылку: {url}"
        ),
        reply_markup=cancel_kb,
    )

    async def _waiter():
        try:
            raw, name = await wait_qr_login(uid, timeout=90)
            await _save_linked(uid, raw, name)
            await state.clear()
            await bot.send_message(
                uid,
                f"{tg_emoji('OK')} Готово! Публикация от <b>{name}</b> подключена.\n"
                "Можно добавлять группы и включать автопостинг.",
                reply_markup=main_menu,
            )
        except Need2FA as e:
            await state.update_data(pending_session=e.pending_session, link_via="qr")
            await state.set_state(AccountLink.password)
            await bot.send_message(
                uid,
                f"{tg_emoji('LOCK')} На аккаунте облачный пароль (2FA).\n"
                "Введи его один раз — как при входе в Desktop.\n"
                "Пароль не сохраняется.",
                reply_markup=cancel_kb,
            )
        except AccountError as e:
            await state.clear()
            await bot.send_message(uid, f"{tg_emoji('WARN')} {e}", reply_markup=main_menu)
        except asyncio.CancelledError:
            await cancel_qr_login(uid)
        except Exception as e:
            logger.exception("QR wait failed")
            await state.clear()
            await cancel_qr_login(uid)
            try:
                await bot.send_message(uid, f"{tg_emoji('WARN')} Ошибка QR: {e}", reply_markup=main_menu)
            except Exception:
                pass
        finally:
            _qr_tasks.pop(uid, None)

    _qr_tasks[uid] = asyncio.create_task(_waiter())


@router.callback_query(F.data == "account_link_phone")
async def account_link_phone(callback: CallbackQuery, state: FSMContext):
    """Phone + code — works on Vercel (each step is a separate webhook)."""
    if not api_configured():
        await callback.answer(_api_missing_alert(callback.from_user.id), show_alert=True)
        return
    await state.set_state(AccountLink.phone)
    await callback.message.answer(
        f"{tg_emoji('LINK')} <b>Подключение по номеру</b>\n\n"
        "Введи номер в формате <code>+79001234567</code>.\n"
        "Telegram пришлёт код в приложение — введи его сюда.\n\n"
        "Номер и код нужны только для входа (как в Desktop).\n"
        "Для отмены — «Отмена».",
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
        pending, phone_code_hash = await start_phone_login(message.text or "")
    except AccountError as e:
        await message.answer(f"{tg_emoji('WARN')} {e}")
        return
    except Exception as e:
        logger.exception("phone login start failed")
        await message.answer(f"{tg_emoji('WARN')} Не удалось отправить код: {e}")
        return

    await state.update_data(
        phone=(message.text or "").strip(),
        pending_session=pending,
        phone_code_hash=phone_code_hash,
        link_via="phone",
    )
    await state.set_state(AccountLink.code)
    await message.answer(
        f"{tg_emoji('OK')} Код отправлен в Telegram.\n"
        "Введи код из сообщения (только цифры):",
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
        raw, name = await complete_phone_login(
            data["phone"],
            message.text or "",
            data["phone_code_hash"],
            data["pending_session"],
        )
    except Need2FA as e:
        await state.update_data(pending_session=e.pending_session, link_via="phone")
        await state.set_state(AccountLink.password)
        await message.answer(
            f"{tg_emoji('LOCK')} Нужен облачный пароль (2FA).\n"
            "Введи его один раз. Пароль не сохраняется.",
            reply_markup=cancel_kb,
        )
        return
    except AccountError as e:
        await message.answer(f"{tg_emoji('WARN')} {e}")
        return
    except Exception as e:
        logger.exception("phone code failed")
        await message.answer(f"{tg_emoji('WARN')} Ошибка: {e}")
        return

    await _save_linked(message.from_user.id, raw, name, phone=data.get("phone"))
    await state.clear()
    await message.answer(
        f"{tg_emoji('OK')} Готово! Публикация от <b>{name}</b> подключена.",
        reply_markup=main_menu,
    )


@router.message(AccountLink.qr_wait)
async def account_qr_cancel(message: Message, state: FSMContext):
    if message.text == "Отмена":
        uid = message.from_user.id
        task = _qr_tasks.pop(uid, None)
        if task and not task.done():
            task.cancel()
        await cancel_qr_login(uid)
        await state.clear()
        await message.answer("Отменено.", reply_markup=main_menu)
        return
    await message.answer("Отсканируй QR в «Устройства» или нажми «Отмена».")


@router.message(AccountLink.password)
async def account_password(message: Message, state: FSMContext):
    if message.text == "Отмена":
        await state.clear()
        await message.answer("Отменено.", reply_markup=main_menu)
        return

    data = await state.get_data()
    try:
        raw_session, name = await finish_password_login(
            data["pending_session"],
            message.text or "",
        )
    except AccountError as e:
        await message.answer(f"{tg_emoji('WARN')} {e}")
        return
    except Exception as e:
        await message.answer(f"{tg_emoji('WARN')} Неверный пароль или ошибка: {e}")
        return

    await _save_linked(message.from_user.id, raw_session, name, phone=data.get("phone"))
    await state.clear()
    await message.answer(
        f"{tg_emoji('OK')} Публикация от <b>{name}</b> подключена.",
        reply_markup=main_menu,
    )


@router.callback_query(F.data == "account_unlink")
async def account_unlink(callback: CallbackQuery):
    await set_user_tg_session(callback.from_user.id, None)
    user = await get_user(callback.from_user.id)
    text = f"{tg_emoji('USER')} <b>Публикация от аккаунта</b>\n\n{account_status_text(user)}"
    await callback.message.edit_text(
        text,
        reply_markup=account_kb(False, serverless=_serverless()),
    )
    await callback.answer("Отключено")
