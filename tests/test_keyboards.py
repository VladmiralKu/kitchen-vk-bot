from decimal import Decimal
from types import SimpleNamespace

from app.models.constants import ITEM_PENDING, ITEM_READY
from app.services.keyboards import MAX_INLINE_KEYBOARD_ROWS, kitchen_order_keyboard


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


def test_kitchen_order_keyboard_packs_many_items_into_vk_row_limit() -> None:
    keyboard = kitchen_order_keyboard("order-1", [_item(index) for index in range(1, 7)])

    assert len(keyboard["buttons"]) <= MAX_INLINE_KEYBOARD_ROWS
    assert len(_flatten_buttons(keyboard)) == 7
    assert keyboard["buttons"][-1][0]["action"]["payload"]["action"] == "mark_order_ready"


def test_kitchen_order_keyboard_trims_item_buttons_before_exceeding_vk_row_limit() -> None:
    keyboard = kitchen_order_keyboard("order-1", [_item(index, ITEM_READY) for index in range(1, 31)])

    assert len(keyboard["buttons"]) == MAX_INLINE_KEYBOARD_ROWS
    assert len(_flatten_buttons(keyboard)) == 26
    assert keyboard["buttons"][-1][0]["action"]["payload"]["action"] == "mark_order_ready"
