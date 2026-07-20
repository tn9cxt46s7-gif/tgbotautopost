from datetime import datetime, timedelta
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext

from keyboards import (
    admin_menu, admin_users_list_kb, admin_user_kb, admin_back_kb,
    broadcast_confirm_kb, main_menu, cancel_kb,
)
from database import (
    list_users, count_users, count_active_subs, count_ads, count_groups,
    count_posts_since, count_open_tickets, find_users, get_user,
    set_user_blocked, extend_subscription, list_recent_ads, get_problem_groups,
    list_open_tickets, get_all_telegram_ids, get_subscribed_telegram_ids,
    update_ad, get_user_ads, get_user_groups, get_or_create_user,
)
from utils.emoji import tg_emoji
from utils.subscription import has_active_subscription
from config import is_admin
from states import AdminGiveSub, AdminFindUser, AdminBroadcast

router = Router()


def _deny(callback_or_msg):
    return not is_admin(callback_or_msg.from_user.id)


@router.message(Command("admin"))
async def admin_panel(message: Message, state: FSMContext):
    if _deny(message):
        return
    await state.clear()
    await message.answer(f"{tg_emoji('ADMIN')} <b>Админ-панель</b>", reply_markup=admin_menu)


@router.callback_query(F.data == "admin_home")
async def admin_home(callback: CallbackQuery, state: FSMContext):
    if _deny(callback):
        return
    await state.clear()
    await callback.message.edit_text(f"{tg_emoji('ADMIN')} <b>Админ-панель</b>", reply_markup=admin_menu)
    await callback.answer()


@router.callback_query(F.data == "admin_stats")
async def admin_stats(callback: CallbackQuery):
    if _deny(callback):
        return
    since = datetime.utcnow() - timedelta(hours=24)
    text = (
        f"{tg_emoji('STATS')} <b>Статистика</b>\n\n"
        f"Пользователей: <b>{await count_users()}</b>\n"
        f"Активных подписок: <b>{await count_active_subs()}</b>\n"
        f"Объявлений всего: <b>{await count_ads()}</b>\n"
        f"Активных объявлений: <b>{await count_ads('active')}</b>\n"
        f"Групп: <b>{await count_groups()}</b>\n"
        f"Постов за 24ч: <b>{await count_posts_since(since)}</b>\n"
        f"Открытых тикетов: <b>{await count_open_tickets()}</b>\n"
    )
    await callback.message.edit_text(text, reply_markup=admin_back_kb())
    await callback.answer()


@router.callback_query(F.data.startswith("admin_users"))
async def admin_users(callback: CallbackQuery):
    if _deny(callback):
        return
    offset = 0
    if callback.data.startswith("admin_users_"):
        try:
            offset = int(callback.data.removeprefix("admin_users_"))
        except ValueError:
            offset = 0
    users = await list_users(offset=offset, limit=20)
    if not users and offset == 0:
        await callback.message.edit_text(f"{tg_emoji('EMPTY')} Пользователей пока нет.", reply_markup=admin_back_kb())
    else:
        await callback.message.edit_text(
            f"{tg_emoji('USER')} <b>Пользователи</b> (с {offset + 1}):",
            reply_markup=admin_users_list_kb(users, offset),
        )
    await callback.answer()


@router.callback_query(F.data.startswith("adm_user_"))
async def admin_user_card(callback: CallbackQuery):
    if _deny(callback):
        return
    tid = int(callback.data.removeprefix("adm_user_"))
    await _render_user_card(callback, tid)
    await callback.answer()


async def _render_user_card(callback: CallbackQuery, tid: int):
    user = await get_user(tid)
    if not user:
        await callback.answer("Не найден", show_alert=True)
        return
    ads = await get_user_ads(user.id)
    groups = await get_user_groups(user.id)
    sub = "нет"
    if has_active_subscription(user):
        sub = f"до {user.subscription_end.strftime('%d.%m.%Y')} ({user.plan})"
    text = (
        f"{tg_emoji('USER')} <b>Пользователь</b>\n\n"
        f"ID: <code>{user.telegram_id}</code>\n"
        f"Username: @{user.username or '—'}\n"
        f"Подписка: {sub}\n"
        f"Блок: {'да' if user.is_blocked else 'нет'}\n"
        f"Автопостинг: {'вкл' if user.autopost_enabled else 'выкл'}\n"
        f"Объявлений: {len(ads)}\n"
        f"Групп: {len(groups)}\n"
        f"Регистрация: {user.created_at.strftime('%d.%m.%Y') if user.created_at else '—'}"
    )
    await callback.message.edit_text(text, reply_markup=admin_user_kb(user.telegram_id, user.is_blocked))


