from decimal import Decimal
from types import SimpleNamespace

from app.models.constants import ITEM_PENDING, ITEM_READY
from app.services.keyboards import MAX_INLINE_KEYBOARD_ROWS, kitchen_order_keyboards


def _item(index: int, status: str = ITEM_PENDING) -> SimpleNamespace:
    return SimpleNamespace(
        id=f"item-{index}",
        name=f"Item {index}",
        quantity=Decimal("1"),
        status=status,
        course=1 if index % 2 else 2,
    )


def _flatten_buttons(keyboard: dict) -> list[dict]:
    return [button for row in keyboard["buttons"] for button in row]


def test_kitchen_order_keyboard_splits_many_items_into_vk_row_limit() -> None:
    keyboards = kitchen_order_keyboards("order-1", [_item(index) for index in range(1, 7)])

    assert len(keyboards) == 2
    assert all(len(keyboard["buttons"]) <= MAX_INLINE_KEYBOARD_ROWS for keyboard in keyboards)
    assert sum(len(_flatten_buttons(keyboard)) for keyboard in keyboards) == 7
    assert keyboards[-1]["buttons"][-1][0]["action"]["payload"]["action"] == "mark_order_ready"


def test_kitchen_order_keyboard_keeps_all_item_buttons_by_splitting() -> None:
    keyboards = kitchen_order_keyboards("order-1", [_item(index, ITEM_READY) for index in range(1, 31)])

    assert len(keyboards) == 6
    assert all(len(keyboard["buttons"]) <= MAX_INLINE_KEYBOARD_ROWS for keyboard in keyboards)
    assert sum(len(_flatten_buttons(keyboard)) for keyboard in keyboards) == 31
    assert keyboards[-1]["buttons"][-1][0]["action"]["payload"]["action"] == "mark_order_ready"
