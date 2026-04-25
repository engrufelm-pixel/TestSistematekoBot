import logging
from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler

from config import CLEANING_TYPES, ROOM_TYPES, ADMIN_IDS, PRIORITIES
from database.db import create_order
from keyboards.kb import (
    room_type_kb,
    cleaning_type_kb,
    extra_services_kb,
    photo_kb,
    confirm_kb,
    main_menu,
)
from utils.helpers import (
    calculate_price,
    get_priority,
    is_valid_phone,
    fmt_extras,
    fmt_money,
)

log = logging.getLogger(__name__)

(
    S_ROOM_TYPE,
    S_AREA,
    S_CLEANING_TYPE,
    S_EXTRAS,
    S_NAME,
    S_PHONE,
    S_ADDRESS,
    S_PHOTOS,
    S_DATE,
    S_CONFIRM,
) = range(10)


async def order_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    await update.callback_query.answer()
    ctx.user_data.clear()
    ctx.user_data["extras"] = []
    ctx.user_data["photos"] = []

    await update.callback_query.edit_message_text(
        "🏠 <b>Шаг 1 — Тип помещения</b>\n\n"
        "Выберите тип вашего помещения:",
        reply_markup=room_type_kb(),
        parse_mode="HTML",
    )
    return S_ROOM_TYPE


