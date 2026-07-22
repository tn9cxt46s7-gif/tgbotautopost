from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from utils.i18n import all_btn
from keyboards import (
    main_menu, cancel_kb, main_menu_kb, cancel_kb_for, skip_photo_kb, skip_price_kb,
    ads_list_kb, ad_card_kb,
)
from database import (
    get_or_create_user, get_user, create_ad, get_ad, get_user_ads,
    count_user_ads, update_ad, delete_ad,
)
from utils.emoji import tg_emoji
from utils.subscription import has_active_subscription, effective_limits
from utils.antibot import validate_ad_text
from states import AdCreate, AdEdit

router = Router()


def format_ad(ad) -> str:
    price = f"\n{tg_emoji('PRICE')} Цена: <b>{ad.price}</b>" if ad.price else ""
    status_map = {
        "draft": "черновик",
        "active": "активно",
        "paused": "пауза",
        "sold": "продано",
    }
    return (
        f"{tg_emoji('ADS')} <b>Объявление #{ad.id}</b>\n"
        f"Статус: <b>{status_map.get(ad.status, ad.status)}</b>\n"
        f"Интервал: {ad.interval_minutes} мин\n\n"
        f"{ad.text}{price}"
    )


async def show_ads_list(target, telegram_id: int, edit: bool = False):
    user = await get_user(telegram_id)
    if not user:
        user = await get_or_create_user(telegram_id)
    ads = await get_user_ads(user.id)
    limits = effective_limits(user)
    header = (
        f"{tg_emoji('ADS')} <b>Мои объявления</b>\n"
        f"Использовано: {len([a for a in ads if a.status != 'sold'])}/{limits['ads']}\n"
    )
    if not ads:
        text = header + f"\n{tg_emoji('EMPTY')} Пока пусто. Создай первое объявление."
    else:
        text = header + "\nВыбери объявление:"
    kb = ads_list_kb(ads)
    if edit and hasattr(target, "edit_text"):
        await target.edit_text(text, reply_markup=kb)
    else:
        await target.answer(text, reply_markup=kb)


@router.message(F.text.in_(all_btn("ads")))
async def my_ads(message: Message):
    await show_ads_list(message, message.from_user.id)


@router.callback_query(F.data == "ads_list")
async def ads_list_cb(callback: CallbackQuery):
    await show_ads_list(callback.message, callback.from_user.id, edit=True)
    await callback.answer()


@router.message(F.text.in_(all_btn("add_ad")))
@router.callback_query(F.data == "ad_create")
async def add_ad_start(event: Message | CallbackQuery, state: FSMContext):
    user = await get_or_create_user(
        event.from_user.id,
        event.from_user.username,
    )
    if not has_active_subscription(user):
        text = f"{tg_emoji('WARN')} Нужна активная подписка, чтобы создавать объявления."
        if isinstance(event, CallbackQuery):
            await event.answer(text, show_alert=True)
        else:
            await event.answer(text)
        return

    limits = effective_limits(user)
    count = await count_user_ads(user.id)
    if count >= limits["ads"]:
        text = f"{tg_emoji('WARN')} Лимит объявлений по плану: {limits['ads']}. Улучши подписку."
        if isinstance(event, CallbackQuery):
            await event.answer(text, show_alert=True)
        else:
            await event.answer(text)
        return

    await state.set_state(AdCreate.text)
    prompt = (
        f"{tg_emoji('ADD')} <b>Новое объявление</b>\n\n"
        "Пришли текст объявления (что продаёшь, состояние, город, контакты):"
    )
    if isinstance(event, CallbackQuery):
        await event.message.answer(prompt, reply_markup=cancel_kb)
        await event.answer()
    else:
        await event.answer(prompt, reply_markup=cancel_kb)


@router.message(AdCreate.text)
async def ad_text_step(message: Message, state: FSMContext):
    if message.text in all_btn("cancel"):
        await state.clear()
        await message.answer("Отменено.", reply_markup=main_menu)
        return
    text = (message.text or "").strip()
    risk = validate_ad_text(text)
    if risk:
        await message.answer(f"{tg_emoji('WARN')} {risk}")
        return
    await state.update_data(text=text)
    await state.set_state(AdCreate.photo)
    await message.answer(
        f"{tg_emoji('PHOTO')} Пришли фото товара или нажми «Без фото»:",
        reply_markup=skip_photo_kb(),
    )


