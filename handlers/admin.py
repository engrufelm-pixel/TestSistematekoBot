import json
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from config import ADMIN_IDS, STATUSES, NOTIFY_CLIENT_ON, CLEANING_TYPES
from database.db import get_all_orders, get_order, update_status, get_analytics
from keyboards.kb import (
    admin_menu,
    orders_list_kb,
    order_actions_kb,
    status_choice_kb,
    filter_kb,
)
from utils.helpers import order_summary, fmt_money

log = logging.getLogger(__name__)


def _is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


def _check_admin(q) -> bool:
    return _is_admin(q.from_user.id)


async def cmd_admin(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_admin(update.effective_user.id):
        await update.message.reply_text("⛔ Нет доступа.")
        return

    await update.message.reply_text(
        "🔧 <b>Панель администратора</b>\n"
        "ООО «Систематеко»\n\n"
        "Выберите действие:",
        reply_markup=admin_menu(),
        parse_mode="HTML",
    )


async def adm_menu(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    q = update.callback_query
    if not _check_admin(q):
        await q.answer("⛔ Нет доступа", show_alert=True)
        return

    await q.answer()
    await q.edit_message_text(
        "🔧 <b>Панель администратора</b>\n\n"
        "Выберите действие:",
        reply_markup=admin_menu(),
        parse_mode="HTML",
    )


async def adm_list(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    q = update.callback_query
    if not _check_admin(q):
        await q.answer("⛔ Нет доступа", show_alert=True)
        return

    await q.answer()

    data = q.data
    status_filter = None
    if data != "adm_list_all":
        status_filter = data.replace("adm_list_", "")

    orders = get_all_orders(status_filter)

    if not orders:
        filter_label = STATUSES.get(status_filter, "Все") if status_filter else "Все"
        await q.edit_message_text(
            f"📭 Заявок нет.\n<i>Фильтр: {filter_label}</i>",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔍 Фильтр", callback_data="adm_filter")],
                [InlineKeyboardButton("◀ Меню", callback_data="adm_menu")],
            ]),
            parse_mode="HTML",
        )
        return

    filter_label = STATUSES.get(status_filter, "Все") if status_filter else "Все"
    text = f"📋 <b>Заявки ({len(orders)} шт.) • {filter_label}</b>\n\n"

    for o in orders[:15]:
        st = STATUSES.get(o["status"], o["status"])
        price = fmt_money(o["price"])
        text += f"#{o['id']}  {o['contact_name']}  {price}  {st}\n"

    if len(orders) > 15:
        text += f"\n<i>Показаны последние 15 из {len(orders)}</i>"

    await q.edit_message_text(
        text,
        reply_markup=orders_list_kb(orders, back_data="adm_menu"),
        parse_mode="HTML",
    )


async def adm_order_detail(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    q = update.callback_query
    if not _check_admin(q):
        await q.answer("⛔ Нет доступа", show_alert=True)
        return

    await q.answer()

    order_id = int(q.data.replace("adm_order_", ""))
    order = get_order(order_id)

    if not order:
        await q.edit_message_text("❌ Заявка не найдена.")
        return

    await q.edit_message_text(
        order_summary(order, short=False),
        reply_markup=order_actions_kb(order_id),
        parse_mode="HTML",
    )


async def adm_show_photos(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    q = update.callback_query
    if not _check_admin(q):
        await q.answer("⛔ Нет доступа", show_alert=True)
        return

    await q.answer()

    order_id = int(q.data.replace("adm_photos_", ""))
    order = get_order(order_id)

    if not order:
        await q.edit_message_text("❌ Заявка не найдена.")
        return

    photos = json.loads(order["photos"] or "[]")

    if not photos:
        await q.edit_message_text(
            f"📷 К заявке #{order_id} фото не приложены.",
            reply_markup=order_actions_kb(order_id),
        )
        return

    await q.edit_message_text(
        f"📷 Отправляю {len(photos)} фото к заявке #{order_id}..."
    )

    for fid in photos:
        try:
            await ctx.bot.send_photo(q.from_user.id, fid)
        except Exception as e:
            log.warning("Не удалось отправить фото: %s", e)

    await ctx.bot.send_message(
        q.from_user.id,
        f"Фото к заявке #{order_id} отправлены.",
        reply_markup=order_actions_kb(order_id),
    )


async def adm_set_status_menu(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    q = update.callback_query
    if not _check_admin(q):
        await q.answer("⛔ Нет доступа", show_alert=True)
        return

    await q.answer()

    order_id = int(q.data.replace("adm_setstatus_", ""))
    order = get_order(order_id)

    if not order:
        await q.edit_message_text("❌ Заявка не найдена.")
        return

    current = STATUSES.get(order["status"], order["status"])
    await q.edit_message_text(
        f"🔄 <b>Изменить статус заявки #{order_id}</b>\n\n"
        f"Текущий статус: {current}\n\n"
        "Выберите новый статус:",
        reply_markup=status_choice_kb(order_id),
        parse_mode="HTML",
    )


async def adm_apply_status(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    q = update.callback_query
    if not _check_admin(q):
        await q.answer("⛔ Нет доступа", show_alert=True)
        return

    await q.answer("Обновляю статус...")

    # callback_data = "adm_status_{order_id}_{new_status}"
    raw = q.data.replace("adm_status_", "", 1)
    parts = raw.split("_", 1)
    order_id = int(parts[0])
    new_status = parts[1]

    user_id = update_status(order_id, new_status, q.from_user.id)

    if user_id is None:
        await q.edit_message_text("❌ Заявка не найдена.")
        return

    if new_status in NOTIFY_CLIENT_ON:
        await _notify_client(ctx.bot, user_id, order_id, new_status)

    order = get_order(order_id)
    new_label = STATUSES.get(new_status, new_status)

    await q.edit_message_text(
        f"✅ Статус заявки #{order_id} изменён на:\n<b>{new_label}</b>\n\n"
        + order_summary(order, short=False),
        reply_markup=order_actions_kb(order_id),
        parse_mode="HTML",
    )


async def _notify_client(bot, user_id: int, order_id: int, new_status: str) -> None:
    order = get_order(order_id)
    if not order:
        return

    if new_status == "meeting":
        msg = (
            f"📅 <b>Обновление по заявке #{order_id}</b>\n\n"
            "Ваша заявка рассмотрена.\n"
            "Для обсуждения условий и стоимости регулярной уборки "
            "наш менеджер <b>свяжется с вами в ближайшее время</b> "
            "для назначения встречи."
        )
    elif new_status == "approved":
        price_str = fmt_money(order["price"])
        msg = (
            f"✅ <b>Заявка #{order_id} одобрена!</b>\n\n"
            f"Стоимость: <b>{price_str}</b>\n\n"
            "Ожидайте звонка менеджера для уточнения даты и времени."
        )
    elif new_status == "in_progress":
        msg = (
            f"🧹 <b>Заявка #{order_id} выполняется!</b>\n\n"
            "Наши специалисты уже приступили к работе."
        )
    elif new_status == "done":
        msg = (
            f"✔️ <b>Заявка #{order_id} выполнена!</b>\n\n"
            "Спасибо, что выбрали <b>ООО «Систематеко»</b>!\n"
            "Будем рады видеть вас снова 😊"
        )
    elif new_status == "cancelled":
        msg = (
            f"❌ <b>Заявка #{order_id} отменена.</b>\n\n"
            "Если у вас есть вопросы — обратитесь к нам."
        )
    else:
        status_label = STATUSES.get(new_status, new_status)
        msg = (
            f"🔔 <b>Статус заявки #{order_id} обновлён:</b>\n"
            f"{status_label}"
        )

    try:
        await bot.send_message(user_id, msg, parse_mode="HTML")
    except Exception as e:
        log.warning("Не удалось уведомить клиента %d: %s", user_id, e)


async def adm_filter(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    q = update.callback_query
    if not _check_admin(q):
        await q.answer("⛔ Нет доступа", show_alert=True)
        return

    await q.answer()
    await q.edit_message_text(
        "🔍 <b>Фильтр заявок по статусу:</b>\n\nВыберите статус:",
        reply_markup=filter_kb(),
        parse_mode="HTML",
    )


async def adm_analytics(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    q = update.callback_query
    if not _check_admin(q):
        await q.answer("⛔ Нет доступа", show_alert=True)
        return

    await q.answer()

    stats = get_analytics()

    status_lines = "\n".join(
        f"  {STATUSES.get(s, s)}: <b>{cnt}</b>"
        for s, cnt in stats["by_status"]
    ) or "  —"

    top_lines = "\n".join(
        f"  {i + 1}. {CLEANING_TYPES.get(ct, {}).get('label', ct)}: <b>{cnt}</b>"
        for i, (ct, cnt) in enumerate(stats["top_services"])
    ) or "  —"

    text = (
        "📊 <b>Аналитика — ООО «Систематеко»</b>\n\n"
        f"📋 <b>Всего заявок:</b> {stats['total']}\n"
        f"📅 <b>Сегодня:</b> {stats['today']}\n"
        f"📆 <b>За 7 дней:</b> {stats['week']}\n\n"
        f"<b>По статусам:</b>\n{status_lines}\n\n"
        f"<b>Популярные услуги:</b>\n{top_lines}\n\n"
        f"📐 <b>Средняя площадь:</b> {stats['avg_area']} м²\n"
        f"💰 <b>Средняя стоимость:</b> {fmt_money(stats['avg_price'])}\n"
        f"💵 <b>Выручка (выполненные):</b> {fmt_money(stats['total_revenue'])}"
    )

    await q.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("📋 К заявкам", callback_data="adm_list_all")],
            [InlineKeyboardButton("◀ Меню", callback_data="adm_menu")],
        ]),
        parse_mode="HTML",
    )