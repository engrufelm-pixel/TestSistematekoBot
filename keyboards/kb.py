from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from config import ROOM_TYPES, CLEANING_TYPES, EXTRA_SERVICES, STATUSES


def main_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🧹 Создать заявку", callback_data="new_order")],
        [InlineKeyboardButton("📋 Мои заявки", callback_data="my_orders")],
        [InlineKeyboardButton("❓ Помощь", callback_data="show_help")],
    ])


def room_type_kb() -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(label, callback_data=f"rt_{key}")]
        for key, label in ROOM_TYPES.items()
    ]
    rows.append([InlineKeyboardButton("❌ Отмена", callback_data="cancel_order")])
    return InlineKeyboardMarkup(rows)


def cleaning_type_kb() -> InlineKeyboardMarkup:
    rows = []
    for key, info in CLEANING_TYPES.items():
        rows.append([InlineKeyboardButton(info["label"], callback_data=f"ct_{key}")])
    rows.append([InlineKeyboardButton("❌ Отмена", callback_data="cancel_order")])
    return InlineKeyboardMarkup(rows)


def extra_services_kb(selected: list) -> InlineKeyboardMarkup:
    rows = []
    for key, info in EXTRA_SERVICES.items():
        tick = "✅ " if key in selected else ""
        label = f"{tick}{info['label']} (+{info['price']:,} ₽)".replace(",", " ")
        rows.append([InlineKeyboardButton(label, callback_data=f"ex_{key}")])

    rows.append([
        InlineKeyboardButton("⏭ Пропустить", callback_data="ex_skip"),
        InlineKeyboardButton("✔️ Готово", callback_data="ex_done"),
    ])
    return InlineKeyboardMarkup(rows)


def photo_kb(count: int = 0) -> InlineKeyboardMarkup:
    added = f" ({count} шт.)" if count else ""
    rows = []
    if count > 0:
        rows.append([InlineKeyboardButton(f"✔️ Готово{added}", callback_data="photo_done")])
    rows.append([InlineKeyboardButton("⏭ Пропустить", callback_data="photo_skip")])
    return InlineKeyboardMarkup(rows)


def confirm_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Отправить заявку", callback_data="order_confirm")],
        [InlineKeyboardButton("✏️ Начать заново", callback_data="new_order")],
        [InlineKeyboardButton("❌ Отмена", callback_data="cancel_order")],
    ])


def back_to_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")],
    ])


def my_orders_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🧹 Создать новую заявку", callback_data="new_order")],
        [InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")],
    ])


def admin_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📋 Все заявки", callback_data="adm_list_all")],
        [InlineKeyboardButton("🆕 Новые заявки", callback_data="adm_list_new")],
        [InlineKeyboardButton("🔍 Фильтр по статусу", callback_data="adm_filter")],
        [InlineKeyboardButton("📊 Аналитика", callback_data="adm_analytics")],
    ])


def orders_list_kb(orders: list, back_data: str = "adm_menu") -> InlineKeyboardMarkup:
    rows = []
    for o in orders[:20]:
        status_text = STATUSES.get(o["status"], o["status"])
        status_icon = status_text.split()[0] if status_text else "•"
        rows.append([
            InlineKeyboardButton(
                f"#{o['id']} — {o['contact_name']} — {status_icon}",
                callback_data=f"adm_order_{o['id']}"
            )
        ])
    rows.append([InlineKeyboardButton("◀ Назад", callback_data=back_data)])
    return InlineKeyboardMarkup(rows)


def order_actions_kb(order_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔄 Изменить статус", callback_data=f"adm_setstatus_{order_id}")],
        [InlineKeyboardButton("📷 Показать фото", callback_data=f"adm_photos_{order_id}")],
        [InlineKeyboardButton("◀ К списку заявок", callback_data="adm_list_all")],
    ])


def status_choice_kb(order_id: int) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(label, callback_data=f"adm_status_{order_id}_{key}")]
        for key, label in STATUSES.items()
    ]
    rows.append([
        InlineKeyboardButton("◀ Отмена", callback_data=f"adm_order_{order_id}")
    ])
    return InlineKeyboardMarkup(rows)


def filter_kb() -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton("📋 Все заявки", callback_data="adm_list_all")]
    ]
    for key, label in STATUSES.items():
        rows.append([InlineKeyboardButton(label, callback_data=f"adm_list_{key}")])
    rows.append([InlineKeyboardButton("◀ Меню", callback_data="adm_menu")])
    return InlineKeyboardMarkup(rows)