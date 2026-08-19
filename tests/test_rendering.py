from decimal import Decimal
from types import SimpleNamespace

from app.models.constants import ITEM_PENDING, ITEM_READY
from app.services.rendering import active_orders_list, orders_list


def test_active_orders_list_shows_waiter_and_table_with_pending_items():
    order = SimpleNamespace(
        order_no=3,
        table_number="2",
        waiter=SimpleNamespace(display_name="Аида", vk_user_id=123),
        items=[
            SimpleNamespace(name="капуч кокос", quantity=Decimal("2"), status=ITEM_PENDING),
            SimpleNamespace(name="ламаджо", quantity=Decimal("1"), status=ITEM_PENDING, course=2),
            SimpleNamespace(name="панкейки", quantity=Decimal("3"), status=ITEM_READY, course=2),
        ],
    )

    text = active_orders_list([order])

    assert "Заказ #3 Аида • стол 2" in text
    assert "❌ К1 2 капуч кокос" in text
    assert "❌ К2 ламаджо" in text
    assert "панкейки" not in text


def test_active_orders_list_shows_duplicate_unit_items_without_numbering():
    order = SimpleNamespace(
        order_no=14,
        table_number="7",
        waiter=SimpleNamespace(display_name="Аида", vk_user_id=123),
        items=[
            SimpleNamespace(id="1", name="капучино", quantity=Decimal("1"), status=ITEM_PENDING),
            SimpleNamespace(id="2", name="капучино", quantity=Decimal("1"), status=ITEM_PENDING),
        ],
    )

    text = active_orders_list([order])

    assert "Заказ #14 Аида • стол 7" in text
    assert text.count("❌ К1 капучино") == 2


def test_done_orders_list_shows_waiter_name():
    order = SimpleNamespace(
        order_no=8,
        table_number="5",
        status="ready",
        created_at=None,
        total_ready_seconds=None,
        waiter=SimpleNamespace(display_name="Аида", vk_user_id=123),
        items=[
            SimpleNamespace(name="чай", quantity=Decimal("1"), course=1),
        ],
    )

    text = orders_list("Выполненные за сегодня", [order], "Europe/Kirov")

    assert "#8 • Аида • ready" in text
    assert "стол" not in text