@router.callback_query(F.data.startswith("adm_block_"))
async def admin_block(callback: CallbackQuery):
    if _deny(callback):
        return
    tid = int(callback.data.removeprefix("adm_block_"))
    await set_user_blocked(tid, True)
    await callback.answer("Заблокирован")
    await _render_user_card(callback, tid)


@router.callback_query(F.data.startswith("adm_unblock_"))
async def admin_unblock(callback: CallbackQuery):
    if _deny(callback):
        return
    tid = int(callback.data.removeprefix("adm_unblock_"))
    await set_user_blocked(tid, False)
    await callback.answer("Разблокирован")
    await _render_user_card(callback, tid)


@router.callback_query(F.data == "admin_find")
async def admin_find_start(callback: CallbackQuery, state: FSMContext):
    if _deny(callback):
        return
    await state.set_state(AdminFindUser.query)
    await callback.message.answer(f"{tg_emoji('SEARCH')} Введи ID или username:", reply_markup=cancel_kb)
    await callback.answer()


@router.message(AdminFindUser.query)
async def admin_find_query(message: Message, state: FSMContext):
    if _deny(message):
        return
    if message.text == "Отмена":
        await state.clear()
        await message.answer("Отменено.", reply_markup=main_menu)
        return
    users = await find_users(message.text.strip())
    await state.clear()
    if not users:
        await message.answer("Никого не найдено.", reply_markup=admin_back_kb())
        return
    await message.answer(
        f"{tg_emoji('SEARCH')} Найдено: {len(users)}",
        reply_markup=admin_users_list_kb(users, 0),
    )


@router.callback_query(F.data == "admin_give_sub")
async def admin_give_start(callback: CallbackQuery, state: FSMContext):
    if _deny(callback):
        return
    await state.set_state(AdminGiveSub.user_id)
    await callback.message.answer(f"{tg_emoji('SUB')} Введи Telegram ID пользователя:", reply_markup=cancel_kb)
    await callback.answer()


@router.callback_query(F.data.startswith("adm_give_"))
async def admin_give_from_card(callback: CallbackQuery, state: FSMContext):
    if _deny(callback):
        return
    tid = int(callback.data.removeprefix("adm_give_"))
    await state.set_state(AdminGiveSub.days)
    await state.update_data(give_tid=tid)
    await callback.message.answer(
        f"{tg_emoji('SUB')} Сколько дней выдать пользователю <code>{tid}</code>?",
        reply_markup=cancel_kb,
    )
    await callback.answer()


@router.message(AdminGiveSub.user_id)
async def admin_give_uid(message: Message, state: FSMContext):
    if _deny(message):
        return
    if message.text == "Отмена":
        await state.clear()
        await message.answer("Отменено.", reply_markup=main_menu)
        return
    if not message.text or not message.text.isdigit():
        await message.answer("Нужен числовой Telegram ID.")
        return
    await state.update_data(give_tid=int(message.text))
    await state.set_state(AdminGiveSub.days)
    await message.answer("Сколько дней подписки выдать?")


@router.message(AdminGiveSub.days)
async def admin_give_days(message: Message, state: FSMContext):
    if _deny(message):
        return
    if message.text == "Отмена":
        await state.clear()
        await message.answer("Отменено.", reply_markup=main_menu)
        return
    if not message.text or not message.text.isdigit():
        await message.answer("Нужно число дней.")
        return
    days = int(message.text)
    data = await state.get_data()
    tid = data["give_tid"]
    await get_or_create_user(tid)
    user = await extend_subscription(tid, "month" if days >= 30 else "week", days)
    await state.clear()
    await message.answer(
        f"{tg_emoji('OK')} Подписка выдана до {user.subscription_end.strftime('%d.%m.%Y')}",
        reply_markup=admin_back_kb(),
    )
    try:
        await message.bot.send_message(
            tid,
            f"{tg_emoji('SUB')} Админ выдал тебе подписку до <b>{user.subscription_end.strftime('%d.%m.%Y')}</b>!",
        )
    except Exception:
        pass


@router.callback_query(F.data == "admin_ads")
async def admin_ads(callback: CallbackQuery):
    if _deny(callback):
        return
    ads = await list_recent_ads(15)
    if not ads:
        await callback.message.edit_text(f"{tg_emoji('EMPTY')} Объявлений нет.", reply_markup=admin_back_kb())
        await callback.answer()
        return
    lines = [f"{tg_emoji('ADS')} <b>Последние объявления</b>\n"]
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    from utils.emoji import eid
    rows = []
    for ad in ads:
        title = (ad.title or ad.text[:30])[:30]
        lines.append(f"#{ad.id} [{ad.status}] user_id={ad.user_id}: {title}")
        if ad.status == "active":
            rows.append([InlineKeyboardButton(
                text=f"Пауза #{ad.id}",
                callback_data=f"adm_ad_pause_{ad.id}",
                icon_custom_emoji_id=eid("PAUSE"),
            )])
    rows.append([InlineKeyboardButton(text="В админку", callback_data="admin_home", icon_custom_emoji_id=eid("BACK"))])
    await callback.message.edit_text("\n".join(lines), reply_markup=InlineKeyboardMarkup(inline_keyboard=rows))
    await callback.answer()


