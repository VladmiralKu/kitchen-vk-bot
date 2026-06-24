from dataclasses import dataclass

from app.models.constants import ACTIVE_STATUS, DELETED_STATUS, ROLE_ADMIN, ROLE_COOK, ROLE_WAITER
from app.services.permissions import can_create_order, can_export, can_manage_users, can_mark_item_ready


@dataclass
class UserStub:
    role: str
    status: str = ACTIVE_STATUS


def test_waiter_can_create_order_but_cannot_export():
    user = UserStub(role=ROLE_WAITER)

    assert can_create_order(user)
    assert not can_export(user)


def test_cook_can_mark_ready_but_cannot_create_order():
    user = UserStub(role=ROLE_COOK)

    assert can_mark_item_ready(user)
    assert not can_create_order(user)


def test_admin_can_manage_users_and_export():
    user = UserStub(role=ROLE_ADMIN)

    assert can_manage_users(user)
    assert can_export(user)


def test_deleted_user_has_no_permissions():
    user = UserStub(role=ROLE_ADMIN, status=DELETED_STATUS)

    assert not can_create_order(user)
    assert not can_mark_item_ready(user)
    assert not can_export(user)
