from __future__ import annotations

import json
import logging
import secrets
from typing import Any

import httpx

logger = logging.getLogger(__name__)


class VKClient:
    API_URL = "https://api.vk.com/method"
    API_VERSION = "5.199"

    def __init__(self, token: str):
        self.token = token

    async def send_message(self, peer_id: int, message: str, keyboard: dict | None = None, attachment: str | None = None) -> dict[str, Any]:
        params: dict[str, Any] = {
            "peer_id": peer_id,
            "message": message,
            "random_id": secrets.randbelow(2_147_483_647),
        }
        if keyboard:
            params["keyboard"] = json.dumps(keyboard, ensure_ascii=False)
        if attachment:
            params["attachment"] = attachment
        return await self._method("messages.send", params)

    async def edit_message(
        self,
        peer_id: int,
        message: str,
        keyboard: dict | None = None,
        conversation_message_id: int | None = None,
        message_id: int | None = None,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {
            "peer_id": peer_id,
            "message": message,
        }
        if conversation_message_id:
            params["conversation_message_id"] = conversation_message_id
        elif message_id:
            params["message_id"] = message_id
        else:
            raise ValueError("conversation_message_id or message_id is required")
        if keyboard:
            params["keyboard"] = json.dumps(keyboard, ensure_ascii=False)
        return await self._method("messages.edit", params)

    async def answer_event(self, event_id: str, user_id: int, peer_id: int, text: str) -> dict[str, Any]:
        return await self._method(
            "messages.sendMessageEventAnswer",
            {
                "event_id": event_id,
                "user_id": user_id,
                "peer_id": peer_id,
                "event_data": json.dumps({"type": "show_snackbar", "text": text}, ensure_ascii=False),
            },
        )

    async def _method(self, name: str, params: dict[str, Any]) -> dict[str, Any]:
        if not self.token:
            logger.warning("VK_TOKEN is empty; skipped VK API call %s", name)
            return {"skipped": True, "method": name}

        payload = {"access_token": self.token, "v": self.API_VERSION, **params}
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.post(f"{self.API_URL}/{name}", data=payload)
            response.raise_for_status()
            data = response.json()

        if "error" in data:
            logger.warning("VK API error in %s: %s", name, data["error"])
        return data