@router.callback_query(F.data.startswith("adm_ad_pause_"))
async def admin_ad_pause(callback: CallbackQuery):
    if _deny(callback):
        return
    ad_id = int(callback.data.removeprefix("adm_ad_pause_"))
    await update_ad(ad_id, status="paused")
    await callback.answer(f"Объявление #{ad_id} на паузе")


@router.callback_query(F.data == "admin_groups")
async def admin_groups(callback: CallbackQuery):
    if _deny(callback):
        return
    groups = await get_problem_groups(20)
    if not groups:
        await callback.message.edit_text(f"{tg_emoji('OK')} Проблемных групп нет.", reply_markup=admin_back_kb())
        await callback.answer()
        return
    lines = [f"{tg_emoji('GROUPS')} <b>Проблемные группы</b>\n"]
    for g in groups:
        lines.append(
            f"#{g.id} {g.title or g.chat_id} | fails={g.fail_count} "
            f"| active={g.active} | user_id={g.user_id}"
        )
    await callback.message.edit_text("\n".join(lines), reply_markup=admin_back_kb())
    await callback.answer()


@router.callback_query(F.data == "admin_support")
async def admin_support(callback: CallbackQuery):
    if _deny(callback):
        return
    tickets = await list_open_tickets(20)
    if not tickets:
        await callback.message.edit_text(f"{tg_emoji('OK')} Открытых тикетов нет.", reply_markup=admin_back_kb())
        await callback.answer()
        return
    lines = [f"{tg_emoji('TICKET')} <b>Открытые тикеты</b>\n"]
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    rows = []
    for t in tickets:
        lines.append(f"#{t.id} tg=<code>{t.telegram_id}</code> с {t.created_at.strftime('%d.%m %H:%M')}")
        rows.append([
            InlineKeyboardButton(text=f"Ответить #{t.id}", callback_data=f"sup_reply_{t.id}_{t.telegram_id}"),
            InlineKeyboardButton(text="Закрыть", callback_data=f"sup_close_{t.id}"),
        ])
    from utils.emoji import eid
    rows.append([InlineKeyboardButton(text="В админку", callback_data="admin_home", icon_custom_emoji_id=eid("BACK"))])
    await callback.message.edit_text("\n".join(lines), reply_markup=InlineKeyboardMarkup(inline_keyboard=rows))
    await callback.answer()


@router.callback_query(F.data == "admin_broadcast")
async def admin_broadcast_start(callback: CallbackQuery, state: FSMContext):
    if _deny(callback):
        return
    await state.set_state(AdminBroadcast.message)
    await callback.message.answer(
        f"{tg_emoji('BROADCAST')} Пришли текст рассылки:",
        reply_markup=cancel_kb,
    )
    await callback.answer()


@router.message(AdminBroadcast.message)
async def admin_broadcast_msg(message: Message, state: FSMContext):
    if _deny(message):
        return
    if message.text == "Отмена":
        await state.clear()
        await message.answer("Отменено.", reply_markup=main_menu)
        return
    await state.update_data(bc_text=message.text)
    await state.set_state(AdminBroadcast.confirm)
    await message.answer(
        f"Рассылка:\n\n{message.text}\n\nКому отправить?",
        reply_markup=broadcast_confirm_kb(),
    )


@router.callback_query(F.data.in_({"bc_all", "bc_subs"}))
async def admin_broadcast_send(callback: CallbackQuery, state: FSMContext):
    if _deny(callback):
        return
    data = await state.get_data()
    text = data.get("bc_text")
    await state.clear()
    if not text:
        await callback.answer("Нет текста", show_alert=True)
        return
    ids = await get_all_telegram_ids() if callback.data == "bc_all" else await get_subscribed_telegram_ids()
    ok, fail = 0, 0
    await callback.message.edit_text(f"{tg_emoji('BROADCAST')} Отправка {len(ids)} пользователям...")
    for tid in ids:
        try:
            await callback.bot.send_message(tid, text)
            ok += 1
        except Exception:
            fail += 1
    await callback.message.answer(
        f"{tg_emoji('OK')} Готово. Успешно: {ok}, ошибок: {fail}",
        reply_markup=admin_back_kb(),
    )
    await callback.answer()
