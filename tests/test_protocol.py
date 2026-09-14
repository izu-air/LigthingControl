import numpy as np

from unified_lighting.color import (
    ColorSmoother,
    apply_brightness,
    apply_gamma,
    color_distance,
    frame_average_color,
    frame_dominant_color,
)
from unified_lighting.devices.rgb_strip_ble import PROTOCOLS
from unified_lighting.devices.yandex_bulb import pack_rgb


def test_pack_rgb():
    assert pack_rgb((255, 0, 0)) == 0xFF0000
    assert pack_rgb((0, 255, 0)) == 0x00FF00
    assert pack_rgb((0, 0, 255)) == 0x0000FF
    assert pack_rgb((18, 52, 86)) == 0x123456


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


def test_color_smoother_converges():
    smoother = ColorSmoother(alpha=0.5)
    first = smoother.push((100, 100, 100))
    assert first == (100, 100, 100)
    second = smoother.push((0, 0, 0))
    assert second == (50, 50, 50)
    third = smoother.push((0, 0, 0))
    assert third == (25, 25, 25)
