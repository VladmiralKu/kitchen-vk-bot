from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from datetime import date, datetime, time, timezone
from pathlib import Path
from urllib.parse import quote
from zoneinfo import ZoneInfo

import httpx
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.config import Settings
from app.models.order import Order
from app.models.order_item import OrderItem


GOOGLE_SHEETS_SCOPE = "https://www.googleapis.com/auth/spreadsheets"
GOOGLE_SHEETS_API = "https://sheets.googleapis.com/v4/spreadsheets"

HEADERS = [
    "order_date",
    "order_no",
    "order_status",
    "table_number",
    "waiter_name",
    "waiter_vk_id",
    "item_index",
    "course",
    "item_name",
    "quantity",
    "item_status",
    "item_created_at",
    "item_ready_at",
    "ready_by_name",
    "ready_by_vk_id",
    "item_ready_seconds",
    "item_ready_minutes",
    "order_created_at",
    "order_ready_at",
    "order_completed_at",
    "order_cancelled_at",
    "order_total_ready_seconds",
    "order_total_ready_minutes",
    "comment",
    "raw_text",
]


class GoogleSheetsExportError(RuntimeError):
    pass


@dataclass(frozen=True)
class GoogleSheetsExportResult:
    spreadsheet_id: str
    sheet_title: str
    day: date
    orders_count: int
    rows_count: int

    @property
    def url(self) -> str:
        return f"https://docs.google.com/spreadsheets/d/{self.spreadsheet_id}"


async def export_day_to_google_sheet(session, settings: Settings, day: date) -> GoogleSheetsExportResult:
    if not settings.google_sheets_spreadsheet_id:
        raise GoogleSheetsExportError("Не заполнен GOOGLE_SHEETS_SPREADSHEET_ID.")

    token = await asyncio.to_thread(_get_access_token, settings)
    headers = {"Authorization": f"Bearer {token}"}
    sheet_title = day.strftime("%Y-%m")
    timezone_name = settings.app_timezone
    orders = await _load_orders(session, day, timezone_name)
    rows = build_google_sheet_rows(orders, timezone_name)

    async with httpx.AsyncClient(timeout=30) as client:
        sheets = await _get_sheets(client, settings.google_sheets_spreadsheet_id, headers)
        if sheet_title not in sheets:
            await _add_sheet(client, settings.google_sheets_spreadsheet_id, headers, sheet_title)

        existing_values = await _get_values(client, settings.google_sheets_spreadsheet_id, headers, sheet_title)
        merged_values = _replace_day_rows(existing_values, day, rows)
        await _write_values(client, settings.google_sheets_spreadsheet_id, headers, sheet_title, merged_values)
        if len(existing_values) > len(merged_values):
            start_row = len(merged_values) + 1
            await _clear_values(client, settings.google_sheets_spreadsheet_id, headers, sheet_title, f"A{start_row}:Z{len(existing_values)}")

    return GoogleSheetsExportResult(
        spreadsheet_id=settings.google_sheets_spreadsheet_id,
        sheet_title=sheet_title,
        day=day,
        orders_count=len(orders),
        rows_count=len(rows),
    )


def build_google_sheet_rows(orders: list, timezone_name: str) -> list[list]:
    rows: list[list] = []
    for order in orders:
        items = list(getattr(order, "items", []) or [])
        if not items:
            rows.append(_row_for_order_item(order, None, timezone_name))
            continue
        for item in items:
            rows.append(_row_for_order_item(order, item, timezone_name))
    return rows


async def _load_orders(session, day: date, timezone_name: str) -> list[Order]:
    start_utc, end_utc = _day_bounds_utc(day, timezone_name)
    result = await session.execute(
        select(Order)
        .options(
            selectinload(Order.waiter),
            selectinload(Order.items).selectinload(OrderItem.ready_by_user),
        )
        .where(Order.created_at >= start_utc, Order.created_at <= end_utc)
        .order_by(Order.created_at, Order.order_no)
    )
    return list(result.scalars().unique())


