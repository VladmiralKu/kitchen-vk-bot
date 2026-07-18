from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.setting import Setting


MODE_STOPS = "stops"
MODE_EDIT_ORDER_NUMBER = "edit_order_number"
MODE_EDIT_ORDER_PREFIX = "edit_order:"


async def get_mode(session: AsyncSession, user_id: str) -> str | None:
    result = await session.execute(select(Setting).where(Setting.key == _mode_key(user_id)))
    setting = result.scalar_one_or_none()
    return setting.value if setting else None


async def set_mode(session: AsyncSession, user_id: str, mode: str) -> None:
    key = _mode_key(user_id)
    result = await session.execute(select(Setting).where(Setting.key == key))
    setting = result.scalar_one_or_none()
    if setting:
        setting.value = mode
    else:
        session.add(Setting(key=key, value=mode))
    await session.flush()


async def clear_mode(session: AsyncSession, user_id: str) -> None:
    result = await session.execute(select(Setting).where(Setting.key == _mode_key(user_id)))
    setting = result.scalar_one_or_none()
    if setting:
        setting.value = None
        await session.flush()


def _mode_key(user_id: str) -> str:
    return f"user_mode:{user_id}"


def edit_order_mode(order_id: str) -> str:
    return f"{MODE_EDIT_ORDER_PREFIX}{order_id}"


def edit_order_id(mode: str | None) -> str | None:
    if mode and mode.startswith(MODE_EDIT_ORDER_PREFIX):
        return mode.removeprefix(MODE_EDIT_ORDER_PREFIX)
    return None
