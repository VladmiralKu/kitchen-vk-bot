from app.models.constants import (
    ITEM_CANCELLED,
    ITEM_PENDING,
    ITEM_READY,
    ORDER_CANCELLED,
    ORDER_IN_PROGRESS,
    ORDER_NEW,
    ORDER_PARTIALLY_READY,
    ORDER_READY,
)


def derive_order_status(item_statuses: list[str], cancelled: bool = False) -> str:
    if cancelled:
        return ORDER_CANCELLED
    active_statuses = [status for status in item_statuses if status != ITEM_CANCELLED]
    if not active_statuses:
        return ORDER_NEW
    ready_count = sum(1 for status in active_statuses if status == ITEM_READY)
    if ready_count == len(active_statuses):
        return ORDER_READY
    if ready_count > 0:
        return ORDER_PARTIALLY_READY
    if any(status != ITEM_PENDING for status in active_statuses):
        return ORDER_IN_PROGRESS
    return ORDER_NEW


def next_item_status(current_status: str, toggle_enabled: bool) -> str:
    if current_status == ITEM_READY:
        return ITEM_PENDING if toggle_enabled else ITEM_READY
    if current_status == ITEM_CANCELLED:
        return ITEM_CANCELLED
    return ITEM_READY
