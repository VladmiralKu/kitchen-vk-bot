from datetime import datetime
from zoneinfo import ZoneInfo

from app.models.constants import ITEM_READY
from app.services.parser import format_item, format_quantity


def order_for_kitchen(order, timezone_name: str) -> str:
    return order_for_kitchen_part(order, timezone_name, order.items, 1, 1)


def order_for_kitchen_part(order, timezone_name: str, items: list, part_no: int, total_parts: int) -> str:
    created = _fmt_dt(order.created_at, timezone_name)
    title = f"Заказ #{order.order_no or '...'} • стол {order.table_number or '-'}"
    if total_parts > 1:
        title = f"{title} • часть {part_no}/{total_parts}"

    lines = [
        title,
        f"Создан: {created}",
        "",
    ]
    lines.extend(_items_by_course(items, prefix_status=True))
    if order.comment:
        lines.extend(["", f"Комм: {order.comment}"])
    return "\n".join(lines)


def order_for_waiter(order, timezone_name: str) -> str:
    lines = [
        f"Заказ #{order.order_no or '...'} принят",
        f"Стол: {order.table_number or '-'}",
        "",
    ]
    lines.extend(_items_by_course(order.items))
    if order.comment:
        lines.extend(["", f"Комм: {order.comment}"])
    return "\n".join(lines)


def ready_notification(order, timezone_name: str) -> str:
    ready = _fmt_dt(order.ready_at, timezone_name)
    minutes = round(order.total_ready_seconds / 60, 1) if order.total_ready_seconds else 0
    return f"Заказ #{order.order_no} готов.\nСтол: {order.table_number or '-'}\nГотово: {ready}\nВремя выдачи: {minutes} мин"


def orders_list(title: str, orders: list, timezone_name: str) -> str:
    if not orders:
        return f"{title}\n\nПока пусто."
    lines = [title, ""]
    for order in orders:
        created = _fmt_dt(order.created_at, timezone_name)
        items = ", ".join(f"К{_item_course(item)} {format_quantity(item.quantity)} {item.name}" for item in order.items)
        waiter = _waiter_name(order)
        waiter_part = f" • {waiter}" if waiter else ""
        lines.append(f"#{order.order_no}{waiter_part} • стол {order.table_number or '-'} • {order.status} • {created}")
        lines.append(items)
        if order.total_ready_seconds:
            lines.append(f"Время выдачи: {round(order.total_ready_seconds / 60, 1)} мин")
        lines.append("")
    return "\n".join(lines).strip()


def active_orders_list(orders: list) -> str:
    title = "Активные заказы"
    if not orders:
        return f"{title}\n\nПока пусто."

    lines = [title, ""]
    visible_count = 0
    for order in orders:
        pending_items = [item for item in order.items if item.status != ITEM_READY]
        if not pending_items:
            continue
        visible_count += 1
        waiter = _waiter_name(order)
        lines.append(f"Заказ #{order.order_no}{f' {waiter}' if waiter else ''}")
        labels = _item_display_labels(list(order.items))
        lines.extend(f"❌ К{_item_course(item)} {labels[_item_identity(item)]}" for item in pending_items)
        lines.append("")

    if visible_count == 0:
        return f"{title}\n\nПока пусто."
    return "\n".join(lines).strip()


def stops_list(stops: list, timezone_name: str) -> str:
    if not stops:
        return "Стопов нет"
    lines = ["Стопы", ""]
    for stop in stops:
        author = getattr(stop.author, "display_name", None) or str(getattr(stop.author, "vk_user_id", ""))
        created = _fmt_dt(stop.created_at, timezone_name)
        lines.append(f"{created} • {author}")
        lines.append(stop.text)
        lines.append("")
    return "\n".join(lines).strip()


def users_list(users: list) -> str:
    if not users:
        return "Сотрудников пока нет."
    lines = ["Сотрудники", ""]
    for user in users:
        name = user.display_name or "-"
        lines.append(f"{user.vk_user_id} • {user.role} • {user.status} • {name}")
    return "\n".join(lines)


def _fmt_dt(value: datetime | None, timezone_name: str) -> str:
    if value is None:
        return "-"
    return value.astimezone(ZoneInfo(timezone_name)).strftime("%H:%M")


def _item_course(item) -> int:
    return int(getattr(item, "course", 1) or 1)


def _items_by_course(items: list, prefix_status: bool = False) -> list[str]:
    lines: list[str] = []
    labels = _item_display_labels(items)
    current_course: int | None = None
    for item in items:
        course = _item_course(item)
        if course != current_course:
            if lines:
                lines.append("")
            current_course = course
            lines.append(f"К{course}")

        item_label = labels[_item_identity(item)]
        if prefix_status:
            mark = "готово" if item.status == ITEM_READY else "не готово"
            lines.append(f"[{mark}] {item_label}")
        else:
            lines.append(f"• {item_label}")
    return lines


def _item_display_labels(items: list) -> dict[str | int, str]:
    grouped: dict[tuple[int, str], list] = {}
    for item in items:
        key = (_item_course(item), item.name.strip().lower())
        grouped.setdefault(key, []).append(item)

    labels: dict[str | int, str] = {}
    for group in grouped.values():
        should_number = len(group) > 1 and all(format_quantity(item.quantity) == "1" for item in group)
        for index, item in enumerate(group, start=1):
            labels[_item_identity(item)] = f"{index}-{item.name}" if should_number else format_item(item.name, item.quantity)
    return labels


def _item_identity(item) -> str | int:
    return getattr(item, "id", id(item))


def _waiter_name(order) -> str | None:
    waiter = getattr(order, "waiter", None)
    if waiter is None:
        return None
    return getattr(waiter, "display_name", None) or str(getattr(waiter, "vk_user_id", "")).strip() or None
