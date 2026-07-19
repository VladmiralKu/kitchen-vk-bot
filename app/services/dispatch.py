from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.models.constants import ROLE_ADMIN, ROLE_COOK
from app.models.vk_message import VKMessage
from app.repositories import users as users_repo
from app.repositories.orders import send_to_kitchen_mark
from app.services.keyboards import kitchen_item_chunks, kitchen_order_keyboards, obsolete_order_keyboard
from app.services.rendering import order_for_kitchen_part, ready_notification
from app.services.vk_client import VKClient

KITCHEN_MESSAGE_KIND = "kitchen_order"


async def send_order_to_kitchen(session: AsyncSession, vk: VKClient, settings: Settings, order, actor) -> None:
    if order.sent_to_kitchen_at is not None:
        return
    await send_to_kitchen_mark(session, order, actor)
    parts = _kitchen_message_parts(order, settings)

    for peer_id, user_id in await _kitchen_recipients(session, settings):
        for index, (text, keyboard) in enumerate(parts):
            result = await vk.send_message(peer_id=peer_id, message=text, keyboard=keyboard)
            session.add(
                VKMessage(
                    order_id=order.id,
                    user_id=user_id,
                    peer_id=peer_id,
                    message_id=_extract_message_id(result),
                    conversation_message_id=_extract_conversation_message_id(result),
                    message_kind=_kitchen_message_kind(index),
                )
            )


async def notify_waiter_ready(session: AsyncSession, vk: VKClient, settings: Settings, order) -> None:
    if not order.waiter:
        return
    await vk.send_message(peer_id=order.waiter.vk_user_id, message=ready_notification(order, settings.app_timezone))


async def refresh_kitchen_order_messages(session: AsyncSession, vk: VKClient, settings: Settings, order) -> None:
    result = await session.execute(
        select(VKMessage)
        .where(VKMessage.order_id == order.id, VKMessage.message_kind.like(f"{KITCHEN_MESSAGE_KIND}%"))
        .order_by(VKMessage.created_at.asc())
    )
    messages = list(result.scalars())
    if not messages:
        return

    parts = _kitchen_message_parts(order, settings)
    messages_by_peer: dict[int, list[VKMessage]] = {}
    for message in messages:
        messages_by_peer.setdefault(message.peer_id, []).append(message)

    for peer_id, peer_messages in messages_by_peer.items():
        peer_messages.sort(key=lambda message: _kitchen_message_index(message.message_kind))
        user_id = peer_messages[0].user_id if peer_messages else None
        for index, (text, keyboard) in enumerate(parts):
            message = peer_messages[index] if index < len(peer_messages) else None
            if message and (message.conversation_message_id or message.message_id):
                await vk.edit_message(
                    peer_id=message.peer_id,
                    message=text,
                    keyboard=keyboard,
                    conversation_message_id=message.conversation_message_id,
                    message_id=message.message_id,
                )
            else:
                result = await vk.send_message(peer_id, text, keyboard=keyboard)
                session.add(
                    VKMessage(
                        order_id=order.id,
                        user_id=user_id,
                        peer_id=peer_id,
                        message_id=_extract_message_id(result),
                        conversation_message_id=_extract_conversation_message_id(result),
                        message_kind=_kitchen_message_kind(index),
                    )
                )

        for message in peer_messages[len(parts):]:
            if message.conversation_message_id or message.message_id:
                await vk.edit_message(
                    peer_id=message.peer_id,
                    message=f"Заказ #{order.order_no}: этот блок больше не используется.",
                    keyboard=obsolete_order_keyboard(),
                    conversation_message_id=message.conversation_message_id,
                    message_id=message.message_id,
                )


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


def _kitchen_message_parts(order, settings: Settings) -> list[tuple[str, dict]]:
    chunks = kitchen_item_chunks(order.items)
    keyboards = kitchen_order_keyboards(order.id, order.items)
    total_parts = len(chunks)
    return [
        (order_for_kitchen_part(order, settings.app_timezone, chunk, index + 1, total_parts), keyboards[index])
        for index, chunk in enumerate(chunks)
    ]


def _kitchen_message_kind(index: int) -> str:
    return KITCHEN_MESSAGE_KIND if index == 0 else f"{KITCHEN_MESSAGE_KIND}:{index + 1}"


def _kitchen_message_index(message_kind: str) -> int:
    if message_kind == KITCHEN_MESSAGE_KIND:
        return 0
    _, _, raw_index = message_kind.partition(":")
    try:
        return max(0, int(raw_index) - 1)
    except ValueError:
        return 0


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
