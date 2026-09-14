from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import Callable

from bleak import BleakClient

from .base import RGB, LightDevice

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class BleProtocol:
    power_on: bytes
    power_off: bytes
    build_color_command: Callable[[RGB], bytes]


def _triones_color(rgb: RGB) -> bytes:
    r, g, b = rgb
    return bytes([0x56, r, g, b, 0x00, 0xF0, 0xAA])


def _happy_lighting_color(rgb: RGB) -> bytes:
    r, g, b = rgb
    return bytes([0x7E, 0x00, 0x05, 0x03, r, g, b, 0x00, 0xEF])


PROTOCOLS: dict[str, BleProtocol] = {
    # Common on FFD5/FFD9 GATT layout controllers (also sold as "Magic Blue").
    "triones": BleProtocol(
        power_on=bytes.fromhex("cc2333"),
        power_off=bytes.fromhex("cc2433"),
        build_color_command=_triones_color,
    ),
    # Common on FFF0/FFF3/FFF4 GATT layout controllers.
    "happy_lighting": BleProtocol(
        power_on=bytes.fromhex("7e04040100000000ef"),
        power_off=bytes.fromhex("7e04040000000000ef"),
        build_color_command=_happy_lighting_color,
    ),
}


class BleRgbStrip(LightDevice):
    name = "rgb_strip"

    def __init__(
        self,
        mac_address: str,
        write_characteristic_uuid: str,
        protocol: str = "triones",
        connect_timeout: float = 10.0,
    ):
        if protocol not in PROTOCOLS:
            raise NotImplementedError(
                f"protocol '{protocol}' is not implemented; choose one of {sorted(PROTOCOLS)}"
            )
        self._protocol = PROTOCOLS[protocol]
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
        await self._write(self._protocol.build_color_command(rgb))

    async def set_power(self, on: bool) -> None:
        await self._write(self._protocol.power_on if on else self._protocol.power_off)

    async def close(self) -> None:
        if self._client is not None and self._client.is_connected:
            await self._client.disconnect()
