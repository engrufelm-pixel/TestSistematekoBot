import logging

from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ConversationHandler,
    filters,
)

from config import BOT_TOKEN
from database.db import init_db

from handlers.start import cmd_start, cmd_help
from handlers.client import my_orders
from handlers.admin import (
    cmd_admin,
    adm_menu,
    adm_list,
    adm_order_detail,
    adm_show_photos,
    adm_set_status_menu,
    adm_apply_status,
    adm_filter,
    adm_analytics,
)
from handlers.order import (
    order_start,
    step_room_type,
    step_area,
    step_cleaning_type,
    step_extras_toggle,
    step_extras_done,
    step_name,
    step_phone,
    step_address,
    step_photo_receive,
    step_photo_done,
    step_confirm,
    cancel,
    S_ROOM_TYPE,
    S_AREA,
    S_CLEANING_TYPE,
    S_EXTRAS,
    S_NAME,
    S_PHONE,
    S_ADDRESS,
    S_PHOTOS,
    S_CONFIRM,
)

logging.basicConfig(
    format="%(asctime)s %(levelname)-8s %(name)s — %(message)s",
    level=logging.INFO,
)

log = logging.getLogger(__name__)


def main() -> None:
    init_db()

    app = Application.builder().token(BOT_TOKEN).build()

    order_conv = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(order_start, pattern="^new_order$"),
        ],
        states={
            S_ROOM_TYPE: [
                CallbackQueryHandler(step_room_type, pattern="^rt_"),
                CallbackQueryHandler(cancel, pattern="^cancel_order$"),
            ],
            S_AREA: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, step_area),
            ],
            S_CLEANING_TYPE: [
                CallbackQueryHandler(step_cleaning_type, pattern="^ct_"),
                CallbackQueryHandler(cancel, pattern="^cancel_order$"),
            ],
            S_EXTRAS: [
                CallbackQueryHandler(step_extras_toggle, pattern="^ex_(?!skip|done)"),
                CallbackQueryHandler(step_extras_done, pattern="^ex_(skip|done)$"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, step_name),
            ],
            S_NAME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, step_name),
            ],
            S_PHONE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, step_phone),
            ],
            S_ADDRESS: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, step_address),
            ],
            S_PHOTOS: [
                MessageHandler(filters.PHOTO, step_photo_receive),
                CallbackQueryHandler(step_photo_done, pattern="^photo_(skip|done)$"),
            ],
            S_CONFIRM: [
                CallbackQueryHandler(
                    step_confirm,
                    pattern="^(order_confirm|cancel_order|new_order)$",
                ),
            ],
        },
        fallbacks=[
            CommandHandler("cancel", cancel),
            CallbackQueryHandler(cancel, pattern="^cancel_order$"),
        ],
        allow_reentry=True,
    )

    # ConversationHandler ПЕРВЫМ
    app.add_handler(order_conv)

    # Команды
    app.add_handler(CommandHandler("start",  cmd_start))
    app.add_handler(CommandHandler("help",   cmd_help))
    app.add_handler(CommandHandler("admin",  cmd_admin))
    app.add_handler(CommandHandler("cancel", cancel))

    # Клиентские кнопки
    app.add_handler(CallbackQueryHandler(cmd_start,  pattern="^main_menu$"))
    app.add_handler(CallbackQueryHandler(cmd_help,   pattern="^show_help$"))
    app.add_handler(CallbackQueryHandler(my_orders,  pattern="^my_orders$"))

    # Админ кнопки
    app.add_handler(CallbackQueryHandler(adm_menu,            pattern="^adm_menu$"))
    app.add_handler(CallbackQueryHandler(adm_list,            pattern="^adm_list_"))
    app.add_handler(CallbackQueryHandler(adm_order_detail,    pattern=r"^adm_order_\d+$"))
    app.add_handler(CallbackQueryHandler(adm_show_photos,     pattern="^adm_photos_"))
    app.add_handler(CallbackQueryHandler(adm_set_status_menu, pattern="^adm_setstatus_"))
    app.add_handler(CallbackQueryHandler(adm_apply_status,    pattern="^adm_status_"))
    app.add_handler(CallbackQueryHandler(adm_filter,          pattern="^adm_filter$"))
    app.add_handler(CallbackQueryHandler(adm_analytics,       pattern="^adm_analytics$"))

    log.info("Бот ООО «Систематеко» запущен. Ожидаю сообщений...")
    app.run_polling(allowed_updates=["message", "callback_query"])


if __name__ == "__main__":
    main()