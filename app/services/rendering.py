from datetime import datetime
from zoneinfo import ZoneInfo

from app.models.constants import ITEM_READY
from app.services.parser import format_quantity


def order_for_kitchen(order, timezone_name: str) -> str:
    created = _fmt_dt(order.created_at, timezone_name)
    lines = [
        f"Заказ #{order.order_no or '...'} • стол {order.table_number or '-'}",
        f"Создан: {created}",
        "",
    ]
    for item in order.items:
        mark = "готово" if item.status == ITEM_READY else "не готово"
        lines.append(f"[{mark}] {format_quantity(item.quantity)} {item.name}")
    if order.comment:
        lines.extend(["", f"Комментарий: {order.comment}"])
    return "\n".join(lines)


def order_for_waiter(order, timezone_name: str) -> str:
    lines = [
        f"Заказ #{order.order_no or '...'} принят",
        f"Стол: {order.table_number or '-'}",
        "",
    ]
    lines.extend(f"• {format_quantity(item.quantity)} {item.name}" for item in order.items)
    if order.comment:
        lines.extend(["", f"Комментарий: {order.comment}"])
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
        items = ", ".join(f"{format_quantity(item.quantity)} {item.name}" for item in order.items)
        lines.append(f"#{order.order_no} • стол {order.table_number or '-'} • {order.status} • {created}")
        lines.append(items)
        if order.total_ready_seconds:
            lines.append(f"Время выдачи: {round(order.total_ready_seconds / 60, 1)} мин")
        lines.append("")
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
