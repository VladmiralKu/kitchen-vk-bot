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


def test_kitchen_order_keyboard_fits_six_items_without_done_all_button() -> None:
    keyboards = kitchen_order_keyboards("order-1", [_item(index) for index in range(1, 7)])

    assert len(keyboards) == 1
    assert len(keyboards[0]["buttons"]) == MAX_INLINE_KEYBOARD_ROWS
    assert all(button["action"]["payload"]["action"] == "toggle_item_ready" for button in _flatten_buttons(keyboards[0]))


def test_kitchen_order_keyboard_keeps_all_item_buttons_by_splitting() -> None:
    keyboards = kitchen_order_keyboards("order-1", [_item(index, ITEM_READY) for index in range(1, 31)])

    assert len(keyboards) == 5
    assert all(len(keyboard["buttons"]) <= MAX_INLINE_KEYBOARD_ROWS for keyboard in keyboards)
    assert sum(len(_flatten_buttons(keyboard)) for keyboard in keyboards) == 30
    assert all(button["action"]["payload"]["action"] == "toggle_item_ready" for keyboard in keyboards for button in _flatten_buttons(keyboard))


def test_kitchen_order_keyboard_shows_duplicate_unit_buttons_without_numbering() -> None:
    items = [
        _item(1),
        _item(2),
    ]
    items[0].name = "капучино"
    items[1].name = "капучино"
    items[1].course = 1
    keyboards = kitchen_order_keyboards("order-1", items)
    labels = [button["action"]["label"] for button in _flatten_buttons(keyboards[0])]

    assert labels == ["К1 не готово: капучино", "К1 не готово: капучино"]
