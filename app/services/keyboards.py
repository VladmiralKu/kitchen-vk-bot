from collections.abc import Iterable

from app.models.constants import ITEM_READY, ROLE_ADMIN, ROLE_COOK, ROLE_WAITER
from app.services.parser import format_item

MAX_INLINE_KEYBOARD_ROWS = 6
MAX_KITCHEN_ITEM_ROWS = MAX_INLINE_KEYBOARD_ROWS - 1


def inline_keyboard(rows: list[list[dict]]) -> dict:
    return {"one_time": False, "inline": True, "buttons": rows}


def main_keyboard(role: str | None = None) -> dict:
    bottom_right = text_button("Выполненные", "secondary") if role == ROLE_COOK else text_button("Редактировать", "secondary")
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
                bottom_right,
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
                callback_button("Редактировать", {"action": "start_edit_order", "order_id": order_id}, "secondary"),
            ],
            [
                callback_button("Отправить на кухню", {"action": "send_order_to_kitchen", "order_id": order_id}, "positive"),
                callback_button("Отмена", {"action": "cancel_order", "order_id": order_id}, "negative"),
            ]
        ]
    )


def edit_order_keyboard(order_id: str) -> dict:
    return inline_keyboard([[callback_button("Редактировать заказ", {"action": "start_edit_order", "order_id": order_id}, "secondary")]])


def edit_mode_keyboard(order_id: str) -> dict:
    return inline_keyboard([[callback_button("Отмена", {"action": "cancel_edit_order", "order_id": order_id}, "negative")]])


def kitchen_item_chunks(items: Iterable) -> list[list]:
    item_list = list(items)
    if not item_list:
        return [[]]
    return [item_list[index:index + MAX_KITCHEN_ITEM_ROWS] for index in range(0, len(item_list), MAX_KITCHEN_ITEM_ROWS)]


def kitchen_order_keyboards(order_id: str, items: Iterable, include_cancel: bool = False) -> list[dict]:
    chunks = kitchen_item_chunks(items)
    keyboards: list[dict] = []
    for chunk_index, chunk in enumerate(chunks):
        rows = [[_item_button(order_id, item)] for item in chunk]
        if chunk_index == len(chunks) - 1:
            action_buttons = [callback_button("Готово всё", {"action": "mark_order_ready", "order_id": order_id}, "positive")]
            if include_cancel:
                action_buttons.append(callback_button("Отменить заказ", {"action": "cancel_order", "order_id": order_id}, "negative"))
            rows.append(action_buttons)
        keyboards.append(inline_keyboard(rows))
    return keyboards


def kitchen_order_keyboard(order_id: str, items: Iterable, include_cancel: bool = False) -> dict:
    return kitchen_order_keyboards(order_id, items, include_cancel)[0]


def obsolete_order_keyboard() -> dict:
    return inline_keyboard([[callback_button("Активные заказы", {"action": "show_orders"})]])


def _item_button(order_id: str, item) -> dict:
    mark = "готово" if item.status == ITEM_READY else "не готово"
    color = "positive" if item.status == ITEM_READY else "secondary"
    label = f"К{getattr(item, 'course', 1) or 1} {mark}: {format_item(item.name, item.quantity)}"
    return callback_button(label, {"action": "toggle_item_ready", "order_id": order_id, "item_id": item.id}, color)


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
