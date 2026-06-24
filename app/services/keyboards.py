from collections.abc import Iterable

from app.models.constants import ITEM_READY, ROLE_ADMIN, ROLE_COOK, ROLE_WAITER
from app.services.parser import format_item


def inline_keyboard(rows: list[list[dict]]) -> dict:
    return {"one_time": False, "inline": True, "buttons": rows}


def main_keyboard() -> dict:
    return {
        "one_time": False,
        "inline": False,
        "buttons": [
            [
                text_button("Меню", "primary"),
                text_button("Активные", "secondary"),
            ],
            [
                text_button("Стопы", "secondary"),
            ],
        ],
    }


def text_button(label: str, color: str = "secondary") -> dict:
    return {
        "action": {
            "type": "text",
            "label": label,
            "payload": {"button": label.lower()},
        },
        "color": color,
    }


def callback_button(label: str, payload: dict, color: str = "secondary") -> dict:
    return {
        "action": {
            "type": "callback",
            "label": label[:40],
            "payload": payload,
        },
        "color": color,
    }


def confirm_order_keyboard(order_id: str) -> dict:
    return inline_keyboard(
        [
            [
                callback_button("Отправить на кухню", {"action": "send_order_to_kitchen", "order_id": order_id}, "positive"),
                callback_button("Отмена", {"action": "cancel_order", "order_id": order_id}, "negative"),
            ]
        ]
    )


def kitchen_order_keyboard(order_id: str, items: Iterable, include_cancel: bool = False) -> dict:
    rows: list[list[dict]] = []
    for item in items:
        mark = "готово" if item.status == ITEM_READY else "не готово"
        color = "positive" if item.status == ITEM_READY else "secondary"
        label = f"{mark}: {format_item(item.name, item.quantity)}"
        rows.append([callback_button(label, {"action": "toggle_item_ready", "order_id": order_id, "item_id": item.id}, color)])

    rows.append([callback_button("Готово всё", {"action": "mark_order_ready", "order_id": order_id}, "positive")])
    if include_cancel:
        rows.append([callback_button("Отменить заказ", {"action": "cancel_order", "order_id": order_id}, "negative")])
    return inline_keyboard(rows)


def menu_keyboard(role: str) -> dict:
    rows = [
        [callback_button("Активные заказы", {"action": "show_orders"})],
        [callback_button("Выполненные", {"action": "show_done"}), callback_button("Стопы", {"action": "show_stops"})],
    ]
    if role in {ROLE_ADMIN, ROLE_WAITER}:
        rows.insert(0, [callback_button("Новый заказ", {"action": "help_new_order"}, "primary")])
    if role == ROLE_ADMIN:
        rows.append([callback_button("Сотрудники", {"action": "show_users"}), callback_button("Экспорт Excel", {"action": "export_orders", "period": "today"})])
    if role == ROLE_COOK:
        rows.insert(0, [callback_button("Кухня", {"action": "show_orders"}, "primary")])
    return inline_keyboard(rows)