@router.callback_query(F.data == "ad_skip_photo", AdCreate.photo)
async def ad_skip_photo(callback: CallbackQuery, state: FSMContext):
    await state.update_data(photo_file_id=None)
    await state.set_state(AdCreate.price)
    await callback.message.answer(
        f"{tg_emoji('PRICE')} Укажи цену (например <code>5000 руб</code>) или «Без цены»:",
        reply_markup=skip_price_kb(),
    )
    await callback.answer()


@router.message(AdCreate.photo, F.photo)
async def ad_photo_step(message: Message, state: FSMContext):
    photo_id = message.photo[-1].file_id
    await state.update_data(photo_file_id=photo_id)
    await state.set_state(AdCreate.price)
    await message.answer(
        f"{tg_emoji('PRICE')} Укажи цену или нажми «Без цены»:",
        reply_markup=skip_price_kb(),
    )


@router.message(AdCreate.photo)
async def ad_photo_invalid(message: Message):
    if message.text in all_btn("cancel"):
        return
    await message.answer("Пришли фото или нажми «Без фото».")


async def _finish_ad(message_or_cb, state: FSMContext, price: str | None):
    data = await state.get_data()
    await state.clear()
    user = await get_or_create_user(message_or_cb.from_user.id, message_or_cb.from_user.username)
    ad = await create_ad(
        user_id=user.id,
        text=data["text"],
        price=price,
        photo_file_id=data.get("photo_file_id"),
        interval_minutes=user.default_interval or 60,
        status="draft",
    )
    target = message_or_cb.message if isinstance(message_or_cb, CallbackQuery) else message_or_cb
    notice = f"{tg_emoji('OK')} Объявление #{ad.id} создано (черновик). Запусти его, когда будешь готов."
    if ad.photo_file_id:
        await target.answer_photo(
            ad.photo_file_id,
            caption=format_ad(ad),
            reply_markup=ad_card_kb(ad),
        )
    else:
        await target.answer(format_ad(ad), reply_markup=ad_card_kb(ad))
    if isinstance(message_or_cb, CallbackQuery):
        await message_or_cb.answer()
    await target.answer(notice, reply_markup=main_menu)


@router.callback_query(F.data == "ad_skip_price", AdCreate.price)
async def ad_skip_price(callback: CallbackQuery, state: FSMContext):
    await _finish_ad(callback, state, None)


@router.message(AdCreate.price)
async def ad_price_step(message: Message, state: FSMContext):
    if message.text in all_btn("cancel"):
        await state.clear()
        await message.answer("Отменено.", reply_markup=main_menu)
        return
    price = message.text.strip() if message.text else None
    await _finish_ad(message, state, price)


