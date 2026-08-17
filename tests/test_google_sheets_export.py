from datetime import datetime, timezone
from decimal import Decimal
from types import SimpleNamespace

from app.services.google_sheets_export import HEADERS, build_google_sheet_rows


def test_build_google_sheet_rows_exports_order_and_item_fields():
    order = SimpleNamespace(
        order_no=14,
        status="ready",
        table_number="3",
        waiter=SimpleNamespace(display_name="Аида", vk_user_id=123),
        created_at=datetime(2026, 8, 16, 10, 0, tzinfo=timezone.utc),
        ready_at=datetime(2026, 8, 16, 10, 7, tzinfo=timezone.utc),
        completed_at=datetime(2026, 8, 16, 10, 7, tzinfo=timezone.utc),
        cancelled_at=None,
        total_ready_seconds=420,
        comment="без сахара",
        raw_text="Стол 3\nчай - 1\nкомм без сахара",
        items=[
            SimpleNamespace(
                position_index=1,
                course=1,
                name="чай",
                quantity=Decimal("1"),
                status="ready",
                created_at=datetime(2026, 8, 16, 10, 0, tzinfo=timezone.utc),
                ready_at=datetime(2026, 8, 16, 10, 7, tzinfo=timezone.utc),
                ready_by_user=SimpleNamespace(display_name="Повар", vk_user_id=456),
                ready_seconds=420,
            ),
        ],
    )

    rows = build_google_sheet_rows([order], "Europe/Kirov")
    row = dict(zip(HEADERS, rows[0]))

    assert row["order_date"] == "2026-08-16"
    assert row["order_no"] == 14
    assert row["waiter_name"] == "Аида"
    assert row["item_name"] == "чай"
    assert row["quantity"] == 1.0
    assert row["ready_by_name"] == "Повар"
    assert row["item_ready_minutes"] == 7