def _day_bounds_utc(day: date, timezone_name: str) -> tuple[datetime, datetime]:
    tz = ZoneInfo(timezone_name)
    start_local = datetime.combine(day, time.min, tzinfo=tz)
    end_local = datetime.combine(day, time.max, tzinfo=tz)
    return start_local.astimezone(timezone.utc), end_local.astimezone(timezone.utc)


def _get_access_token(settings: Settings) -> str:
    try:
        from google.auth.transport.requests import Request as GoogleAuthRequest
        from google.oauth2 import service_account
    except ImportError as exc:
        raise GoogleSheetsExportError("Не установлена зависимость google-auth. Обновите сервер через docker compose up -d --build.") from exc

    service_account_info = _load_service_account_info(settings)
    credentials = service_account.Credentials.from_service_account_info(
        service_account_info,
        scopes=[GOOGLE_SHEETS_SCOPE],
    )
    credentials.refresh(GoogleAuthRequest())
    if not credentials.token:
        raise GoogleSheetsExportError("Google не вернул access token для сервисного аккаунта.")
    return credentials.token


def _load_service_account_info(settings: Settings) -> dict:
    if settings.google_service_account_json:
        try:
            return json.loads(settings.google_service_account_json)
        except json.JSONDecodeError as exc:
            raise GoogleSheetsExportError("GOOGLE_SERVICE_ACCOUNT_JSON не похож на JSON.") from exc

    if settings.google_service_account_file:
        path = Path(settings.google_service_account_file)
        if not path.exists():
            raise GoogleSheetsExportError(f"Файл сервисного аккаунта не найден: {path}")
        return json.loads(path.read_text(encoding="utf-8"))

    raise GoogleSheetsExportError("Не заполнен GOOGLE_SERVICE_ACCOUNT_FILE или GOOGLE_SERVICE_ACCOUNT_JSON.")


async def _get_sheets(client: httpx.AsyncClient, spreadsheet_id: str, headers: dict[str, str]) -> set[str]:
    response = await client.get(
        f"{GOOGLE_SHEETS_API}/{quote(spreadsheet_id, safe='')}",
        headers=headers,
        params={"fields": "sheets.properties.title"},
    )
    _raise_for_google_response(response)
    data = response.json()
    return {sheet["properties"]["title"] for sheet in data.get("sheets", [])}


async def _add_sheet(client: httpx.AsyncClient, spreadsheet_id: str, headers: dict[str, str], sheet_title: str) -> None:
    response = await client.post(
        f"{GOOGLE_SHEETS_API}/{quote(spreadsheet_id, safe='')}:batchUpdate",
        headers=headers,
        json={"requests": [{"addSheet": {"properties": {"title": sheet_title}}}]},
    )
    _raise_for_google_response(response)


async def _get_values(client: httpx.AsyncClient, spreadsheet_id: str, headers: dict[str, str], sheet_title: str) -> list[list]:
    response = await client.get(
        f"{GOOGLE_SHEETS_API}/{quote(spreadsheet_id, safe='')}/values/{_range_path(sheet_title, 'A:Z')}",
        headers=headers,
    )
    if response.status_code == 404:
        return []
    _raise_for_google_response(response)
    return response.json().get("values", [])


async def _clear_values(client: httpx.AsyncClient, spreadsheet_id: str, headers: dict[str, str], sheet_title: str, cells: str) -> None:
    response = await client.post(
        f"{GOOGLE_SHEETS_API}/{quote(spreadsheet_id, safe='')}/values/{_range_path(sheet_title, cells)}:clear",
        headers=headers,
        json={},
    )
    _raise_for_google_response(response)


