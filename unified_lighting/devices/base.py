from __future__ import annotations

from abc import ABC, abstractmethod

RGB = tuple[int, int, int]


class LightDevice(ABC):
    """Common interface every controllable light implements."""

    name: str = "device"
    # Minimum seconds between two set_color calls. Cloud-bridged devices
    # (e.g. Yandex/Tuya) can reject or drop rapid-fire updates; local
    # transports like BLE can typically take one every frame.
    min_update_interval: float = 0.0

    @abstractmethod
    async def connect(self) -> None:
        ...

    @abstractmethod
    async def set_color(self, rgb: RGB) -> None:
        ...

    @abstractmethod
    async def set_power(self, on: bool) -> None:
        ...

    @abstractmethod
    async def close(self) -> None:
        ...

    async def __aenter__(self) -> "LightDevice":
        await self.connect()
        return self

    async def __aexit__(self, *exc_info: object) -> None:
        await self.close()
