from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import PlainTextResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import Settings, get_settings
from app.db import get_session
from app.models.constants import ORDER_READY, ROLE_ADMIN
from app.models.order import Order
from app.repositories import events as events_repo
from app.repositories import orders as orders_repo
from app.repositories import stops as stops_repo
from app.repositories import user_modes
from app.repositories import users as users_repo
from app.services.dispatch import broadcast_to_active_staff, notify_waiter_ready, refresh_kitchen_order_messages, send_order_to_kitchen
from app.services.excel_export import create_export_file, parse_export_period
from app.services.keyboards import confirm_order_keyboard, main_keyboard
from app.services.parser import parse_order_text, render_parsed_order
from app.services.permissions import (
    can_cancel_order,
    can_create_order,
    can_export,
    can_manage_users,
    can_mark_item_ready,
    can_use_stops,
    is_active,
)
from app.services.rendering import active_orders_list, orders_list, stops_list, users_list
from app.services.vk_client import VKClient

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/vk/callback", response_class=PlainTextResponse)
async def vk_callback(
    request: Request,
    payload: dict,
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> PlainTextResponse:
    if settings.vk_secret and payload.get("secret") != settings.vk_secret:
        raise HTTPException(status_code=403, detail="Invalid VK secret")

    event_type = payload.get("type")
    if event_type == "confirmation":
        return PlainTextResponse(settings.vk_confirmation_code)

    event_key = _event_key(payload)
    if await events_repo.event_exists(session, event_key):
        return PlainTextResponse("ok")

    vk = VKClient(settings.vk_token)
    try:
        await events_repo.record_event_once(session, event_key, f"vk_{event_type}", payload=_safe_payload(payload))
        if event_type == "message_new":
            await _handle_message_new(request, payload, session, settings, vk)
        elif event_type == "message_event":
            await _handle_message_event(request, payload, session, settings, vk)
        else:
            logger.info("Ignored VK event type: %s", event_type)
        await session.commit()
    except Exception:
        await session.rollback()
        logger.exception("Failed to process VK callback")
    return PlainTextResponse("ok")


async def _handle_message_new(request: Request, payload: dict, session: AsyncSession, settings: Settings, vk: VKClient) -> None:
    message = payload.get("object", {}).get("message", {})
    from_id = int(message.get("from_id") or 0)
    peer_id = int(message.get("peer_id") or from_id)
    text = (message.get("text") or "").strip()
    if not text or from_id <= 0:
        return

    command, args = _split_command(text)
    user = await users_repo.get_by_vk_id(session, from_id)

    if command == "/start":
        await _cmd_start(session, settings, vk, from_id, peer_id, user)
        return

    if command == "/myid":
        await vk.send_message(peer_id, f"Ваш VK ID: {from_id}")
        return

    if not is_active(user):
        await vk.send_message(peer_id, f"Доступ пока не открыт.\nВаш VK ID: {from_id}\nПередайте его администратору.")
        return

    button_action = _button_action(text)
    if button_action == "menu":
        await user_modes.clear_mode(session, user.id)
        await vk.send_message(peer_id, _menu_text(user), keyboard=main_keyboard())
    elif button_action == "orders":
        await user_modes.clear_mode(session, user.id)
        await _cmd_orders(session, settings, vk, peer_id, user)
    elif button_action == "stops":
        await _cmd_stops(session, settings, vk, peer_id, user, [], enter_mode=True)
    elif command == "/menu":
        await user_modes.clear_mode(session, user.id)
        await vk.send_message(peer_id, _menu_text(user), keyboard=main_keyboard())
    elif command == "/help":
        await vk.send_message(peer_id, _help_text(user), keyboard=main_keyboard())
    elif command == "/add":
        await user_modes.clear_mode(session, user.id)
        await _cmd_add(session, vk, peer_id, user, args)
    elif command == "/remove":
        await user_modes.clear_mode(session, user.id)
        await _cmd_remove(session, vk, peer_id, user, args)
    elif command == "/users":
        await user_modes.clear_mode(session, user.id)
        await _cmd_users(session, vk, peer_id, user)
    elif command == "/orders":
        await user_modes.clear_mode(session, user.id)
        await _cmd_orders(session, settings, vk, peer_id, user)
    elif command == "/done":
        await user_modes.clear_mode(session, user.id)
        await _cmd_done(session, settings, vk, peer_id, user)
    elif command == "/export":
        await user_modes.clear_mode(session, user.id)
        await _cmd_export(request, session, settings, vk, peer_id, user, args)
    elif command == "/stats":
        await user_modes.clear_mode(session, user.id)
        await _cmd_stats(session, settings, vk, peer_id, user, args)
    elif command in {"/stops", "/stop"}:
        await _cmd_stops(session, settings, vk, peer_id, user, args, enter_mode=True)
    elif command and command.startswith("/"):
        await vk.send_message(peer_id, "Не знаю такую команду. Напишите /menu.")
    else:
        if await user_modes.get_mode(session, user.id) == user_modes.MODE_STOPS:
            await _create_stop_from_text(session, settings, vk, peer_id, user, text)
            return
        await _handle_root_text(session, settings, vk, peer_id, user, text)


async def _handle_message_event(request: Request, payload: dict, session: AsyncSession, settings: Settings, vk: VKClient) -> None:
    obj = payload.get("object", {})
    from_id = int(obj.get("user_id") or 0)
    peer_id = int(obj.get("peer_id") or from_id)
    event_id = obj.get("event_id")
    action_payload = obj.get("payload") or {}
    action = action_payload.get("action")

    user = await users_repo.get_by_vk_id(session, from_id)
    if not is_active(user):
        await _answer_event(vk, event_id, from_id, peer_id, "Нет доступа")
        return

    if action == "show_orders":
        await user_modes.clear_mode(session, user.id)
        await _cmd_orders(session, settings, vk, peer_id, user)
    elif action == "show_done":
        await user_modes.clear_mode(session, user.id)
        await _cmd_done(session, settings, vk, peer_id, user)
    elif action == "show_stops":
        await _cmd_stops(session, settings, vk, peer_id, user, [], enter_mode=True)
    elif action == "show_users":
        await user_modes.clear_mode(session, user.id)
        await _cmd_users(session, vk, peer_id, user)
    elif action == "help_new_order":
        await vk.send_message(peer_id, "Отправьте заказ обычным текстом, например:\nСтол 4\nборщ 2\nпаста 1\nкомм: без лука")
    elif action == "export_orders":
        await _cmd_export(request, session, settings, vk, peer_id, user, [action_payload.get("period", "today")])
    elif action == "send_order_to_kitchen":
        await _event_send_order(session, settings, vk, user, action_payload)
        await _answer_event(vk, event_id, from_id, peer_id, "Отправлено на кухню")
    elif action == "toggle_item_ready":
        await _event_toggle_item(session, settings, vk, user, action_payload)
        await _answer_event(vk, event_id, from_id, peer_id, "Статус обновлён")
    elif action == "mark_order_ready":
        await _event_mark_all_ready(session, settings, vk, user, action_payload)
        await _answer_event(vk, event_id, from_id, peer_id, "Заказ готов")
    elif action == "cancel_order":
        await _event_cancel_order(session, vk, user, action_payload)
        await _answer_event(vk, event_id, from_id, peer_id, "Заказ отменён")
    else:
        await _answer_event(vk, event_id, from_id, peer_id, "Неизвестное действие")


async def _cmd_start(session: AsyncSession, settings: Settings, vk: VKClient, from_id: int, peer_id: int, user) -> None:
    if user and is_active(user):
        await user_modes.clear_mode(session, user.id)
        await vk.send_message(peer_id, _help_text(user), keyboard=main_keyboard())
        return

    if settings.superadmin_vk_id and from_id == settings.superadmin_vk_id:
        user = await users_repo.ensure_superadmin(session, from_id)
        await vk.send_message(peer_id, f"Вы подключены как первый администратор.\n\n{_help_text(user)}", keyboard=main_keyboard())
        return

    await vk.send_message(peer_id, f"Бот видит ваш VK ID: {from_id}\nПередайте его администратору для добавления.")


async def _cmd_add(session: AsyncSession, vk: VKClient, peer_id: int, actor, args: list[str]) -> None:
    if not can_manage_users(actor):
        await vk.send_message(peer_id, "Добавлять сотрудников может только админ.")
        return
    if len(args) < 2:
        await vk.send_message(peer_id, "Формат: /add <vk_id> <admin|waiter|cook> <имя>")
        return
    vk_user_id = int(args[0])
    role = args[1].lower()
    name = " ".join(args[2:]) or None
    user = await users_repo.add_or_activate_user(session, vk_user_id, role, name, actor.id)
    await vk.send_message(peer_id, f"Готово: {user.vk_user_id} добавлен как {user.role}.")


async def _cmd_remove(session: AsyncSession, vk: VKClient, peer_id: int, actor, args: list[str]) -> None:
    if not can_manage_users(actor):
        await vk.send_message(peer_id, "Удалять сотрудников может только админ.")
        return
    if not args:
        await vk.send_message(peer_id, "Формат: /remove <vk_id>")
        return
    user = await users_repo.deactivate_user(session, int(args[0]))
    await vk.send_message(peer_id, "Сотрудник деактивирован." if user else "Пользователь не найден.")


async def _cmd_users(session: AsyncSession, vk: VKClient, peer_id: int, actor) -> None:
    if not can_manage_users(actor):
        await vk.send_message(peer_id, "Список сотрудников доступен только админу.")
        return
    await vk.send_message(peer_id, users_list(await users_repo.list_users(session)))


async def _cmd_orders(session: AsyncSession, settings: Settings, vk: VKClient, peer_id: int, actor) -> None:
    orders = await orders_repo.list_active_orders(session, actor)
    await vk.send_message(peer_id, active_orders_list(orders), keyboard=main_keyboard())


async def _cmd_done(session: AsyncSession, settings: Settings, vk: VKClient, peer_id: int, actor) -> None:
    orders = await orders_repo.list_done_orders(session, actor)
    await vk.send_message(peer_id, orders_list("Выполненные заказы", orders, settings.app_timezone))


async def _cmd_export(request: Request, session: AsyncSession, settings: Settings, vk: VKClient, peer_id: int, actor, args: list[str]) -> None:
    if not can_export(actor):
        await vk.send_message(peer_id, "Excel-выгрузка доступна только админу.")
        return
    try:
        period = parse_export_period(args or ["today"], settings.app_timezone)
    except ValueError as exc:
        await vk.send_message(peer_id, str(exc))
        return
    path = await create_export_file(session, period, settings.app_timezone)
    base_url = (settings.public_base_url or str(request.base_url)).rstrip("/")
    await vk.send_message(peer_id, f"Excel готов:\n{base_url}/exports/{path.name}")


async def _cmd_stats(session: AsyncSession, settings: Settings, vk: VKClient, peer_id: int, actor, args: list[str]) -> None:
    if not can_export(actor):
        await vk.send_message(peer_id, "Статистика доступна только админу.")
        return
    period = parse_export_period(args or ["today"], settings.app_timezone)
    result = await session.execute(
        select(Order)
        .options(selectinload(Order.items))
        .where(Order.created_at >= period.start_utc, Order.created_at <= period.end_utc)
    )
    orders = list(result.scalars().unique())
    ready = [order.total_ready_seconds for order in orders if order.total_ready_seconds]
    avg_minutes = round(sum(ready) / len(ready) / 60, 1) if ready else 0
    longest = max(orders, key=lambda item: item.total_ready_seconds or 0, default=None)
    longest_text = f"#{longest.order_no}, {round((longest.total_ready_seconds or 0) / 60, 1)} мин" if longest else "-"
    await vk.send_message(peer_id, f"Заказы: {len(orders)}\nСредняя выдача: {avg_minutes} мин\nСамый долгий заказ: {longest_text}")


async def _cmd_stops(
    session: AsyncSession,
    settings: Settings,
    vk: VKClient,
    peer_id: int,
    actor,
    args: list[str],
    enter_mode: bool = False,
) -> None:
    if not can_use_stops(actor):
        await vk.send_message(peer_id, "Стоп-лист доступен только активным сотрудникам.")
        return
    text = " ".join(args).strip()
    if text:
        if enter_mode:
            await user_modes.set_mode(session, actor.id, user_modes.MODE_STOPS)
        await _create_stop_from_text(session, settings, vk, peer_id, actor, text)
        return
    if enter_mode:
        await user_modes.set_mode(session, actor.id, user_modes.MODE_STOPS)
    await vk.send_message(
        peer_id,
        _stops_mode_text(await stops_repo.list_active_stops(session), settings.app_timezone),
        keyboard=main_keyboard(),
    )


async def _create_stop_from_text(session: AsyncSession, settings: Settings, vk: VKClient, peer_id: int, actor, text: str) -> None:
    stop = await stops_repo.create_stop_message(session, actor, text, settings.stops_ttl_hours)
    author = actor.display_name or str(actor.vk_user_id)
    await broadcast_to_active_staff(session, vk, f"Стоп-лист • {author}\n{stop.text}", exclude_vk_id=actor.vk_user_id)
    await vk.send_message(
        peer_id,
        "Стоп добавлен. Можно написать следующий стоп или нажать Меню, чтобы выйти из стопов.",
        keyboard=main_keyboard(),
    )


async def _handle_root_text(session: AsyncSession, settings: Settings, vk: VKClient, peer_id: int, actor, text: str) -> None:
    parsed = parse_order_text(text)
    if parsed.has_items and can_create_order(actor):
        order = await orders_repo.create_order(session, actor, parsed, text)
        await _notify_admins_raw_order(session, vk, actor, order, text)
        if settings.auto_send_orders:
            await send_order_to_kitchen(session, vk, settings, order, actor)
            await vk.send_message(peer_id, f"Заказ #{order.order_no} отправлен на кухню.")
        else:
            await vk.send_message(peer_id, f"Проверь заказ:\n\n{render_parsed_order(parsed)}", keyboard=confirm_order_keyboard(order.id))
        return

    author = actor.display_name or str(actor.vk_user_id)
    await _notify_admins_raw_text(session, vk, actor, f"Сообщение • {author}\n{text}")
    await vk.send_message(peer_id, "Сообщение передано администраторам.", keyboard=main_keyboard())


async def _event_send_order(session: AsyncSession, settings: Settings, vk: VKClient, actor, payload: dict) -> None:
    order = await orders_repo.get_order(session, payload.get("order_id"))
    if not order:
        raise ValueError("Заказ не найден")
    if actor.id != order.waiter_id and not can_export(actor):
        raise PermissionError("Нет прав отправить заказ")
    await send_order_to_kitchen(session, vk, settings, order, actor)


async def _event_toggle_item(session: AsyncSession, settings: Settings, vk: VKClient, actor, payload: dict) -> None:
    if not can_mark_item_ready(actor):
        raise PermissionError("Нет прав менять готовность")
    order = await orders_repo.get_order(session, payload.get("order_id"))
    if not order:
        raise ValueError("Заказ не найден")
    previous_status = order.status
    await orders_repo.toggle_item_ready(session, order, payload.get("item_id"), actor, settings.toggle_item_ready)
    await refresh_kitchen_order_messages(session, vk, settings, order)
    if previous_status != ORDER_READY and order.status == ORDER_READY:
        await notify_waiter_ready(session, vk, settings, order)


async def _event_mark_all_ready(session: AsyncSession, settings: Settings, vk: VKClient, actor, payload: dict) -> None:
    if not can_mark_item_ready(actor):
        raise PermissionError("Нет прав менять готовность")
    order = await orders_repo.get_order(session, payload.get("order_id"))
    if not order:
        raise ValueError("Заказ не найден")
    previous_status = order.status
    await orders_repo.mark_all_ready(session, order, actor)
    await refresh_kitchen_order_messages(session, vk, settings, order)
    if previous_status != ORDER_READY and order.status == ORDER_READY:
        await notify_waiter_ready(session, vk, settings, order)


async def _event_cancel_order(session: AsyncSession, vk: VKClient, actor, payload: dict) -> None:
    order = await orders_repo.get_order(session, payload.get("order_id"))
    if not order:
        raise ValueError("Заказ не найден")
    own_unsent_order = actor.id == order.waiter_id and order.sent_to_kitchen_at is None
    if not can_cancel_order(actor) and not own_unsent_order:
        raise PermissionError("Отменять этот заказ может только админ")
    await orders_repo.cancel_order(session, order, actor)


async def _answer_event(vk: VKClient, event_id: str | None, user_id: int, peer_id: int, text: str) -> None:
    if event_id:
        await vk.answer_event(event_id, user_id, peer_id, text)


def _split_command(text: str) -> tuple[str | None, list[str]]:
    parts = text.split()
    if not parts or not parts[0].startswith("/"):
        return None, []
    command = parts[0].split("@", 1)[0].lower()
    return command, parts[1:]


def _menu_text(user) -> str:
    return f"Меню. Ваша роль: {user.role}.\nВыберите действие кнопками ниже."


def _help_text(user) -> str:
    return (
        f"Ваша роль: {user.role}.\n\n"
        "Как внести заказ:\n"
        "Стол 4\nборщ 2\nпаста 1\nкомм: без лука\n\n"
        "Чтобы добавить стоп, нажмите Стопы и напишите текст обычным сообщением.\n"
        "Команда /help покажет эту подсказку снова."
    )


async def _notify_admins_raw_order(session: AsyncSession, vk: VKClient, actor, order, raw_text: str) -> None:
    author = actor.display_name or str(actor.vk_user_id)
    await _notify_admins_raw_text(
        session,
        vk,
        actor,
        f"Исходный текст заказа #{order.order_no} • {author}\n{raw_text}",
    )


async def _notify_admins_raw_text(session: AsyncSession, vk: VKClient, actor, text: str) -> None:
    admins = await users_repo.list_active_by_roles(session, {ROLE_ADMIN})
    for admin in admins:
        if admin.vk_user_id == actor.vk_user_id:
            continue
        await vk.send_message(admin.vk_user_id, text)


def _button_action(text: str) -> str | None:
    normalized = text.strip().lower()
    if normalized in {"меню", "menu"}:
        return "menu"
    if normalized in {"активные", "заказы", "активные заказы", "orders"}:
        return "orders"
    if normalized in {"стопы", "стоп", "stops", "stop"}:
        return "stops"
    return None


def _stops_mode_text(stops: list, timezone_name: str) -> str:
    return (
        f"{stops_list(stops, timezone_name)}\n\n"
        "Вы в разделе Стопы. Теперь просто напишите текст стопа обычным сообщением.\n"
        "Например: нет борща до 18:00\n\n"
        "Чтобы выйти, нажмите Меню или Активные."
    )


def _event_key(payload: dict) -> str:
    obj = payload.get("object", {})
    if payload.get("event_id"):
        return f"{payload.get('type')}:{payload['event_id']}"
    if payload.get("type") == "message_event" and obj.get("event_id"):
        return f"message_event:{obj['event_id']}"
    if payload.get("type") == "message_new":
        message = obj.get("message", {})
        parts = [message.get("id"), message.get("conversation_message_id"), message.get("date"), message.get("from_id")]
        if any(parts):
            return "message_new:" + ":".join(str(part) for part in parts)
    digest = hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    return f"{payload.get('type')}:{digest}"


def _safe_payload(payload: dict) -> dict:
    value = dict(payload)
    if "secret" in value:
        value["secret"] = "***"
    return value
