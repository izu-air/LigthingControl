from __future__ import annotations

import colorsys
import logging

import httpx

from .base import RGB, LightDevice

logger = logging.getLogger(__name__)

API_BASE = "https://api.iot.yandex.net/v1.0"


def pack_rgb(rgb: RGB) -> int:
    r, g, b = rgb
    return (r << 16) | (g << 8) | b


def rgb_to_hsv_value(rgb: RGB) -> dict:
    r, g, b = rgb
    h, s, v = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
    return {"h": round(h * 360), "s": round(s * 100), "v": round(v * 100)}


class YandexBulb(LightDevice):
    """Controls a device exposed through the Yandex Smart Home (IoT) API.

    Requires an OAuth token scoped for smart-home device control and the
    device_id as returned by GET {API_BASE}/user/info. See README.md for
    how to obtain both.
    """

    name = "yandex_bulb"
    # Many bulbs sold as "Yandex-compatible" are actually bridged through
    # Tuya's cloud; that bridge starts returning 501/INTERNAL_ERROR under
    # ambilight's frame rate, so this device gets updated far less often
    # than a directly-connected one like the BLE strip.
    min_update_interval = 1.5

    def __init__(self, oauth_token: str, device_id: str, timeout: float = 10.0):
        self._device_id = device_id
        self._client = httpx.AsyncClient(
            base_url=API_BASE,
            headers={"Authorization": f"Bearer {oauth_token}"},
            timeout=timeout,
        )
        self._color_model: str | None = None

    async def connect(self) -> None:
        response = await self._client.get(f"/devices/{self._device_id}")
        response.raise_for_status()
        for capability in response.json().get("capabilities", []):
            if capability.get("type") == "devices.capabilities.color_setting":
                self._color_model = capability.get("parameters", {}).get("color_model")
        if self._color_model is None:
            logger.info("Device %s has no color_setting capability; set_color will be a no-op", self._device_id)

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
        if self._color_model is None:
            await self.connect()
        if self._color_model == "rgb":
            value = pack_rgb(rgb)
            instance = "rgb"
        elif self._color_model == "hsv":
            value = rgb_to_hsv_value(rgb)
            instance = "hsv"
        else:
            logger.warning("Device %s does not support color_setting, skipping set_color", self._device_id)
            return
        await self._send_actions(
            [{"type": "devices.capabilities.color_setting", "state": {"instance": instance, "value": value}}]
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
