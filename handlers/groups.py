from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, ChatShared
from aiogram.fsm.context import FSMContext
from aiogram.exceptions import TelegramAPIError

from keyboards import (
    main_menu, cancel_kb, group_pick_kb, groups_list_kb, group_card_kb,
)
from database import (
    get_or_create_user, get_user, create_group, get_group, get_user_groups,
    count_user_groups, update_group, delete_group,
)
from utils.emoji import tg_emoji
from utils.subscription import has_active_subscription, effective_limits
from states import GroupAdd, GroupSettings

router = Router()


def format_group(g) -> str:
    status = "активна" if g.active else "выключена"
    cooldown = ""
    if g.cooldown_until:
        cooldown = f"\nCooldown до: {g.cooldown_until.strftime('%d.%m %H:%M')} UTC"
    return (
        f"{tg_emoji('GROUPS')} <b>{g.title or g.chat_id}</b>\n"
        f"chat_id: <code>{g.chat_id}</code>\n"
        f"Статус: <b>{status}</b>\n"
        f"Посты: от твоего аккаунта\n"
        f"Интервал: {g.min_interval_minutes} мин (±{g.jitter_seconds} сек)\n"
        f"Тихие часы: {g.quiet_hours_start:02d}–{g.quiet_hours_end:02d} UTC\n"
        f"Ошибок подряд: {g.fail_count}{cooldown}"
    )


async def _add_group_for_user(
    bot: Bot,
    telegram_id: int,
    username: str | None,
    chat_id: int,
    title: str | None,
):
    """Save group by chat_id. Posts go from client's account — bot need not join."""
    user = await get_or_create_user(telegram_id, username)
    if not has_active_subscription(user):
        return False, "Нужна активная подписка."
    limits = effective_limits(user)
    count = await count_user_groups(user.id)
    if count >= limits["groups"]:
        return False, f"Лимит групп: {limits['groups']}."

    if not title:
        try:
            chat = await bot.get_chat(chat_id)
            title = chat.title or str(chat_id)
        except TelegramAPIError:
            title = title or str(chat_id)

    # Safer default interval for flea markets
    interval = max(user.default_interval or 90, 60)

    group = await create_group(
        user_id=user.id,
        chat_id=chat_id,
        title=title or str(chat_id),
        min_interval_minutes=interval,
        quiet_hours_start=user.quiet_hours_start or 0,
        quiet_hours_end=user.quiet_hours_end or 7,
        bot_can_post=False,
    )
    if group is None:
        return False, "Эта группа уже добавлена."

    hint = (
        "\n\nПосты пойдут <b>от твоего аккаунта</b> (бот в группу не нужен).\n"
        "Подключи аккаунт в «Мой аккаунт». Сам состои в барахолке и читай её правила."
    )
    return True, f"{tg_emoji('OK')} Группа добавлена!\n\n{format_group(group)}{hint}"


async def show_groups(target, telegram_id: int, edit: bool = False):
    user = await get_user(telegram_id)
    if not user:
        user = await get_or_create_user(telegram_id)
    groups = await get_user_groups(user.id)
    limits = effective_limits(user)
    header = (
        f"{tg_emoji('GROUPS')} <b>Мои группы</b>\n"
        f"Использовано: {len(groups)}/{limits['groups']}\n\n"
        "Выбери барахолку. Бот админом <b>не становится</b> — "
        "объявления уходят от твоего аккаунта после подключения в «Мой аккаунт»."
    )
    if not groups:
        text = header + f"\n\n{tg_emoji('EMPTY')} Группы ещё не добавлены."
    else:
        text = header + "\n\nВыбери группу:"
    kb = groups_list_kb(groups)
    if edit:
        await target.edit_text(text, reply_markup=kb)
    else:
        await target.answer(text, reply_markup=kb)


@router.message(F.text == "Мои группы")
async def my_groups(message: Message):
    await show_groups(message, message.from_user.id)


@router.callback_query(F.data == "groups_list")
async def groups_list_cb(callback: CallbackQuery):
    await show_groups(callback.message, callback.from_user.id, edit=True)
    await callback.answer()


@router.callback_query(F.data == "grp_help")
async def grp_help(callback: CallbackQuery):
    await callback.message.answer(
        f"{tg_emoji('SUPPORT')} <b>Как добавить группу</b>\n\n"
        "1. «Мои группы» → «➕ Добавить группу»\n"
        "2. Нажми «Выбрать группу»\n"
        "3. Тапни барахолку в меню Telegram\n\n"
        "Бот в группу <b>не добавляется</b>.\n"
        "Посты идут от твоего аккаунта после «Мой аккаунт».\n"
        "Ты должен быть участником барахолки и соблюдать её правила.",
    )
    await callback.answer()


@router.callback_query(F.data == "grp_add")
async def grp_add_start(callback: CallbackQuery, state: FSMContext):
    user = await get_or_create_user(callback.from_user.id, callback.from_user.username)
    if not has_active_subscription(user):
        await callback.answer("Нужна активная подписка", show_alert=True)
        return
    limits = effective_limits(user)
    count = await count_user_groups(user.id)
    if count >= limits["groups"]:
        await callback.answer(f"Лимит групп: {limits['groups']}", show_alert=True)
        return
    await state.set_state(GroupAdd.waiting)
    await callback.message.answer(
        f"{tg_emoji('GROUPS')} <b>Добавление группы</b>\n\n"
        "Нажми <b>«Выбрать группу»</b> и тапни барахолку в меню Telegram.\n\n"
        "Можно также переслать сюда любое сообщение из группы.\n"
        "Для отмены — «Отмена».",
        reply_markup=group_pick_kb(),
    )
    await callback.answer()


