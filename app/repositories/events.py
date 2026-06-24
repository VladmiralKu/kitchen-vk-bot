from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.order_event import OrderEvent


async def event_exists(session: AsyncSession, vk_event_id: str) -> bool:
    result = await session.execute(select(OrderEvent.id).where(OrderEvent.vk_event_id == vk_event_id))
    return result.scalar_one_or_none() is not None


async def record_event_once(
    session: AsyncSession,
    vk_event_id: str | None,
    event_type: str,
    payload: dict | None = None,
    order_id: str | None = None,
    item_id: str | None = None,
    user_id: str | None = None,
) -> OrderEvent | None:
    if vk_event_id and await event_exists(session, vk_event_id):
        return None
    event = OrderEvent(
        vk_event_id=vk_event_id,
        event_type=event_type,
        payload=payload,
        order_id=order_id,
        item_id=item_id,
        user_id=user_id,
    )
    session.add(event)
    await session.flush()
    return event
