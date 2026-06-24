from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.constants import ACTIVE_STATUS, ALL_ROLES, DELETED_STATUS, ROLE_ADMIN
from app.models.user import User


async def get_by_vk_id(session: AsyncSession, vk_user_id: int) -> User | None:
    result = await session.execute(select(User).where(User.vk_user_id == vk_user_id))
    return result.scalar_one_or_none()


async def get_by_id(session: AsyncSession, user_id: str) -> User | None:
    result = await session.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()


async def ensure_superadmin(session: AsyncSession, vk_user_id: int) -> User:
    user = await get_by_vk_id(session, vk_user_id)
    if user:
        user.role = ROLE_ADMIN
        user.status = ACTIVE_STATUS
        await session.flush()
        return user

    user = User(vk_user_id=vk_user_id, display_name=f"Admin {vk_user_id}", role=ROLE_ADMIN, status=ACTIVE_STATUS)
    session.add(user)
    await session.flush()
    return user


async def add_or_activate_user(session: AsyncSession, vk_user_id: int, role: str, display_name: str | None, created_by: str | None) -> User:
    if role not in ALL_ROLES:
        raise ValueError("Роль должна быть admin, waiter или cook")

    user = await get_by_vk_id(session, vk_user_id)
    if user:
        user.role = role
        user.status = ACTIVE_STATUS
        if display_name:
            user.display_name = display_name
        await session.flush()
        return user

    user = User(vk_user_id=vk_user_id, display_name=display_name, role=role, status=ACTIVE_STATUS, created_by=created_by)
    session.add(user)
    await session.flush()
    return user


async def deactivate_user(session: AsyncSession, vk_user_id: int) -> User | None:
    user = await get_by_vk_id(session, vk_user_id)
    if not user:
        return None
    user.status = DELETED_STATUS
    await session.flush()
    return user


async def list_users(session: AsyncSession, include_deleted: bool = False) -> list[User]:
    query = select(User).order_by(User.role, User.display_name, User.vk_user_id)
    if not include_deleted:
        query = query.where(User.status != DELETED_STATUS)
    result = await session.execute(query)
    return list(result.scalars())


async def list_active_users(session: AsyncSession) -> list[User]:
    result = await session.execute(select(User).where(User.status == ACTIVE_STATUS).order_by(User.role, User.display_name))
    return list(result.scalars())


async def list_active_by_roles(session: AsyncSession, roles: set[str]) -> list[User]:
    result = await session.execute(select(User).where(User.status == ACTIVE_STATUS, User.role.in_(roles)).order_by(User.display_name))
    return list(result.scalars())
