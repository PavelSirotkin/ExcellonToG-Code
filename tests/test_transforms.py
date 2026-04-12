"""
Тесты для модуля transforms.
"""
import pytest
import core.config as cfg
from core.transforms import (
    to_real_x,
    to_real_y,
    to_virtual_x,
    to_virtual_y,
    clamp_offset,
)


class TestToRealX:
    def test_center_x(self):
        cfg.offset_x = 0
        cfg.scale_factor = 10
        result = to_real_x(0)
        expected = cfg.WORKAREA_OFFSET_X + cfg.WORKAREA_WIDTH / 2
        assert abs(result - expected) < 1e-9

    def test_positive_virtual(self):
        cfg.offset_x = 0
        cfg.scale_factor = 10
        center = cfg.WORKAREA_OFFSET_X + cfg.WORKAREA_WIDTH / 2
        result = to_real_x(10)
        assert result == center + 100

    def test_scale_factor_1(self):
        cfg.offset_x = 0
        cfg.scale_factor = 1
        center = cfg.WORKAREA_OFFSET_X + cfg.WORKAREA_WIDTH / 2
        assert to_real_x(50) == center + 50


class TestToRealY:
    def test_center_y(self):
        cfg.offset_y = 0
        cfg.scale_factor = 10
        result = to_real_y(0)
        expected = cfg.WORKAREA_OFFSET_Y + cfg.WORKAREA_HEIGHT / 2
        assert abs(result - expected) < 1e-9

    def test_positive_virtual_inverted(self):
        cfg.offset_y = 0
        cfg.scale_factor = 10
        center = cfg.WORKAREA_OFFSET_Y + cfg.WORKAREA_HEIGHT / 2
        result = to_real_y(10)
        assert result == center - 100  # Инвертировано!


class TestToVirtualX:
    def test_inverse_of_to_real_x(self):
        cfg.offset_x = 50
        cfg.scale_factor = 15
        # to_real_x -> to_virtual_x должно вернуть исходное
        virtual = 12.345
        real = to_real_x(virtual)
        recovered = to_virtual_x(real)
        assert abs(virtual - recovered) < 1e-6


class TestToVirtualY:
    def test_inverse_of_to_real_y(self):
        cfg.offset_y = 30
        cfg.scale_factor = 20
        virtual = 25.678
        real = to_real_y(virtual)
        recovered = to_virtual_y(real)
        assert abs(virtual - recovered) < 1e-6


class TestClampOffset:
    def test_small_viewport_clamped(self):
        cfg.WORKAREA_WIDTH = 900
        cfg.WORKAREA_HEIGHT = 560
        # При маленьком масштабе viewport маленький — clamp ограничивает
        ox, oy = clamp_offset(0, 0, 1.5)
        # Допустимые пределы
        vw = cfg.WORKAREA_WIDTH / 1.5
        assert ox >= cfg.X_MIN + vw / 2 - 1e-9
        assert ox <= cfg.X_MAX - vw / 2 + 1e-9

    def test_large_viewport_not_clamped(self):
        # При большом масштабе viewport больше мира — clamp не ограничен
        ox, oy = clamp_offset(0, 0, 1000)
        assert ox == 0
        assert oy == 0

    def test_offset_within_bounds(self):
        cfg.WORKAREA_WIDTH = 900
        cfg.WORKAREA_HEIGHT = 560
        sf = 10
        vw = cfg.WORKAREA_WIDTH / sf  # 90
        min_ox = cfg.X_MIN + vw / 2   # -300 + 45 = -255
        max_ox = cfg.X_MAX - vw / 2   # 300 - 45 = 255
        ox, oy = clamp_offset(0, 0, sf)
        assert ox == 0  # 0 внутри [-255, 255]

    def test_offset_clamped_to_max(self):
        cfg.WORKAREA_WIDTH = 900
        sf = 10
        vw = cfg.WORKAREA_WIDTH / sf  # 90
        max_ox = cfg.X_MAX - vw / 2   # 255
        ox, oy = clamp_offset(500, 0, sf)
        assert abs(ox - max_ox) < 1e-9

    def test_offset_clamped_to_min(self):
        cfg.WORKAREA_WIDTH = 900
        sf = 10
        vw = cfg.WORKAREA_WIDTH / sf  # 90
        min_ox = cfg.X_MIN + vw / 2   # -255
        ox, oy = clamp_offset(-500, 0, sf)
        assert abs(ox - min_ox) < 1e-9
