from __future__ import annotations

from dataclasses import dataclass

import numpy as np


RGB = tuple[int, int, int]


def frame_average_color(frame: np.ndarray) -> RGB:
    """frame is HxWx(3|4) in BGRA or RGB order; returns (r, g, b)."""
    pixels = frame.reshape(-1, frame.shape[-1])
    mean = pixels.mean(axis=0)
    if frame.shape[-1] == 4:
        b, g, r = mean[0], mean[1], mean[2]
    else:
        r, g, b = mean[0], mean[1], mean[2]
    return (int(round(r)), int(round(g)), int(round(b)))


def frame_dominant_color(frame: np.ndarray, bins: int = 5) -> RGB:
    """Cheap dominant-color estimate via coarse histogram binning (no sklearn dependency)."""
    pixels = frame.reshape(-1, frame.shape[-1]).astype(np.float32)
    if frame.shape[-1] == 4:
        pixels = pixels[:, [2, 1, 0]]
    quantized = (pixels // (256 // bins)).astype(np.int32)
    keys = quantized[:, 0] * bins * bins + quantized[:, 1] * bins + quantized[:, 2]
    values, counts = np.unique(keys, return_counts=True)
    top_key = values[np.argmax(counts)]
    r_bin = top_key // (bins * bins)
    g_bin = (top_key // bins) % bins
    b_bin = top_key % bins
    step = 256 // bins
    r = int(r_bin * step + step // 2)
    g = int(g_bin * step + step // 2)
    b = int(b_bin * step + step // 2)
    return (r, g, b)


def luma(color: RGB) -> float:
    """Perceptual brightness of a color, 0-255."""
    r, g, b = color
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def normalize_color(color: RGB) -> RGB:
    """Scale so the brightest channel hits 255, keeping the hue but discarding overall level."""
    peak = max(color)
    if peak == 0:
        return (0, 0, 0)
    scale = 255.0 / peak
    return tuple(int(round(min(255, c * scale))) for c in color)  # type: ignore[return-value]


def apply_gamma(color: RGB, gamma: float) -> RGB:
    if gamma == 1.0:
        return color
    return tuple(int(round(255 * ((c / 255.0) ** (1.0 / gamma)))) for c in color)  # type: ignore[return-value]


def apply_brightness(color: RGB, brightness: float) -> RGB:
    brightness = max(0.0, min(1.0, brightness))
    return tuple(int(round(c * brightness)) for c in color)  # type: ignore[return-value]


def compute_output_color(color: RGB, gamma: float, brightness: float) -> RGB:
    """Gamma is applied to the hue only (kept at full strength) so dark scenes stay
    colorful instead of washing out; overall output level then follows the color's
    own perceived brightness, so a dark screen dims the light and a bright one
    doesn't - on top of the user's brightness cap."""
    screen_luminance = luma(color) / 255.0
    hue = normalize_color(color)
    vivid = apply_gamma(hue, gamma)
    return apply_brightness(vivid, brightness * screen_luminance)


def color_distance(a: RGB, b: RGB) -> int:
    return sum(abs(x - y) for x, y in zip(a, b))


@dataclass
class ColorSmoother:
    alpha: float
    _current: RGB | None = None

    def push(self, target: RGB) -> RGB:
        if self._current is None:
            self._current = target
            return target
        r = self._current[0] + self.alpha * (target[0] - self._current[0])
        g = self._current[1] + self.alpha * (target[1] - self._current[1])
        b = self._current[2] + self.alpha * (target[2] - self._current[2])
        self._current = (int(round(r)), int(round(g)), int(round(b)))
        return self._current


class ScreenCapturer:
    """Thin wrapper around mss so it can be imported without a display for unit tests."""

    def __init__(self, monitor_index: int = 1):
        import mss  # local import: mss opens a display connection on construction

        self._mss = mss.mss()
        monitors = self._mss.monitors
        if monitor_index >= len(monitors):
            raise ValueError(
                f"monitor_index {monitor_index} out of range, only {len(monitors) - 1} monitor(s) detected"
            )
        self._monitor = monitors[monitor_index]

    def grab(self) -> np.ndarray:
        shot = self._mss.grab(self._monitor)
        return np.array(shot)

    def close(self) -> None:
        self._mss.close()