async def step_room_type(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    q = update.callback_query
    await q.answer()

    key = q.data.replace("rt_", "")
    ctx.user_data["room_type"] = key
    label = ROOM_TYPES.get(key, key)

    await q.edit_message_text(
        f"✅ Помещение: <b>{label}</b>\n\n"
        "📐 <b>Шаг 2 — Площадь</b>\n\n"
        "Введите площадь помещения в м²\n"
        "<i>Например: 45 или 45.5</i>",
        parse_mode="HTML",
    )
    return S_AREA


async def step_area(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text.strip().replace(",", ".")

    try:
        area = float(text)
        if area <= 0 or area > 50000:
            raise ValueError
    except ValueError:
        await update.message.reply_text(
            "⚠️ Введите корректную площадь числом (например: <b>45</b> или <b>45.5</b>)\n"
            "Значение должно быть от 1 до 50 000 м²",
            parse_mode="HTML",
        )
        return S_AREA

    ctx.user_data["area"] = area

    await update.message.reply_text(
        f"✅ Площадь: <b>{area} м²</b>\n\n"
        "🧹 <b>Шаг 3 — Вид уборки</b>\n\n"
        "Выберите вид уборки:",
        reply_markup=cleaning_type_kb(),
        parse_mode="HTML",
    )
    return S_CLEANING_TYPE


async def step_cleaning_type(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    q = update.callback_query
    await q.answer()

    key = q.data.replace("ct_", "")
    info = CLEANING_TYPES.get(key, {})
    ctx.user_data["cleaning_type"] = key
    ctx.user_data["is_one_time"] = info.get("one_time", True)
    ctx.user_data["extras"] = []
    ctx.user_data["photos"] = []
    label = info.get("label", key)

    if not info.get("one_time", True):
        await q.edit_message_text(
            f"✅ Вид уборки: <b>{label}</b>\n\n"
            "💡 <b>Это регулярная уборка на постоянной основе.</b>\n\n"
            "Стоимость рассчитывается индивидуально — после получения заявки "
            "наш менеджер свяжется с вами для <b>назначения встречи</b> "
            "и обсуждения всех условий и цены.\n\n"
            "👤 <b>Шаг 4 — Контактные данные</b>\n\n"
            "Введите ваше имя и фамилию:",
            parse_mode="HTML",
        )
        return S_NAME

    await q.edit_message_text(
        f"✅ Вид уборки: <b>{label}</b>\n\n"
        "➕ <b>Шаг 4 — Дополнительные услуги</b>\n\n"
        "Отметьте нужные услуги (можно выбрать несколько).\n"
        "Нажмите <b>«Готово»</b> или <b>«Пропустить»</b>, если не нужны:",
        reply_markup=extra_services_kb([]),
        parse_mode="HTML",
    )
    return S_EXTRAS


async def step_extras_toggle(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    q = update.callback_query
    await q.answer()

    key = q.data.replace("ex_", "")
    extras: list = ctx.user_data.get("extras", [])

    if key in extras:
        extras.remove(key)
    else:
        extras.append(key)

    ctx.user_data["extras"] = extras
    await q.edit_message_reply_markup(reply_markup=extra_services_kb(extras))
    return S_EXTRAS


async def step_extras_done(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    q = update.callback_query
    await q.answer()

    if q.data == "ex_skip":
        ctx.user_data["extras"] = []

    await q.edit_message_text(
        "👤 <b>Шаг 5 — Контактные данные</b>\n\n"
        "Введите ваше имя и фамилию:",
        parse_mode="HTML",
    )
    return S_NAME


async def step_name(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    name = update.message.text.strip()

    if len(name) < 2 or len(name) > 100:
        await update.message.reply_text(
            "⚠️ Введите корректное имя (от 2 до 100 символов)."
        )
        return S_NAME

    ctx.user_data["contact_name"] = name

    await update.message.reply_text(
        f"✅ Имя: <b>{name}</b>\n\n"
        "📞 <b>Шаг 6 — Номер телефона</b>\n\n"
        "Введите номер телефона для связи:\n"
        "<i>Пример: +79001234567 или 89001234567</i>",
        parse_mode="HTML",
    )
    return S_PHONE


async def step_phone(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    phone = update.message.text.strip()

    if not is_valid_phone(phone):
        await update.message.reply_text(
            "⚠️ Неверный формат номера.\n"
            "Введите российский номер:\n"
            "<b>+79001234567</b> или <b>89001234567</b>",
            parse_mode="HTML",
        )
        return S_PHONE

    ctx.user_data["contact_phone"] = phone

    await update.message.reply_text(
        f"✅ Телефон: <b>{phone}</b>\n\n"
        "📍 <b>Шаг 7 — Адрес</b>\n\n"
        "Введите полный адрес объекта:\n"
        "<i>Пример: г. Сочи, ул. Навагинская, д. 16, кв. 25</i>",
        parse_mode="HTML",
    )
    return S_ADDRESS


async def step_address(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    address = update.message.text.strip()

    if len(address) < 5:
        await update.message.reply_text(
            "⚠️ Пожалуйста, введите полный адрес (город, улица, дом)."
        )
        return S_ADDRESS

    ctx.user_data["address"] = address

    await update.message.reply_text(
        f"✅ Адрес: <b>{address}</b>\n\n"
        "📸 <b>Шаг 8 — Фотографии</b>\n\n"
        "Отправьте фото помещения (необязательно).\n"
        "Можно прикрепить несколько фотографий, затем нажмите <b>«Готово»</b>.\n\n"
        "Если фото не нужны — нажмите <b>«Пропустить»</b>.",
        reply_markup=photo_kb(0),
        parse_mode="HTML",
    )
    return S_PHOTOS


async def step_photo_receive(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    file_id = update.message.photo[-1].file_id
    photos: list = ctx.user_data.get("photos", [])
    photos.append(file_id)
    ctx.user_data["photos"] = photos

    count = len(photos)
    await update.message.reply_text(
        f"📸 Фото {count} принято!\n"
        "Можете добавить ещё или нажмите «Готово».",
        reply_markup=photo_kb(count),
    )
    return S_PHOTOS


async def step_photo_done(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    q = update.callback_query
    await q.answer()

    if q.data == "photo_skip":
        ctx.user_data["photos"] = []

    if ctx.user_data.get("is_one_time", True):
        await q.message.reply_text(
            "📅 <b>Шаг 9 — Дата и время</b>\n\n"
            "Напишите удобную дату и время для уборки.\n"
            "<i>Например: завтра в 14:00 или 25 мая, утро</i>",
            parse_mode="HTML",
        )
        return S_DATE

    await q.message.reply_text("⏳ Формирую сводку заявки...")
    return await _show_summary(q.message, ctx)


async def step_date(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    desired_datetime = update.message.text.strip()

    if len(desired_datetime) < 3:
        await update.message.reply_text(
            "⚠️ Пожалуйста, укажите дату и время понятным текстом.\n"
            "<i>Например: завтра в 14:00</i>",
            parse_mode="HTML",
        )
        return S_DATE

    ctx.user_data["desired_datetime"] = desired_datetime
    await update.message.reply_text("⏳ Формирую сводку заявки...")
    return await _show_summary(update.message, ctx)


async def _show_summary(message_obj, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    d = ctx.user_data
    is_one_time = d.get("is_one_time", True)
    cleaning_type = d["cleaning_type"]
    area = d["area"]
    extras = d.get("extras", [])
    photos = d.get("photos", [])

    if is_one_time:
        price = calculate_price(cleaning_type, area, extras)
        price_text = (
            f"💰 <b>Предварительная стоимость: {fmt_money(price)}</b>\n"
            "<i>(окончательная цена может уточняться)</i>"
        )
        step_title = "📋 <b>Шаг 10 — Проверьте вашу заявку</b>\n\n"
    else:
        price = None
        price_text = (
            "💰 <b>Стоимость: договорная</b>\n"
            "📅 После отправки заявки менеджер свяжется с вами "
            "для назначения встречи."
        )
        step_title = "📋 <b>Шаг 9 — Проверьте вашу заявку</b>\n\n"

    d["price"] = price
    d["priority"] = get_priority(cleaning_type, area)

    ct_label = CLEANING_TYPES.get(cleaning_type, {}).get("label", cleaning_type)
    room_label = ROOM_TYPES.get(d["room_type"], d["room_type"])

    text = (
        step_title +
        f"🏠 <b>Помещение:</b> {room_label}\n"
        f"📐 <b>Площадь:</b> {area} м²\n"
        f"🧹 <b>Вид уборки:</b> {ct_label}\n"
    )

    if is_one_time and extras:
        text += f"➕ <b>Доп. услуги:</b>\n{fmt_extras(extras)}\n"
    elif is_one_time:
        text += "➕ <b>Доп. услуги:</b> —\n"

    text += (
        f"\n👤 <b>Имя:</b> {d['contact_name']}\n"
        f"📞 <b>Телефон:</b> {d['contact_phone']}\n"
        f"📍 <b>Адрес:</b> {d['address']}\n"
    )

    if is_one_time:
        text += f"📅 <b>Желаемая дата и время:</b> {d.get('desired_datetime', 'не указаны')}\n"

    text += (
        f"📸 <b>Фото:</b> {'есть (' + str(len(photos)) + ' шт.)' if photos else 'нет'}\n\n"
        f"{price_text}"
    )

    await message_obj.reply_text(
        text,
        reply_markup=confirm_kb(),
        parse_mode="HTML",
    )

    return S_CONFIRM


async def step_confirm(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    q = update.callback_query

    log.info("=== step_confirm ВЫЗВАН === q.data=%s", q.data)
    log.info("user_data=%s", ctx.user_data)

    await q.answer()

    if q.data == "cancel_order":
        ctx.user_data.clear()
        await q.message.reply_text(
            "❌ Заявка отменена.\n\nВы всегда можете создать новую.",
            reply_markup=main_menu(),
        )
        return ConversationHandler.END

    if q.data == "new_order":
        ctx.user_data.clear()
        ctx.user_data["extras"] = []
        ctx.user_data["photos"] = []
        await q.message.reply_text(
            "🏠 <b>Шаг 1 — Тип помещения</b>\n\n"
            "Выберите тип вашего помещения:",
            reply_markup=room_type_kb(),
            parse_mode="HTML",
        )
        return S_ROOM_TYPE

    d = ctx.user_data
    is_one_time = d.get("is_one_time", True)
    initial_status = "new" if is_one_time else "reviewing"

    admin_comment = None
    if is_one_time and d.get("desired_datetime"):
        admin_comment = f"Желаемая дата и время: {d['desired_datetime']}"

    try:
        order_id = create_order({
            "user_id": q.from_user.id,
            "room_type": d["room_type"],
            "area": d["area"],
            "cleaning_type": d["cleaning_type"],
            "is_one_time": is_one_time,
            "extra_services": d.get("extras", []),
            "contact_name": d["contact_name"],
            "contact_phone": d["contact_phone"],
            "address": d["address"],
            "photos": d.get("photos", []),
            "price": d.get("price"),
            "priority": d.get("priority", "medium"),
            "status": initial_status,
            "admin_comment": admin_comment,
        })
        log.info("=== Заявка создана: #%d ===", order_id)
    except Exception as e:
        log.error("=== ОШИБКА при создании заявки: %s ===", e)
        await q.message.reply_text(
            "❌ Произошла ошибка при создании заявки.\n"
            "Попробуйте ещё раз.",
            reply_markup=main_menu(),
        )
        return ConversationHandler.END

    if is_one_time:
        client_text = (
            f"✅ <b>Заявка #{order_id} принята!</b>\n\n"
            f"🧹 {CLEANING_TYPES.get(d['cleaning_type'], {}).get('label', '')}\n"
            f"📍 {d['address']}\n"
            f"📅 Желаемая дата и время: <b>{d.get('desired_datetime', 'не указаны')}</b>\n"
            f"💰 Стоимость: <b>{fmt_money(d.get('price'))}</b>\n\n"
            "Наш менеджер свяжется с вами для подтверждения даты и времени.\n\n"
            "📋 Статус заявки можно отслеживать в разделе <b>«Мои заявки»</b>."
        )
    else:
        client_text = (
            f"✅ <b>Заявка #{order_id} принята!</b>\n\n"
            f"🧹 {CLEANING_TYPES.get(d['cleaning_type'], {}).get('label', '')}\n"
            f"📍 {d['address']}\n\n"
            "📅 Вы выбрали <b>уборку на постоянной основе</b>.\n"
            "Стоимость рассчитывается индивидуально.\n\n"
            "Наш менеджер свяжется с вами в ближайшее время "
            "для <b>назначения встречи</b> и обсуждения условий.\n\n"
            "📋 Статус заявки можно отслеживать в разделе <b>«Мои заявки»</b>."
        )

    await q.message.reply_text(
        client_text,
        reply_markup=main_menu(),
        parse_mode="HTML",
    )

    await _notify_admins(ctx, order_id, d, q.from_user)

    ctx.user_data.clear()
    return ConversationHandler.END


async def _notify_admins(ctx, order_id: int, d: dict, user) -> None:
    from keyboards.kb import order_actions_kb

    is_one_time = d.get("is_one_time", True)
    priority = d.get("priority", "medium")
    ct_label = CLEANING_TYPES.get(d["cleaning_type"], {}).get("label", "")
    room_label = ROOM_TYPES.get(d["room_type"], "")
    price_str = fmt_money(d.get("price")) if is_one_time else "Договорная (встреча)"
    priority_label = PRIORITIES.get(priority, priority)

    text = (
        f"🔔 <b>Новая заявка #{order_id}!</b>\n\n"
        f"👤 {d['contact_name']} • {d['contact_phone']}\n"
        f"🏠 {room_label} • {d['area']} м²\n"
        f"🧹 {ct_label}\n"
        f"📍 {d['address']}\n"
    )

    if is_one_time and d.get("desired_datetime"):
        text += f"📅 {d['desired_datetime']}\n"

    text += (
        f"💰 {price_str}\n"
        f"🎯 Приоритет: {priority_label}\n"
        f"📸 Фото: {'есть (' + str(len(d.get('photos', []))) + ' шт.)' if d.get('photos') else 'нет'}"
    )

    for admin_id in ADMIN_IDS:
        try:
            await ctx.bot.send_message(
                admin_id,
                text,
                reply_markup=order_actions_kb(order_id),
                parse_mode="HTML",
            )

            if d.get("photos"):
                await ctx.bot.send_message(admin_id, f"📸 Фото к заявке #{order_id}:")
                for fid in d["photos"]:
                    await ctx.bot.send_photo(admin_id, fid)

        except Exception as e:
            log.warning("Не удалось уведомить администратора %d: %s", admin_id, e)


async def cancel(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    ctx.user_data.clear()
    text = "❌ Создание заявки отменено."

    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.message.reply_text(
            text,
            reply_markup=main_menu(),
        )
    else:
        await update.message.reply_text(
            text,
            reply_markup=main_menu(),
        )

    return ConversationHandler.END