@router.message(GroupAdd.waiting, F.chat_shared)
async def grp_add_chat_shared(message: Message, state: FSMContext):
    shared: ChatShared = message.chat_shared
    title = getattr(shared, "title", None)
    ok, text = await _add_group_for_user(
        message.bot,
        message.from_user.id,
        message.from_user.username,
        shared.chat_id,
        title,
    )
    await state.clear()
    await message.answer(text, reply_markup=main_menu)


@router.message(GroupAdd.waiting)
async def grp_add_receive(message: Message, state: FSMContext):
    if message.text == "Отмена":
        await state.clear()
        await message.answer("Отменено.", reply_markup=main_menu)
        return

    if message.text == "Выбрать группу":
        await message.answer(
            "Выбери группу в окне Telegram, которое открылось.",
            reply_markup=group_pick_kb(),
        )
        return

    chat_id = None
    title = None

    if message.forward_from_chat:
        chat_id = message.forward_from_chat.id
        title = message.forward_from_chat.title
    elif message.forward_origin and getattr(message.forward_origin, "chat", None):
        chat_id = message.forward_origin.chat.id
        title = message.forward_origin.chat.title
    elif message.text and message.text.lstrip("-").isdigit():
        chat_id = int(message.text.strip())
    else:
        await message.answer(
            "Нажми «Выбрать группу» или перешли сообщение из барахолки.",
            reply_markup=group_pick_kb(),
        )
        return

    ok, text = await _add_group_for_user(
        message.bot,
        message.from_user.id,
        message.from_user.username,
        chat_id,
        title,
    )
    await state.clear()
    await message.answer(text, reply_markup=main_menu)


@router.callback_query(F.data.startswith("grp_view_"))
async def grp_view(callback: CallbackQuery):
    gid = int(callback.data.removeprefix("grp_view_"))
    group = await get_group(gid)
    user = await get_user(callback.from_user.id)
    if not group or not user or group.user_id != user.id:
        await callback.answer("Не найдено", show_alert=True)
        return
    await callback.message.edit_text(format_group(group), reply_markup=group_card_kb(group))
    await callback.answer()


@router.callback_query(F.data.startswith("grp_toggle_"))
async def grp_toggle(callback: CallbackQuery):
    gid = int(callback.data.removeprefix("grp_toggle_"))
    group = await get_group(gid)
    user = await get_user(callback.from_user.id)
    if not group or not user or group.user_id != user.id:
        await callback.answer("Не найдено", show_alert=True)
        return
    new_active = not group.active
    kwargs = {"active": new_active}
    if new_active:
        kwargs["fail_count"] = 0
        kwargs["cooldown_until"] = None
    group = await update_group(gid, **kwargs)
    await callback.message.edit_text(format_group(group), reply_markup=group_card_kb(group))
    await callback.answer("Обновлено")


@router.callback_query(F.data.startswith("grp_interval_"))
async def grp_interval_start(callback: CallbackQuery, state: FSMContext):
    gid = int(callback.data.removeprefix("grp_interval_"))
    await state.set_state(GroupSettings.interval)
    await state.update_data(group_id=gid)
    await callback.message.answer(
        f"{tg_emoji('CLOCK')} Введи минимальный интервал в минутах (60–1440):",
        reply_markup=cancel_kb,
    )
    await callback.answer()


@router.message(GroupSettings.interval)
async def grp_interval_save(message: Message, state: FSMContext):
    if message.text == "Отмена":
        await state.clear()
        await message.answer("Отменено.", reply_markup=main_menu)
        return
    if not message.text or not message.text.isdigit():
        await message.answer("Нужно число.")
        return
    minutes = int(message.text)
    if minutes < 60 or minutes > 1440:
        await message.answer("Для защиты от бана минимум 60 мин (до 1440).")
        return
    data = await state.get_data()
    gid = data["group_id"]
    user = await get_user(message.from_user.id)
    group = await get_group(gid)
    if not group or not user or group.user_id != user.id:
        await state.clear()
        await message.answer("Не найдено.", reply_markup=main_menu)
        return
    await update_group(gid, min_interval_minutes=minutes)
    await state.clear()
    await message.answer(f"{tg_emoji('OK')} Интервал: {minutes} мин.", reply_markup=main_menu)


@router.callback_query(F.data.startswith("grp_del_"))
async def grp_delete(callback: CallbackQuery):
    gid = int(callback.data.removeprefix("grp_del_"))
    group = await get_group(gid)
    user = await get_user(callback.from_user.id)
    if not group or not user or group.user_id != user.id:
        await callback.answer("Не найдено", show_alert=True)
        return
    await delete_group(gid)
    await callback.answer("Удалено")
    await show_groups(callback.message, callback.from_user.id, edit=True)
