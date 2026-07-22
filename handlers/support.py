from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from keyboards import main_menu, support_exit_kb, support_admin_kb, support_menu_kb
from database import get_or_create_user, open_ticket, get_open_ticket, close_ticket
from utils.emoji import tg_emoji
from config import ADMIN_IDS, is_admin, SUPPORT_USERNAME, SUPPORT_URL
from states import SupportChat, AdminReply

router = Router()


@router.message(F.text == "Поддержка")
@router.callback_query(F.data == "support_start")
async def support_menu(event: Message | CallbackQuery, state: FSMContext):
    await state.clear()
    text = (
        f"{tg_emoji('SUPPORT')} <b>Поддержка</b>\n\n"
        f"Быстрый контакт в Telegram: <b>@{SUPPORT_USERNAME}</b>\n"
        f"{SUPPORT_URL}\n\n"
        "Или открой тикет прямо в боте — админ ответит здесь."
    )
    if isinstance(event, CallbackQuery):
        await event.message.answer(text, reply_markup=support_menu_kb())
        await event.answer()
    else:
        await event.answer(text, reply_markup=support_menu_kb())


@router.callback_query(F.data == "support_ticket")
async def support_ticket_start(callback: CallbackQuery, state: FSMContext):
    user = await get_or_create_user(callback.from_user.id, callback.from_user.username)
    ticket = await open_ticket(user.id, user.telegram_id)
    await state.set_state(SupportChat.chatting)
    await state.update_data(ticket_id=ticket.id)

    await callback.message.answer(
        f"{tg_emoji('SUPPORT')} <b>Чат поддержки</b>\n"
        f"Тикет #{ticket.id}\n\n"
        "Напиши вопрос — админ ответит здесь.\n"
        f"Также можно: @{SUPPORT_USERNAME}\n"
        "Выход: «Завершить диалог».",
        reply_markup=support_exit_kb,
    )
    await callback.answer()


@router.message(SupportChat.chatting, F.text == "Завершить диалог")
async def support_exit(message: Message, state: FSMContext):
    data = await state.get_data()
    ticket_id = data.get("ticket_id")
    if ticket_id:
        await close_ticket(ticket_id)
    await state.clear()
    await message.answer(f"{tg_emoji('OK')} Диалог завершён.", reply_markup=main_menu)


@router.message(SupportChat.chatting)
async def support_user_message(message: Message, state: FSMContext):
    data = await state.get_data()
    ticket_id = data.get("ticket_id")
    if not ticket_id:
        ticket = await get_open_ticket(message.from_user.id)
        if not ticket:
            user = await get_or_create_user(message.from_user.id, message.from_user.username)
            ticket = await open_ticket(user.id, user.telegram_id)
        ticket_id = ticket.id
        await state.update_data(ticket_id=ticket_id)

    uname = f"@{message.from_user.username}" if message.from_user.username else "—"
    header = (
        f"{tg_emoji('TICKET')} <b>Тикет #{ticket_id}</b>\n"
        f"От: {uname} (<code>{message.from_user.id}</code>)\n\n"
    )

    for admin_id in ADMIN_IDS:
        try:
            if message.photo:
                await message.bot.send_photo(
                    admin_id,
                    message.photo[-1].file_id,
                    caption=header + (message.caption or ""),
                    reply_markup=support_admin_kb(ticket_id, message.from_user.id),
                )
            elif message.document:
                await message.bot.send_document(
                    admin_id,
                    message.document.file_id,
                    caption=header + (message.caption or ""),
                    reply_markup=support_admin_kb(ticket_id, message.from_user.id),
                )
            else:
                await message.bot.send_message(
                    admin_id,
                    header + (message.text or "(пустое сообщение)"),
                    reply_markup=support_admin_kb(ticket_id, message.from_user.id),
                )
        except Exception:
            pass

    await message.answer(
        f"{tg_emoji('OK')} Сообщение отправлено.\n"
        f"Дублируй в @{SUPPORT_USERNAME}, если срочно."
    )


@router.callback_query(F.data.startswith("sup_reply_"))
async def support_admin_reply_start(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return
    parts = callback.data.split("_")
    ticket_id = int(parts[2])
    telegram_id = int(parts[3])
    await state.set_state(AdminReply.waiting)
    await state.update_data(reply_ticket_id=ticket_id, reply_to=telegram_id)
    await callback.message.answer(
        f"{tg_emoji('SUPPORT')} Напиши ответ пользователю <code>{telegram_id}</code>:"
    )
    await callback.answer()


@router.message(AdminReply.waiting)
async def support_admin_reply_send(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    data = await state.get_data()
    telegram_id = data["reply_to"]
    ticket_id = data["reply_ticket_id"]
    await state.clear()
    try:
        await message.bot.send_message(
            telegram_id,
            f"{tg_emoji('SUPPORT')} <b>Ответ поддержки</b> (тикет #{ticket_id}):\n\n{message.text}",
        )
        await message.answer(f"{tg_emoji('OK')} Ответ отправлен.")
    except Exception as e:
        await message.answer(f"{tg_emoji('WARN')} Не удалось отправить: {e}")


@router.callback_query(F.data.startswith("sup_close_"))
async def support_close(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return
    ticket_id = int(callback.data.removeprefix("sup_close_"))
    ticket = await close_ticket(ticket_id)
    if ticket:
        try:
            await callback.bot.send_message(
                ticket.telegram_id,
                f"{tg_emoji('OK')} Тикет #{ticket_id} закрыт.\n"
                f"Если нужно — «Поддержка» или @{SUPPORT_USERNAME}.",
            )
        except Exception:
            pass
    await callback.answer("Тикет закрыт")
    await callback.message.edit_reply_markup(reply_markup=None)
