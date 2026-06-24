from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.stop_message import StopMessage
from app.models.user import User


async def create_stop_message(session: AsyncSession, author: User, text: str, ttl_hours: int) -> StopMessage:
    now = datetime.now(timezone.utc)
    stop = StopMessage(author_id=author.id, text=text, expires_at=now + timedelta(hours=ttl_hours))
    session.add(stop)
    await session.flush()
    await session.refresh(stop, attribute_names=["author"])
    return stop


async def list_active_stops(session: AsyncSession, now: datetime | None = None) -> list[StopMessage]:
    now = now or datetime.now(timezone.utc)
    result = await session.execute(
        select(StopMessage)
        .options(selectinload(StopMessage.author))
        .where(StopMessage.deleted_at.is_(None), StopMessage.expires_at > now)
        .order_by(StopMessage.created_at.desc())
    )
    return list(result.scalars())
