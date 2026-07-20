from aiogram import Router, F
from aiogram.types import Message, CallbackQuery

from keyboards import autopost_kb
from database import (
    get_or_create_user, get_user, set_autopost_enabled,
    get_user_ads, get_user_groups, user_has_tg_account,
)
from utils.emoji import tg_emoji
from utils.subscription import has_active_subscription

router = Router()


async def build_autopost_text(telegram_id: int) -> tuple[str, bool]:
    user = await get_user(telegram_id)
    if not user:
        user = await get_or_create_user(telegram_id)
    ads = await get_user_ads(user.id)
    groups = await get_user_groups(user.id)
    active_ads = [a for a in ads if a.status == "active"]
    active_groups = [g for g in groups if g.active]
    linked = user_has_tg_account(user)

    sub = "да" if has_active_subscription(user) else "нет"
    ready = bool(user.autopost_enabled and active_ads and active_groups)
    status = "работает" if ready else "остановлен"

    if linked:
        mode = "полный автопост от твоего аккаунта (QR)"
    else:
        mode = "без входа: бот пришлёт готовый пост → ты пересылаешь в группу"

    text = (
        f"{tg_emoji('AUTO')} <b>Автопостинг</b>\n\n"
        f"Статус: <b>{status}</b>\n"
        f"Переключатель: <b>{'вкл' if user.autopost_enabled else 'выкл'}</b>\n"
        f"Подписка: <b>{sub}</b>\n"
        f"Режим: <b>{mode}</b>\n\n"
        f"{tg_emoji('ADS')} Активных объявлений: <b>{len(active_ads)}</b> / {len(ads)}\n"
        f"{tg_emoji('GROUPS')} Активных групп: <b>{len(active_groups)}</b> / {len(groups)}\n\n"
        "Авторизация аккаунта <b>не обязательна</b>.\n"
        "QR в «Мой аккаунт» — только если хочешь посты совсем без ручной пересылки."
    )
    return text, user.autopost_enabled


@router.message(F.text == "Автопостинг")
async def autopost_menu(message: Message):
    text, enabled = await build_autopost_text(message.from_user.id)
    await message.answer(text, reply_markup=autopost_kb(enabled))


@router.callback_query(F.data == "ap_start")
async def ap_start(callback: CallbackQuery):
    user = await get_or_create_user(callback.from_user.id, callback.from_user.username)
    if not has_active_subscription(user):
        await callback.answer("Нужна активная подписка", show_alert=True)
        return
    groups = await get_user_groups(user.id)
    ads = await get_user_ads(user.id)
    if not any(g.active for g in groups):
        await callback.answer("Сначала добавь группу", show_alert=True)
        return
    if not any(a.status == "active" for a in ads):
        await callback.answer("Сначала запусти объявление", show_alert=True)
        return
    await set_autopost_enabled(callback.from_user.id, True)
    text, enabled = await build_autopost_text(callback.from_user.id)
    await callback.message.edit_text(text, reply_markup=autopost_kb(enabled))
    await callback.answer("Автопостинг включён")


@router.callback_query(F.data == "ap_stop")
async def ap_stop(callback: CallbackQuery):
    await set_autopost_enabled(callback.from_user.id, False)
    text, enabled = await build_autopost_text(callback.from_user.id)
    await callback.message.edit_text(text, reply_markup=autopost_kb(enabled))
    await callback.answer("Автопостинг выключен")
