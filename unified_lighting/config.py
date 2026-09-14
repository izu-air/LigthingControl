from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml


class ConfigError(Exception):
    pass


@dataclass
class YandexConfig:
    enabled: bool = True
    oauth_token: str = ""
    device_id: str = ""

    def validate(self) -> None:
        if not self.enabled:
            return
        if not self.oauth_token:
            raise ConfigError("yandex.oauth_token is not set (see README for how to obtain it)")
        if not self.device_id:
            raise ConfigError("yandex.device_id is not set (see README: GET /v1.0/user/info)")


@dataclass
class BleStripConfig:
    enabled: bool = True
    mac_address: str = ""
    protocol: str = "triones"
    write_characteristic_uuid: str = "0000ffd9-0000-1000-8000-00805f9b34fb"
    connect_timeout: float = 10.0

    def validate(self) -> None:
        if not self.enabled:
            return
        if not self.mac_address:
            raise ConfigError("rgb_strip.mac_address is not set (scan for it, see README)")
        if self.protocol not in ("triones", "happy_lighting"):
            raise ConfigError(f"rgb_strip.protocol: unknown value '{self.protocol}'")


@dataclass
class SyncConfig:
    mode: str = "screen"
    fps: float = 15.0
    color_algorithm: str = "average"
    brightness: float = 1.0
    gamma: float = 2.2
    smoothing: float = 0.3
    min_change_threshold: int = 4
    monitor_index: int = 1

    def validate(self) -> None:
        if self.mode not in ("screen", "static", "off"):
            raise ConfigError(f"sync.mode: unknown value '{self.mode}'")
        if self.color_algorithm not in ("average", "dominant"):
            raise ConfigError(f"sync.color_algorithm: unknown value '{self.color_algorithm}'")
        if not (0.0 <= self.brightness <= 1.0):
            raise ConfigError("sync.brightness must be between 0.0 and 1.0")
        if not (0.0 <= self.smoothing <= 1.0):
            raise ConfigError("sync.smoothing must be between 0.0 and 1.0")
        if self.fps <= 0:
            raise ConfigError("sync.fps must be positive")


@dataclass
class AppConfig:
    yandex: YandexConfig = field(default_factory=YandexConfig)
    rgb_strip: BleStripConfig = field(default_factory=BleStripConfig)
    sync: SyncConfig = field(default_factory=SyncConfig)

    def validate(self) -> None:
        self.yandex.validate()
        self.rgb_strip.validate()
        self.sync.validate()
        if not self.yandex.enabled and not self.rgb_strip.enabled:
            raise ConfigError("both yandex and rgb_strip are disabled, nothing to control")


def load_config(path: str | Path) -> AppConfig:
    path = Path(path)
    if not path.exists():
        raise ConfigError(
            f"config file not found: {path}. Copy config.example.yaml to config.yaml and fill it in."
        )
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}

    yandex_raw = raw.get("yandex") or {}
    rgb_raw = raw.get("rgb_strip") or {}
    sync_raw = raw.get("sync") or {}

    config = AppConfig(
        yandex=YandexConfig(**yandex_raw),
        rgb_strip=BleStripConfig(**rgb_raw),
        sync=SyncConfig(**sync_raw),
    )
    config.validate()
    return config
