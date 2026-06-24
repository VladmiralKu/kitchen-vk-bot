from datetime import datetime, timezone

from app.services.excel_export import build_export_workbook


def test_build_export_workbook_has_required_sheets():
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

    assert workbook.sheetnames == ["Orders", "Items", "Events", "Users", "Stats"]
    assert workbook["Orders"]["A2"].value == 1
    assert workbook["Orders"]["K2"].value == 10
