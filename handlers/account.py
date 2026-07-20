"""Connect client's Telegram account for user-side autoposting (QR-first)."""

import asyncio
import logging

from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, BufferedInputFile
from aiogram.fsm.context import FSMContext

from keyboards import main_menu, cancel_kb, account_kb
from database import get_or_create_user, get_user, set_user_tg_session, user_has_tg_account
from utils.emoji import tg_emoji
from states import AccountLink
from config import is_admin
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
)

router = Router()
logger = logging.getLogger(__name__)

_qr_tasks: dict[int, asyncio.Task] = {}


def account_status_text(user) -> str:
    if user_has_tg_account(user):
        name = user.tg_account_name or "аккаунт"
        phone = mask_phone(user.tg_phone)
        extra = f"\nТелефон: <code>{phone}</code>" if user.tg_phone else ""
        return (
            f"{tg_emoji('OK')} <b>Публикация подключена</b>\n"
            f"Аккаунт: <b>{name}</b>{extra}\n\n"
            "Объявления публикуются от твоего имени в выбранные барахолки.\n"
            "Отключить можно здесь или в Telegram → Настройки → Устройства."
        )
    return (
        f"{tg_emoji('WARN')} <b>Аккаунт не подключён</b>\n\n"
        "Чтобы посты сами уходили в барахолки, подключи Telegram "
        "<b>через QR</b> — как обычный Desktop:\n\n"
        "1. Нажми кнопку ниже\n"
        "2. Телефон → Настройки → Устройства → Подключить устройство\n"
        "3. Наведи камеру на QR\n\n"
        "Номер и SMS-код боту <b>не нужны</b>.\n"
        "Отключить можно тут или в Telegram → Устройства."
    )


def _api_missing_alert(telegram_id: int) -> str:
    if is_admin(telegram_id):
        return (
            "Нужны TG_API_ID и TG_API_HASH в .env "
            "(my.telegram.org → Create application). Перезапусти main.py."
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
        reply_markup=account_kb(user_has_tg_account(user)),
    )


@router.callback_query(F.data == "account_menu")
async def account_menu_cb(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await cancel_qr_login(callback.from_user.id)
    user = await get_or_create_user(callback.from_user.id, callback.from_user.username)
    text = f"{tg_emoji('USER')} <b>Публикация от аккаунта</b>\n\n{account_status_text(user)}"
    try:
        await callback.message.edit_text(text, reply_markup=account_kb(user_has_tg_account(user)))
    except Exception:
        await callback.message.answer(text, reply_markup=account_kb(user_has_tg_account(user)))
    await callback.answer()


@router.callback_query(F.data == "account_link")
async def account_link_qr(callback: CallbackQuery, state: FSMContext, bot: Bot):
    """Primary: QR like Telegram Desktop — no phone/code to the bot."""
    if not api_configured():
        await callback.answer(_api_missing_alert(callback.from_user.id), show_alert=True)
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
            "Бот не просит номер и код из SMS.\n"
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
async def account_link_phone_removed(callback: CallbackQuery, state: FSMContext):
    """Old phone-login button — disabled (looks like phishing)."""
    await state.clear()
    await callback.answer(
        "Вход по номеру отключён. Используй QR или режим без входа.",
        show_alert=True,
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


@router.message(AccountLink.phone)
@router.message(AccountLink.code)
async def account_phone_flow_cancelled(message: Message, state: FSMContext):
    """Kill any leftover phone/code FSM from old builds."""
    await state.clear()
    await message.answer(
        f"{tg_emoji('OK')} Вход по номеру больше не нужен.\n"
        "Просто добавь группы и включи автопостинг — "
        "бот пришлёт готовый пост, перешлёшь в барахолку.\n\n"
        "Напиши /start",
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
        f"{tg_emoji('OK')} Полный автопост от <b>{name}</b> подключён.",
        reply_markup=main_menu,
    )


@router.callback_query(F.data == "account_unlink")
async def account_unlink(callback: CallbackQuery):
    await set_user_tg_session(callback.from_user.id, None)
    user = await get_user(callback.from_user.id)
    text = f"{tg_emoji('USER')} <b>Публикация от аккаунта</b>\n\n{account_status_text(user)}"
    await callback.message.edit_text(text, reply_markup=account_kb(False))
    await callback.answer("Отключено")
