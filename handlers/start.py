from telegram import Update
from telegram.ext import ContextTypes

from database.db import save_user
from keyboards.kb import main_menu, back_to_menu


async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик /start и кнопки «Главное меню»."""
    user = update.effective_user
    save_user(user.id, user.username, user.first_name, user.last_name)

    text = (
        f"Добро пожаловать, <b>{user.first_name}</b>! 👋\n\n"
        "Я бот клининговой компании <b>ООО «Систематеко»</b> — "
        "профессиональная уборка любых помещений в Сочи.\n\n"
        "Здесь вы можете:\n"
        "• 🧹 Оформить заявку на уборку\n"
        "• 📋 Следить за статусом своих заявок\n"
        "• 💬 Получать уведомления о ходе работ\n\n"
        "Выберите действие:"
    )

    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(
            text,
            reply_markup=main_menu(),
            parse_mode="HTML",
        )
    else:
        await update.message.reply_text(
            text,
            reply_markup=main_menu(),
            parse_mode="HTML",
        )


async def cmd_help(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик /help и кнопки «Помощь»."""
    text = (
        "📖 <b>Как оформить заявку:</b>\n\n"
        "1️⃣ Нажмите <b>«Создать заявку»</b>\n"
        "2️⃣ Выберите тип помещения\n"
        "3️⃣ Укажите площадь\n"
        "4️⃣ Выберите вид уборки\n"
        "5️⃣ Добавьте дополнительные услуги (если нужно)\n"
        "6️⃣ Введите имя, телефон и адрес\n"
        "7️⃣ Прикрепите фото помещения (необязательно)\n"
        "8️⃣ Подтвердите заявку\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "💡 <b>Важно о видах уборки:</b>\n\n"
        "📌 <b>Разовая уборка</b> — стоимость рассчитывается автоматически прямо в боте.\n\n"
        "📌 <b>Регулярная уборка / офисное обслуживание</b> — цена договорная. "
        "После получения заявки менеджер свяжется с вами для назначения встречи.\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "📞 <b>Контакты:</b>\n"
        "• Сайт: sistemateko.ru\n"
        "• Телефон: +7 (862) 123-45-67\n"
        "• Режим работы: Пн–Сб, 8:00–20:00"
    )

    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(
            text,
            parse_mode="HTML",
            reply_markup=back_to_menu(),
        )
    else:
        await update.message.reply_text(
            text,
            parse_mode="HTML",
            reply_markup=back_to_menu(),
        )