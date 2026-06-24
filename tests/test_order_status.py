from app.models.constants import ITEM_CANCELLED, ITEM_PENDING, ITEM_READY, ORDER_NEW, ORDER_PARTIALLY_READY, ORDER_READY
from app.services.order_status import derive_order_status, next_item_status


def test_order_ready_when_all_items_ready():
    assert derive_order_status([ITEM_READY, ITEM_READY]) == ORDER_READY


def test_order_partially_ready_when_some_items_ready():
    assert derive_order_status([ITEM_READY, ITEM_PENDING]) == ORDER_PARTIALLY_READY


def test_order_new_when_all_items_pending():
    assert derive_order_status([ITEM_PENDING, ITEM_PENDING]) == ORDER_NEW


def test_cancelled_items_do_not_block_ready_status():
    assert derive_order_status([ITEM_READY, ITEM_CANCELLED]) == ORDER_READY


def test_toggle_ready_back_to_pending_when_enabled():
    assert next_item_status(ITEM_READY, toggle_enabled=True) == ITEM_PENDING
