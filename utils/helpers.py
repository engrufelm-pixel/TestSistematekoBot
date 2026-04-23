import re
import json
from config import (
    ROOM_TYPES,
    CLEANING_TYPES,
    EXTRA_SERVICES,
    PRICE_PER_SQM,
    MIN_PRICE,
    STATUSES,
    PRIORITIES,
)


def calculate_price(cleaning_type: str, area: float, extras: list) -> float | None:
    """Считает стоимость разовой уборки."""
    base = PRICE_PER_SQM.get(cleaning_type)
    if base is None:
        return None

    total = area * base
    for key in extras:
        total += EXTRA_SERVICES.get(key, {}).get("price", 0)

    return max(round(total), MIN_PRICE)


def get_priority(cleaning_type: str, area: float) -> str:
    """Автоматически определяет приоритет заявки."""
    if cleaning_type == "after_repair" or area > 100:
        return "high"
    if area < 30:
        return "low"
    return "medium"


def is_valid_phone(phone: str) -> bool:
    """Проверяет, что номер телефона похож на российский."""
    digits = re.sub(r"[\s\-\+\(\)]", "", phone)
    return bool(re.match(r"^[78]\d{10}$", digits))


def fmt_money(amount) -> str:
    """Форматирует сумму в рублях."""
    if amount is None:
        return "Договорная"
    return f"{int(amount):,} ₽".replace(",", " ")


def fmt_extras(extras_list: list) -> str:
    """Форматирует список доп. услуг."""
    if not extras_list:
        return "—"

    lines = []
    for key in extras_list:
        info = EXTRA_SERVICES.get(key)
        if info:
            lines.append(f" • {info['label']} — {fmt_money(info['price'])}")

    return "\n".join(lines) if lines else "—"


def order_summary(order, short: bool = False) -> str:
    """Формирует текст карточки заявки."""
    extras = json.loads(order["extra_services"] or "[]")
    photos = json.loads(order["photos"] or "[]")
    status = STATUSES.get(order["status"], order["status"])
    priority = PRIORITIES.get(order["priority"], order["priority"])
    room = ROOM_TYPES.get(order["room_type"], order["room_type"])
    ct_info = CLEANING_TYPES.get(order["cleaning_type"], {})
    ct_label = ct_info.get("label", order["cleaning_type"])

    if short:
        price_str = fmt_money(order["price"])
        return (
            f"📋 <b>Заявка #{order['id']}</b> | {status}\n"
            f"🏠 {room} • {order['area']} м²\n"
            f"🧹 {ct_label}\n"
            f"💰 {price_str} • 🕐 {str(order['created_at'])[:16]}"
        )

    lines = [
        f"📋 <b>Заявка #{order['id']}</b>",
        "",
        f"<b>Тип помещения:</b> {room}",
        f"<b>Площадь:</b> {order['area']} м²",
        f"<b>Вид уборки:</b> {ct_label}",
    ]

    if extras:
        lines.append(f"<b>Доп. услуги:</b>\n{fmt_extras(extras)}")
    else:
        lines.append("<b>Доп. услуги:</b> —")

    lines += [
        "",
        f"<b>Клиент:</b> {order['contact_name']}",
        f"<b>Телефон:</b> {order['contact_phone']}",
        f"<b>Адрес:</b> {order['address']}",
        "",
        f"<b>Стоимость:</b> {fmt_money(order['price'])}",
        f"<b>Приоритет:</b> {priority}",
        f"<b>Статус:</b> {status}",
        f"<b>Фото:</b> {'есть, ' + str(len(photos)) + ' шт.' if photos else 'нет'}",
        "",
        f"<b>Создана:</b> {str(order['created_at'])[:16]}",
        f"<b>Обновлена:</b> {str(order['updated_at'])[:16]}",
    ]

    if order["admin_comment"]:
        lines.append(f"\n<b>Комментарий администратора:</b>\n{order['admin_comment']}")

    return "\n".join(lines)