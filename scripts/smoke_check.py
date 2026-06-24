from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.models.constants import ACTIVE_STATUS, DELETED_STATUS, ITEM_PENDING, ITEM_READY, ROLE_ADMIN, ROLE_WAITER
from app.services.excel_export import build_export_workbook
from app.services.order_status import derive_order_status
from app.services.parser import parse_order_text
from app.services.permissions import can_create_order, can_export


class UserStub:
    def __init__(self, role: str, status: str = ACTIVE_STATUS):
        self.role = role
        self.status = status


def main() -> None:
    parsed = parse_order_text("Стол 4\n2 борщ\n1 паста\nКомментарий: без лука")
    assert parsed.table_number == "4"
    assert parsed.items[0].quantity == Decimal("2")
    assert parsed.comment == "без лука"

    assert can_create_order(UserStub(ROLE_WAITER))
    assert can_export(UserStub(ROLE_ADMIN))
    assert not can_export(UserStub(ROLE_ADMIN, DELETED_STATUS))
    assert derive_order_status([ITEM_READY, ITEM_PENDING]) == "partially_ready"

    workbook = build_export_workbook(
        {
            "orders": [
                {
                    "order_no": 1,
                    "status": "ready",
                    "table_number": "4",
                    "waiter_name": "Иван",
                    "raw_text": "2 борщ",
                    "comment": None,
                    "created_at": datetime(2026, 6, 24, 10, 0, tzinfo=timezone.utc),
                    "ready_at": datetime(2026, 6, 24, 10, 10, tzinfo=timezone.utc),
                    "completed_at": None,
                    "total_ready_seconds": 600,
                    "total_ready_minutes": 10,
                }
            ],
            "items": [],
            "events": [],
            "users": [],
            "stats": [],
        },
        "Europe/Chisinau",
    )
    assert workbook["Orders"]["A2"].value == 1
    print("smoke ok")


if __name__ == "__main__":
    main()
