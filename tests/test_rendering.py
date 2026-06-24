from decimal import Decimal
from types import SimpleNamespace

from app.models.constants import ITEM_PENDING, ITEM_READY
from app.services.rendering import active_orders_list


def test_active_orders_list_shows_only_pending_items_without_tables():
    order = SimpleNamespace(
        order_no=3,
        table_number="2",
        items=[
            SimpleNamespace(name="капуч кокос", quantity=Decimal("2"), status=ITEM_PENDING),
            SimpleNamespace(name="ламаджо", quantity=Decimal("1"), status=ITEM_PENDING),
            SimpleNamespace(name="панкейки", quantity=Decimal("3"), status=ITEM_READY),
        ],
    )

    text = active_orders_list([order])

    assert "Заказ #3" in text
    assert "стол" not in text
    assert "❌ капуч кокос 2" in text
    assert "❌ ламаджо 1" in text
    assert "панкейки" not in text
