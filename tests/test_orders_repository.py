import asyncio
from decimal import Decimal
from types import SimpleNamespace

from app.models.order_item import OrderItem
from app.repositories.orders import create_order
from app.services.parser import ParsedItem, ParsedOrder


class FakeSession:
    def __init__(self) -> None:
        self.added = []

    def add(self, item) -> None:
        self.added.append(item)

    async def flush(self) -> None:
        pass

    async def refresh(self, *_args, **_kwargs) -> None:
        pass


def test_create_order_keeps_large_quantity_as_single_item() -> None:
    session = FakeSession()
    waiter = SimpleNamespace(id="waiter-1")
    parsed = ParsedOrder(
        table_number="1",
        items=[ParsedItem(quantity=Decimal("650"), name="чай")],
        comment=None,
    )

    asyncio.run(create_order(session, waiter, parsed, "Стол 1\nчай 650"))

    items = [item for item in session.added if isinstance(item, OrderItem)]
    assert len(items) == 1
    assert items[0].name == "чай"
    assert items[0].quantity == Decimal("650")


def test_create_order_splits_leading_quantity_into_unit_items() -> None:
    session = FakeSession()
    waiter = SimpleNamespace(id="waiter-1")
    parsed = ParsedOrder(
        table_number="1",
        items=[ParsedItem(quantity=Decimal("2"), name="капучино", split_units=True)],
        comment=None,
    )

    asyncio.run(create_order(session, waiter, parsed, "Стол 1\n2 капучино"))

    items = [item for item in session.added if isinstance(item, OrderItem)]
    assert len(items) == 2
    assert [item.name for item in items] == ["капучино", "капучино"]
    assert [item.quantity for item in items] == [Decimal("1"), Decimal("1")]


def test_create_order_does_not_split_huge_leading_quantity() -> None:
    session = FakeSession()
    waiter = SimpleNamespace(id="waiter-1")
    parsed = ParsedOrder(
        table_number="1",
        items=[ParsedItem(quantity=Decimal("650"), name="чай", split_units=True)],
        comment=None,
    )

    asyncio.run(create_order(session, waiter, parsed, "Стол 1\n650 чай"))

    items = [item for item in session.added if isinstance(item, OrderItem)]
    assert len(items) == 1
    assert items[0].name == "чай"
    assert items[0].quantity == Decimal("650")
