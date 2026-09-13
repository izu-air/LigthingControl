from __future__ import annotations

import asyncio
import logging

from bleak import BleakClient

from .base import RGB, LightDevice

logger = logging.getLogger(__name__)

# "Triones"-family protocol used by most generic white-label BLE RGB
# controllers (the chipset behind many rebranded apps such as
# "Happy Lighting", "LED BLE", "Magic Blue" and, most likely, "Lotus
# Lantern"). If your strip does not respond, capture the real bytes with
# an Android "Bluetooth HCI snoop log" + Wireshark while using the Lotus
# Lantern app, then adjust the constants below or switch protocol to
# "raw_hex" in config.yaml and supply your own templates. See README.md.
POWER_ON = bytes.fromhex("cc2333")
POWER_OFF = bytes.fromhex("cc2433")


def build_color_command(rgb: RGB) -> bytes:
    r, g, b = rgb
    return bytes([0x56, r, g, b, 0x00, 0xF0, 0xAA])


class BleRgbStrip(LightDevice):
    name = "rgb_strip"

    def __init__(
        self,
        mac_address: str,
        write_characteristic_uuid: str,
        protocol: str = "triones",
        connect_timeout: float = 10.0,
    ):
        if protocol != "triones":
            raise NotImplementedError(
                f"protocol '{protocol}' is not implemented yet; use 'triones' or extend this class"
            )
        self._mac_address = mac_address
        self._char_uuid = write_characteristic_uuid
        self._timeout = connect_timeout
        self._client: BleakClient | None = None
        self._lock = asyncio.Lock()

    async def connect(self) -> None:
        self._client = BleakClient(self._mac_address, timeout=self._timeout)
        await self._client.connect()
        logger.info("Connected to BLE RGB strip at %s", self._mac_address)

    async def _write(self, payload: bytes) -> None:
        if self._client is None or not self._client.is_connected:
            await self.connect()
        assert self._client is not None
        async with self._lock:
            await self._client.write_gatt_char(self._char_uuid, payload, response=False)

    async def set_color(self, rgb: RGB) -> None:
        await self._write(build_color_command(rgb))

    async def set_power(self, on: bool) -> None:
        await self._write(POWER_ON if on else POWER_OFF)

    async def close(self) -> None:
        if self._client is not None and self._client.is_connected:
            await self._client.disconnect()
