from __future__ import annotations

import logging

import httpx

from .base import RGB, LightDevice

logger = logging.getLogger(__name__)

API_BASE = "https://api.iot.yandex.net/v1.0"


def pack_rgb(rgb: RGB) -> int:
    r, g, b = rgb
    return (r << 16) | (g << 8) | b


class YandexBulb(LightDevice):
    """Controls a device exposed through the Yandex Smart Home (IoT) API.

    Requires an OAuth token scoped for smart-home device control and the
    device_id as returned by GET {API_BASE}/user/info. See README.md for
    how to obtain both.
    """

    name = "yandex_bulb"

    def __init__(self, oauth_token: str, device_id: str, timeout: float = 10.0):
        self._device_id = device_id
        self._client = httpx.AsyncClient(
            base_url=API_BASE,
            headers={"Authorization": f"Bearer {oauth_token}"},
            timeout=timeout,
        )

    async def connect(self) -> None:
        response = await self._client.get(f"/devices/{self._device_id}")
        response.raise_for_status()

    async def _send_actions(self, actions: list[dict]) -> None:
        payload = {"devices": [{"id": self._device_id, "actions": actions}]}
        response = await self._client.post("/devices/actions", json=payload)
        if response.status_code >= 400:
            logger.error("Yandex API error %s: %s", response.status_code, response.text)
        response.raise_for_status()
        body = response.json()
        for device in body.get("devices", []):
            for capability in device.get("capabilities", []):
                state = capability.get("state", {})
                if state.get("action_result", {}).get("status") == "ERROR":
                    logger.warning("Yandex API rejected action: %s", state)

    async def set_color(self, rgb: RGB) -> None:
        await self._send_actions(
            [
                {
                    "type": "devices.capabilities.color_setting",
                    "state": {"instance": "rgb", "value": pack_rgb(rgb)},
                }
            ]
        )

    async def set_brightness(self, brightness: float) -> None:
        await self._send_actions(
            [
                {
                    "type": "devices.capabilities.range",
                    "state": {"instance": "brightness", "value": round(brightness * 100)},
                }
            ]
        )

    async def set_power(self, on: bool) -> None:
        await self._send_actions(
            [{"type": "devices.capabilities.on_off", "state": {"instance": "on", "value": on}}]
        )

    async def close(self) -> None:
        await self._client.aclose()
