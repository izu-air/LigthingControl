from __future__ import annotations

import asyncio
import logging

from .color import (
    ColorSmoother,
    ScreenCapturer,
    apply_brightness,
    apply_gamma,
    color_distance,
    frame_average_color,
    frame_dominant_color,
)
from .config import AppConfig
from .devices.base import RGB, LightDevice
from .devices.rgb_strip_ble import BleRgbStrip
from .devices.yandex_bulb import YandexBulb

logger = logging.getLogger(__name__)

# Every Nth pixel is sampled in each dimension before computing a color from
# a frame. A full 4K frame is ~8M pixels; sampling every 8th cuts that to
# ~130K with no visible difference in the resulting average/dominant color.
SCREEN_DOWNSAMPLE = 8


def build_devices(config: AppConfig) -> list[LightDevice]:
    devices: list[LightDevice] = []
    if config.yandex.enabled:
        devices.append(YandexBulb(config.yandex.oauth_token, config.yandex.device_id))
    if config.rgb_strip.enabled:
        devices.append(
            BleRgbStrip(
                config.rgb_strip.mac_address,
                config.rgb_strip.write_characteristic_uuid,
                protocol=config.rgb_strip.protocol,
                connect_timeout=config.rgb_strip.connect_timeout,
            )
        )
    return devices


async def connect_all(devices: list[LightDevice]) -> None:
    results = await asyncio.gather(*(d.connect() for d in devices), return_exceptions=True)
    for device, result in zip(devices, results):
        if isinstance(result, Exception):
            logger.error("Failed to connect %s: %s", device.name, result)


async def close_all(devices: list[LightDevice]) -> None:
    await asyncio.gather(*(d.close() for d in devices), return_exceptions=True)


async def set_color_all(devices: list[LightDevice], rgb: RGB) -> None:
    results = await asyncio.gather(*(d.set_color(rgb) for d in devices), return_exceptions=True)
    for device, result in zip(devices, results):
        if isinstance(result, Exception):
            logger.warning("set_color failed on %s: %s", device.name, result)


async def set_power_all(devices: list[LightDevice], on: bool) -> None:
    results = await asyncio.gather(*(d.set_power(on) for d in devices), return_exceptions=True)
    for device, result in zip(devices, results):
        if isinstance(result, Exception):
            logger.warning("set_power failed on %s: %s", device.name, result)


async def _send_to_device(device: LightDevice, rgb: RGB) -> None:
    try:
        await device.set_color(rgb)
    except Exception as exc:  # noqa: BLE001 - device errors must not kill the sync loop
        logger.warning("set_color failed on %s: %s", device.name, exc)


def select_due_devices(
    devices: list[LightDevice],
    final_color: RGB,
    last_sent_color: dict[LightDevice, RGB],
    last_sent_time: dict[LightDevice, float],
    now: float,
    min_change_threshold: int,
) -> list[LightDevice]:
    return [
        device
        for device in devices
        if now - last_sent_time.get(device, float("-inf")) >= device.min_update_interval
        and color_distance(final_color, last_sent_color.get(device, (-999, -999, -999))) >= min_change_threshold
    ]


async def run_screen_sync(config: AppConfig, devices: list[LightDevice], stop_event: asyncio.Event) -> None:
    capturer = ScreenCapturer(monitor_index=config.sync.monitor_index)
    smoother = ColorSmoother(alpha=config.sync.smoothing)
    period = 1.0 / config.sync.fps
    last_sent_color: dict[LightDevice, RGB] = {}
    last_sent_time: dict[LightDevice, float] = {}
    loop = asyncio.get_running_loop()

    try:
        while not stop_event.is_set():
            tick_start = loop.time()

            try:
                frame = await loop.run_in_executor(None, capturer.grab)
                frame = frame[::SCREEN_DOWNSAMPLE, ::SCREEN_DOWNSAMPLE]
                if config.sync.color_algorithm == "dominant":
                    raw_color = frame_dominant_color(frame)
                else:
                    raw_color = frame_average_color(frame)
            except Exception:
                logger.exception("Screen capture failed, skipping this tick")
                await asyncio.sleep(period)
                continue

            smoothed = smoother.push(raw_color)
            final_color = apply_brightness(apply_gamma(smoothed, config.sync.gamma), config.sync.brightness)

            due_devices = select_due_devices(
                devices, final_color, last_sent_color, last_sent_time, tick_start, config.sync.min_change_threshold
            )
            if due_devices:
                logger.debug(
                    "screen avg=%s -> sending %s to %s", raw_color, final_color, [d.name for d in due_devices]
                )
                await asyncio.gather(*(_send_to_device(d, final_color) for d in due_devices))
                for device in due_devices:
                    last_sent_color[device] = final_color
                    last_sent_time[device] = tick_start

            elapsed = loop.time() - tick_start
            await asyncio.sleep(max(0.0, period - elapsed))
    finally:
        capturer.close()