async def _write_values(
    client: httpx.AsyncClient,
    spreadsheet_id: str,
    headers: dict[str, str],
    sheet_title: str,
    values: list[list],
) -> None:
    response = await client.put(
        f"{GOOGLE_SHEETS_API}/{quote(spreadsheet_id, safe='')}/values/{_range_path(sheet_title, 'A1')}",
        headers=headers,
        params={"valueInputOption": "RAW"},
        json={"values": values},
    )
    _raise_for_google_response(response)


def _replace_day_rows(existing_values: list[list], day: date, new_rows: list[list]) -> list[list]:
    target = day.isoformat()
    data_rows = existing_values[1:] if existing_values and existing_values[0] == HEADERS else existing_values
    kept_rows = [row for row in data_rows if not row or row[0] != target]
    rows = [_pad_row(row) for row in kept_rows + new_rows]
    rows.sort(key=_row_sort_key)
    return [HEADERS, *rows]


def _row_for_order_item(order, item, timezone_name: str) -> list:
    created_at = getattr(order, "created_at", None)
    order_date = _local_date(created_at, timezone_name)
    waiter = getattr(order, "waiter", None)
    ready_by = getattr(item, "ready_by_user", None) if item is not None else None
    item_ready_seconds = getattr(item, "ready_seconds", None) if item is not None else None
    order_ready_seconds = getattr(order, "total_ready_seconds", None)

    return [
        order_date,
        getattr(order, "order_no", None),
        getattr(order, "status", None),
        getattr(order, "table_number", None),
        getattr(waiter, "display_name", None),
        getattr(waiter, "vk_user_id", None),
        getattr(item, "position_index", None) if item is not None else None,
        getattr(item, "course", None) if item is not None else None,
        getattr(item, "name", None) if item is not None else None,
        _quantity_value(getattr(item, "quantity", None)) if item is not None else None,
        getattr(item, "status", None) if item is not None else None,
        _local_datetime(getattr(item, "created_at", None), timezone_name) if item is not None else None,
        _local_datetime(getattr(item, "ready_at", None), timezone_name) if item is not None else None,
        getattr(ready_by, "display_name", None),
        getattr(ready_by, "vk_user_id", None),
        item_ready_seconds,
        round(item_ready_seconds / 60, 2) if item_ready_seconds is not None else None,
        _local_datetime(created_at, timezone_name),
        _local_datetime(getattr(order, "ready_at", None), timezone_name),
        _local_datetime(getattr(order, "completed_at", None), timezone_name),
        _local_datetime(getattr(order, "cancelled_at", None), timezone_name),
        order_ready_seconds,
        round(order_ready_seconds / 60, 2) if order_ready_seconds is not None else None,
        getattr(order, "comment", None),
        getattr(order, "raw_text", None),
    ]


def _local_date(value: datetime | None, timezone_name: str) -> str:
    if value is None:
        return ""
    return value.astimezone(ZoneInfo(timezone_name)).date().isoformat()


def _local_datetime(value: datetime | None, timezone_name: str) -> str:
    if value is None:
        return ""
    return value.astimezone(ZoneInfo(timezone_name)).strftime("%Y-%m-%d %H:%M:%S")


def _quantity_value(value):
    if value is None:
        return ""
    return float(value)


def _range_path(sheet_title: str, cells: str) -> str:
    escaped_title = sheet_title.replace("'", "''")
    return quote(f"'{escaped_title}'!{cells}", safe="")


def _pad_row(row: list) -> list:
    return [*(row[: len(HEADERS)]), *([""] * max(len(HEADERS) - len(row), 0))]


def _row_sort_key(row: list) -> tuple:
    return (row[0], _safe_int(row[1]), _safe_int(row[6]))


def _safe_int(value) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _raise_for_google_response(response: httpx.Response) -> None:
    if response.status_code < 400:
        return
    try:
        payload = response.json()
        message = payload.get("error", {}).get("message") or response.text
    except ValueError:
        message = response.text
    raise GoogleSheetsExportError(f"Google Sheets API вернул {response.status_code}: {message}")
