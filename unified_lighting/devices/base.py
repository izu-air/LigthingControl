from __future__ import annotations

from abc import ABC, abstractmethod

RGB = tuple[int, int, int]


class LightDevice(ABC):
    """Common interface every controllable light implements."""

    name: str = "device"

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
