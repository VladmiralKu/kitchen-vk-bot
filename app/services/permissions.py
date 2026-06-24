from app.models.constants import ACTIVE_STATUS, ROLE_ADMIN, ROLE_COOK, ROLE_WAITER


def is_active(user) -> bool:
    return bool(user) and getattr(user, "status", None) == ACTIVE_STATUS


def is_admin(user) -> bool:
    return is_active(user) and getattr(user, "role", None) == ROLE_ADMIN


def can_create_order(user) -> bool:
    return is_active(user) and getattr(user, "role", None) in {ROLE_ADMIN, ROLE_WAITER}


def can_view_kitchen(user) -> bool:
    return is_active(user) and getattr(user, "role", None) in {ROLE_ADMIN, ROLE_COOK}


def can_mark_item_ready(user) -> bool:
    return can_view_kitchen(user)


def can_view_order(user, order) -> bool:
    if not is_active(user):
        return False
    if getattr(user, "role", None) in {ROLE_ADMIN, ROLE_COOK}:
        return True
    return getattr(user, "role", None) == ROLE_WAITER and getattr(order, "waiter_id", None) == getattr(user, "id", None)


def can_cancel_order(user) -> bool:
    return is_admin(user)


def can_manage_users(user) -> bool:
    return is_admin(user)


def can_export(user) -> bool:
    return is_admin(user)


def can_use_stops(user) -> bool:
    return is_active(user)
