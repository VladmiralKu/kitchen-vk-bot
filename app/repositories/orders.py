from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.constants import (
    DONE_ORDER_STATUSES,
    ITEM_PENDING,
    ITEM_READY,
    OPEN_ORDER_STATUSES,
    ORDER_CANCELLED,
    ORDER_READY,
    ROLE_ADMIN,
    ROLE_COOK,
    ROLE_WAITER,
)
from app.models.order import Order
from app.models.order_event import OrderEvent
from app.models.order_item import OrderItem
from app.models.user import User
from app.services.order_status import derive_order_status, next_item_status
from app.services.parser import ParsedOrder


async def create_order(session: AsyncSession, waiter: User, parsed: ParsedOrder, raw_text: str) -> Order:
    order = Order(waiter_id=waiter.id, table_number=parsed.table_number, raw_text=raw_text, comment=parsed.comment)
    session.add(order)
    await session.flush()

    for index, parsed_item in enumerate(parsed.items, start=1):
        session.add(
            OrderItem(
                order_id=order.id,
                position_index=index,
                quantity=parsed_item.quantity,
                name=parsed_item.name,
                status=ITEM_PENDING,
            )
        )
    session.add(OrderEvent(order_id=order.id, user_id=waiter.id, event_type="order_created", payload={"raw_text": raw_text}))
    await session.flush()
    await session.refresh(order, attribute_names=["items"])
    return order


async def get_order(session: AsyncSession, order_id: str) -> Order | None:
    result = await session.execute(
        select(Order)
        .options(selectinload(Order.items), selectinload(Order.waiter))
        .where(Order.id == order_id)
    )
    return result.scalar_one_or_none()


async def list_active_orders(session: AsyncSession, user: User, limit: int = 20) -> list[Order]:
    query = (
        select(Order)
        .options(selectinload(Order.items), selectinload(Order.waiter))
        .where(Order.status.in_(OPEN_ORDER_STATUSES))
        .order_by(Order.created_at.desc())
        .limit(limit)
    )
    if user.role == ROLE_WAITER:
        query = query.where(Order.waiter_id == user.id)
    result = await session.execute(query)
    return list(result.scalars().unique())


async def list_done_orders(session: AsyncSession, user: User, limit: int = 20) -> list[Order]:
    query = (
        select(Order)
        .options(selectinload(Order.items), selectinload(Order.waiter))
        .where(Order.status.in_(DONE_ORDER_STATUSES))
        .order_by(Order.ready_at.desc().nullslast(), Order.created_at.desc())
        .limit(limit)
    )
    if user.role == ROLE_WAITER:
        query = query.where(Order.waiter_id == user.id)
    result = await session.execute(query)
    return list(result.scalars().unique())


async def send_to_kitchen_mark(session: AsyncSession, order: Order, actor: User) -> None:
    now = datetime.now(timezone.utc)
    if order.sent_to_kitchen_at is None:
        order.sent_to_kitchen_at = now
    session.add(OrderEvent(order_id=order.id, user_id=actor.id, event_type="order_sent_to_kitchen", payload={}))
    await session.flush()


async def toggle_item_ready(session: AsyncSession, order: Order, item_id: str, actor: User, toggle_enabled: bool) -> OrderItem:
    item = next((candidate for candidate in order.items if candidate.id == item_id), None)
    if item is None:
        raise ValueError("Позиция заказа не найдена")

    now = datetime.now(timezone.utc)
    new_status = next_item_status(item.status, toggle_enabled)
    item.status = new_status

    if new_status == ITEM_READY:
        item.ready_at = now
        item.ready_by = actor.id
        item.ready_seconds = int((now - order.created_at).total_seconds()) if order.created_at else None
    else:
        item.ready_at = None
        item.ready_by = None
        item.ready_seconds = None

    await _refresh_order_status(session, order, actor, now)
    session.add(OrderEvent(order_id=order.id, item_id=item.id, user_id=actor.id, event_type="item_status_changed", payload={"status": item.status}))
    await session.flush()
    return item


async def mark_all_ready(session: AsyncSession, order: Order, actor: User) -> None:
    now = datetime.now(timezone.utc)
    for item in order.items:
        if item.status != ITEM_READY:
            item.status = ITEM_READY
            item.ready_at = now
            item.ready_by = actor.id
            item.ready_seconds = int((now - order.created_at).total_seconds()) if order.created_at else None
    await _refresh_order_status(session, order, actor, now)
    session.add(OrderEvent(order_id=order.id, user_id=actor.id, event_type="order_marked_ready", payload={}))
    await session.flush()


async def cancel_order(session: AsyncSession, order: Order, actor: User) -> None:
    now = datetime.now(timezone.utc)
    order.status = ORDER_CANCELLED
    order.cancelled_at = now
    order.cancelled_by = actor.id
    session.add(OrderEvent(order_id=order.id, user_id=actor.id, event_type="order_cancelled", payload={}))
    await session.flush()


async def _refresh_order_status(session: AsyncSession, order: Order, actor: User, now: datetime) -> None:
    previous_status = order.status
    order.status = derive_order_status([item.status for item in order.items])
    if order.status == ORDER_READY:
        order.ready_at = now
        order.completed_at = now
        order.total_ready_seconds = int((now - order.created_at).total_seconds()) if order.created_at else None
    else:
        order.ready_at = None
        order.completed_at = None
        order.total_ready_seconds = None
    if previous_status != order.status:
        session.add(OrderEvent(order_id=order.id, user_id=actor.id, event_type="order_status_changed", payload={"status": order.status}))


def role_label(role: str) -> str:
    return {
        ROLE_ADMIN: "админ",
        ROLE_COOK: "повар",
        ROLE_WAITER: "официант",
    }.get(role, role)
