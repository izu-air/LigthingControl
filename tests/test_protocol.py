import numpy as np
import pytest

from unified_lighting.color import (
    ColorSmoother,
    apply_brightness,
    apply_gamma,
    color_distance,
    compute_output_color,
    frame_average_color,
    frame_dominant_color,
    luma,
    normalize_color,
)
from unified_lighting.devices.rgb_strip_ble import PROTOCOLS
from unified_lighting.devices.yandex_bulb import pack_rgb, rgb_to_hsv_value


def test_pack_rgb():
    assert pack_rgb((255, 0, 0)) == 0xFF0000
    assert pack_rgb((0, 255, 0)) == 0x00FF00
    assert pack_rgb((0, 0, 255)) == 0x0000FF
    assert pack_rgb((18, 52, 86)) == 0x123456


def test_rgb_to_hsv_value():
    assert rgb_to_hsv_value((255, 0, 0)) == {"h": 0, "s": 100, "v": 100}
    assert rgb_to_hsv_value((0, 255, 0)) == {"h": 120, "s": 100, "v": 100}
    assert rgb_to_hsv_value((0, 0, 255)) == {"h": 240, "s": 100, "v": 100}
    assert rgb_to_hsv_value((0, 0, 0)) == {"h": 0, "s": 0, "v": 0}
    assert rgb_to_hsv_value((255, 255, 255)) == {"h": 0, "s": 0, "v": 100}


def test_triones_color_command():
    build = PROTOCOLS["triones"].build_color_command
    assert build((255, 128, 0)) == bytes([0x56, 255, 128, 0, 0x00, 0xF0, 0xAA])


def test_happy_lighting_color_command():
    build = PROTOCOLS["happy_lighting"].build_color_command
    assert build((255, 128, 0)) == bytes([0x7E, 0x00, 0x05, 0x03, 255, 128, 0, 0x00, 0xEF])


def test_happy_lighting_power_commands():
    protocol = PROTOCOLS["happy_lighting"]
    assert protocol.power_on == bytes.fromhex("7e04040100000000ef")
    assert protocol.power_off == bytes.fromhex("7e04040000000000ef")


def test_frame_average_color_rgb():
    frame = np.zeros((4, 4, 3), dtype=np.uint8)
    frame[..., 0] = 100
    frame[..., 1] = 150
    frame[..., 2] = 200
    assert frame_average_color(frame) == (100, 150, 200)


def test_frame_average_color_bgra():
    frame = np.zeros((4, 4, 4), dtype=np.uint8)
    frame[..., 0] = 10  # B
    frame[..., 1] = 20  # G
    frame[..., 2] = 30  # R
    frame[..., 3] = 255  # A
    assert frame_average_color(frame) == (30, 20, 10)


def test_frame_dominant_color_picks_majority():
    frame = np.zeros((10, 10, 3), dtype=np.uint8)
    frame[:, :, :] = (255, 0, 0)
    frame[0:2, 0:2] = (0, 255, 0)
    r, g, b = frame_dominant_color(frame, bins=5)
    assert r > g and r > b


def test_apply_gamma_identity():
    assert apply_gamma((10, 20, 30), 1.0) == (10, 20, 30)


def test_apply_gamma_brightens_midtones():
    r, _, _ = apply_gamma((128, 128, 128), 2.2)
    assert r > 128


def test_apply_brightness_clamps():
    assert apply_brightness((200, 200, 200), 0.5) == (100, 100, 100)
    assert apply_brightness((200, 200, 200), 1.5) == (200, 200, 200)
    assert apply_brightness((200, 200, 200), -1.0) == (0, 0, 0)


def test_color_distance():
    assert color_distance((0, 0, 0), (10, 10, 10)) == 30
    assert color_distance((5, 5, 5), (5, 5, 5)) == 0


def test_luma_orders_perceived_brightness():
    assert luma((255, 255, 255)) == pytest.approx(255)
    assert luma((0, 0, 0)) == 0
    # green reads brighter than blue at equal channel value (perceptual weights)
    assert luma((0, 200, 0)) > luma((0, 0, 200))


def test_normalize_color_preserves_hue_and_maxes_out():
    r, g, b = normalize_color((100, 50, 25))
    assert r == 255
    assert g == pytest.approx(128, abs=1)
    assert b == pytest.approx(64, abs=1)
    assert normalize_color((0, 0, 0)) == (0, 0, 0)
    assert normalize_color((255, 255, 255)) == (255, 255, 255)


def test_compute_output_color_dims_for_dark_screen():
    dark = compute_output_color((10, 10, 10), gamma=2.2, brightness=1.0)
    bright = compute_output_color((240, 240, 240), gamma=2.2, brightness=1.0)
    assert sum(dark) < sum(bright)
    assert sum(dark) < 60  # a near-black screen should not come out looking lit up


def test_compute_output_color_respects_brightness_cap():
    full = compute_output_color((200, 100, 50), gamma=2.2, brightness=1.0)
    half = compute_output_color((200, 100, 50), gamma=2.2, brightness=0.5)
    assert sum(half) < sum(full)


def test_compute_output_color_black_stays_black():
    assert compute_output_color((0, 0, 0), gamma=2.2, brightness=1.0) == (0, 0, 0)


def test_color_smoother_converges():
    smoother = ColorSmoother(alpha=0.5)
    first = smoother.push((100, 100, 100))
    assert first == (100, 100, 100)
    second = smoother.push((0, 0, 0))
    assert second == (50, 50, 50)
    third = smoother.push((0, 0, 0))
    assert third == (25, 25, 25)
