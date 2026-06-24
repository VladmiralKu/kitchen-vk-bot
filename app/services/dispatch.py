from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.config import Settings
from app.models.constants import ROLE_ADMIN, ROLE_COOK
from app.models.vk_message import VKMessage
from app.repositories import users as users_repo
from app.repositories.orders import send_to_kitchen_mark
from app.services.keyboards import kitchen_order_keyboard
from app.services.rendering import order_for_kitchen, ready_notification
from app.services.vk_client import VKClient


async def send_order_to_kitchen(session: AsyncSession, vk: VKClient, settings: Settings, order, actor) -> None:
    if order.sent_to_kitchen_at is not None:
        return
    await send_to_kitchen_mark(session, order, actor)
    text = order_for_kitchen(order, settings.app_timezone)
    keyboard = kitchen_order_keyboard(order.id, order.items)

    for peer_id, user_id in await _kitchen_recipients(session, settings):
        result = await vk.send_message(peer_id=peer_id, message=text, keyboard=keyboard)
        session.add(
            VKMessage(
                order_id=order.id,
                user_id=user_id,
                peer_id=peer_id,
                message_id=_extract_message_id(result),
                conversation_message_id=_extract_conversation_message_id(result),
                message_kind="kitchen_order",
            )
        )


async def notify_waiter_ready(session: AsyncSession, vk: VKClient, settings: Settings, order) -> None:
    if not order.waiter:
        return
    await vk.send_message(peer_id=order.waiter.vk_user_id, message=ready_notification(order, settings.app_timezone))


async def refresh_kitchen_order_messages(session: AsyncSession, vk: VKClient, settings: Settings, order) -> None:
    result = await session.execute(
        select(VKMessage).where(VKMessage.order_id == order.id, VKMessage.message_kind == "kitchen_order")
    )
    messages = list(result.scalars())
    if not messages:
        return

    text = order_for_kitchen(order, settings.app_timezone)
    keyboard = kitchen_order_keyboard(order.id, order.items)
    for message in messages:
        if message.conversation_message_id or message.message_id:
            await vk.edit_message(
                peer_id=message.peer_id,
                message=text,
                keyboard=keyboard,
                conversation_message_id=message.conversation_message_id,
                message_id=message.message_id,
            )
        else:
            await vk.send_message(message.peer_id, text, keyboard=keyboard)


async def broadcast_to_active_staff(session: AsyncSession, vk: VKClient, text: str, exclude_vk_id: int | None = None) -> None:
    for user in await users_repo.list_active_users(session):
        if exclude_vk_id is not None and user.vk_user_id == exclude_vk_id:
            continue
        await vk.send_message(peer_id=user.vk_user_id, message=text)


async def _kitchen_recipients(session: AsyncSession, settings: Settings) -> list[tuple[int, str | None]]:
    if settings.kitchen_mode == "peer_chat" and settings.kitchen_peer_id:
        return [(settings.kitchen_peer_id, None)]
    staff = await users_repo.list_active_by_roles(session, {ROLE_COOK, ROLE_ADMIN})
    return [(user.vk_user_id, user.id) for user in staff]


def _extract_message_id(result: dict) -> int | None:
    response = result.get("response")
    if isinstance(response, int):
        return response
    if isinstance(response, dict):
        return response.get("message_id")
    return None


def _extract_conversation_message_id(result: dict) -> int | None:
    response = result.get("response")
    if isinstance(response, dict):
        return response.get("conversation_message_id")
    return None