@router.callback_query(F.data == "ad_cancel")
async def ad_cancel(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.answer("Отменено.", reply_markup=main_menu)
    await callback.answer()


@router.callback_query(F.data.startswith("ad_view_"))
async def ad_view(callback: CallbackQuery):
    ad_id = int(callback.data.removeprefix("ad_view_"))
    ad = await get_ad(ad_id)
    user = await get_user(callback.from_user.id)
    if not ad or not user or ad.user_id != user.id:
        await callback.answer("Не найдено", show_alert=True)
        return
    if ad.photo_file_id:
        try:
            await callback.message.delete()
        except Exception:
            pass
        await callback.message.answer_photo(ad.photo_file_id, caption=format_ad(ad), reply_markup=ad_card_kb(ad))
    else:
        await callback.message.edit_text(format_ad(ad), reply_markup=ad_card_kb(ad))
    await callback.answer()


@router.callback_query(F.data.startswith("ad_start_"))
async def ad_start(callback: CallbackQuery):
    ad_id = int(callback.data.removeprefix("ad_start_"))
    ad = await get_ad(ad_id)
    user = await get_user(callback.from_user.id)
    if not ad or not user or ad.user_id != user.id:
        await callback.answer("Не найдено", show_alert=True)
        return
    if not has_active_subscription(user):
        await callback.answer("Нужна активная подписка", show_alert=True)
        return
    ad = await update_ad(ad_id, status="active")
    await callback.answer("Запущено!")
    try:
        await callback.message.edit_caption(caption=format_ad(ad), reply_markup=ad_card_kb(ad))
    except Exception:
        await callback.message.edit_text(format_ad(ad), reply_markup=ad_card_kb(ad))


@router.callback_query(F.data.startswith("ad_pause_"))
async def ad_pause(callback: CallbackQuery):
    ad_id = int(callback.data.removeprefix("ad_pause_"))
    ad = await get_ad(ad_id)
    user = await get_user(callback.from_user.id)
    if not ad or not user or ad.user_id != user.id:
        await callback.answer("Не найдено", show_alert=True)
        return
    ad = await update_ad(ad_id, status="paused")
    await callback.answer("На паузе")
    try:
        await callback.message.edit_caption(caption=format_ad(ad), reply_markup=ad_card_kb(ad))
    except Exception:
        await callback.message.edit_text(format_ad(ad), reply_markup=ad_card_kb(ad))


@router.callback_query(F.data.startswith("ad_sold_"))
async def ad_sold(callback: CallbackQuery):
    ad_id = int(callback.data.removeprefix("ad_sold_"))
    ad = await get_ad(ad_id)
    user = await get_user(callback.from_user.id)
    if not ad or not user or ad.user_id != user.id:
        await callback.answer("Не найдено", show_alert=True)
        return
    ad = await update_ad(ad_id, status="sold")
    await callback.answer("Отмечено как продано")
    try:
        await callback.message.edit_caption(caption=format_ad(ad), reply_markup=ad_card_kb(ad))
    except Exception:
        await callback.message.edit_text(format_ad(ad), reply_markup=ad_card_kb(ad))


@router.callback_query(F.data.startswith("ad_del_"))
async def ad_delete(callback: CallbackQuery):
    ad_id = int(callback.data.removeprefix("ad_del_"))
    ad = await get_ad(ad_id)
    user = await get_user(callback.from_user.id)
    if not ad or not user or ad.user_id != user.id:
        await callback.answer("Не найдено", show_alert=True)
        return
    await delete_ad(ad_id)
    await callback.answer("Удалено")
    await show_ads_list(callback.message, callback.from_user.id, edit=True)


@router.callback_query(F.data.startswith("ad_edit_text_"))
async def ad_edit_text_start(callback: CallbackQuery, state: FSMContext):
    ad_id = int(callback.data.removeprefix("ad_edit_text_"))
    await state.set_state(AdEdit.text)
    await state.update_data(edit_ad_id=ad_id)
    await callback.message.answer(f"{tg_emoji('EDIT')} Пришли новый текст объявления:", reply_markup=cancel_kb)
    await callback.answer()


@router.message(AdEdit.text)
async def ad_edit_text_save(message: Message, state: FSMContext):
    if message.text in all_btn("cancel"):
        await state.clear()
        await message.answer("Отменено.", reply_markup=main_menu)
        return
    text = (message.text or "").strip()
    risk = validate_ad_text(text)
    if risk:
        await message.answer(f"{tg_emoji('WARN')} {risk}")
        return
    data = await state.get_data()
    ad_id = data["edit_ad_id"]
    user = await get_user(message.from_user.id)
    ad = await get_ad(ad_id)
    if not ad or not user or ad.user_id != user.id:
        await state.clear()
        await message.answer("Не найдено.", reply_markup=main_menu)
        return
    title = text.split("\n")[0][:80]
    await update_ad(ad_id, text=text, title=title)
    await state.clear()
    await message.answer(f"{tg_emoji('OK')} Текст обновлён.", reply_markup=main_menu)


@router.callback_query(F.data.startswith("ad_edit_price_"))
async def ad_edit_price_start(callback: CallbackQuery, state: FSMContext):
    ad_id = int(callback.data.removeprefix("ad_edit_price_"))
    await state.set_state(AdEdit.price)
    await state.update_data(edit_ad_id=ad_id)
    await callback.message.answer(f"{tg_emoji('PRICE')} Пришли новую цену (или «-» чтобы убрать):", reply_markup=cancel_kb)
    await callback.answer()


@router.message(AdEdit.price)
async def ad_edit_price_save(message: Message, state: FSMContext):
    if message.text in all_btn("cancel"):
        await state.clear()
        await message.answer("Отменено.", reply_markup=main_menu)
        return
    data = await state.get_data()
    ad_id = data["edit_ad_id"]
    user = await get_user(message.from_user.id)
    ad = await get_ad(ad_id)
    if not ad or not user or ad.user_id != user.id:
        await state.clear()
        await message.answer("Не найдено.", reply_markup=main_menu)
        return
    price = None if message.text.strip() == "-" else message.text.strip()
    await update_ad(ad_id, price=price)
    await state.clear()
    await message.answer(f"{tg_emoji('OK')} Цена обновлена.", reply_markup=main_menu)
