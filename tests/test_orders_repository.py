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
