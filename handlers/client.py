# =============================================================================
#  handlers/client.py — Просмотр заявок клиентом
# =============================================================================

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from database.db import get_orders_by_user
from keyboards.kb import main_menu, my_orders_kb
from utils.helpers import order_summary


async def my_orders(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    """Показывает список заявок текущего пользователя."""
    q    = update.callback_query
    user = update.effective_user
    await q.answer()

    orders = get_orders_by_user(user.id)

    if not orders:
        await q.edit_message_text(
            "📭 <b>У вас пока нет заявок.</b>\n\n"
            "Создайте первую заявку — это быстро!",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🧹 Создать заявку", callback_data="new_order")],
                [InlineKeyboardButton("🏠 Главное меню",   callback_data="main_menu")],
            ]),
            parse_mode="HTML",
        )
        return

    # Показываем последние 10 заявок
    text = f"📋 <b>Ваши заявки ({len(orders)} шт.):</b>\n\n"
    for o in orders[:10]:
        text += order_summary(o, short=True) + "\n" + "─" * 28 + "\n"

    if len(orders) > 10:
        text += f"\n<i>Показаны последние 10 из {len(orders)} заявок.</i>"

    await q.edit_message_text(
        text,
        reply_markup=my_orders_kb(),
        parse_mode="HTML",
    )
