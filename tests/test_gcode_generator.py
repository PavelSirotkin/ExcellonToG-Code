"""
Тесты для модуля gcode_generator.
"""
import pytest
from core.gcode_generator import (
    validate_gcode_params,
    write_tool_parking,
    write_tool_start,
    _build_drilling_gcode,
    _build_milling_gcode,
    _build_combined_gcode,
    _calc_multipass_offsets,
)
import io


class TestValidateGcodeParams:
    def test_valid_params(self):
        errors = validate_gcode_params(5.0, -2.5, 100, 500, 30)
        assert errors == []

    def test_negative_safe_z(self):
        errors = validate_gcode_params(-5.0, -2.5, 100, 500, 30)
        assert len(errors) > 0
        assert any("Безопасная Z" in e for e in errors)

    def test_positive_drill_z(self):
        errors = validate_gcode_params(5.0, 2.5, 100, 500, 30)
        assert len(errors) > 0
        assert any("Глубина сверления" in e for e in errors)

    def test_zero_feed_rate(self):
        errors = validate_gcode_params(5.0, -2.5, 0, 500, 30)
        assert len(errors) > 0
        assert any("Подача" in e for e in errors)

    def test_park_below_safe_z(self):
        errors = validate_gcode_params(10.0, -2.5, 100, 500, 2)
        assert len(errors) > 0
        assert any("Парковка Z" in e for e in errors)

    def test_mill_feed_validation(self):
        errors = validate_gcode_params(5.0, -2.5, 100, 500, 30, mill_feed=-10)
        assert len(errors) > 0
        assert any("Подача фрезы" in e for e in errors)

    def test_mill_feed_zero(self):
        errors = validate_gcode_params(5.0, -2.5, 100, 500, 30, mill_feed=0)
        assert len(errors) > 0

    def test_mill_feed_valid(self):
        errors = validate_gcode_params(5.0, -2.5, 100, 500, 30, mill_feed=50)
        assert errors == []


class TestBuildDrillingGcode:
    def test_build_valid(self):
        tools = {
            '1': {'diameter': 1.0, 'holes': [(0, 0), (10, 10)], 'visible': True},
        }
        params = {
            'safe_z': 5.0, 'drill_z': -2.5, 'feed_rate': 100,
            'rapid_rate': 500, 'park_z': 30,
        }
        gcode, errors = _build_drilling_gcode(tools, "test.drl", params)
        assert errors == []
        assert gcode is not None
        assert "M03" in gcode
        assert "M30" in gcode

    def test_build_no_tools(self):
        params = {
            'safe_z': 5.0, 'drill_z': -2.5, 'feed_rate': 100,
            'rapid_rate': 500, 'park_z': 30,
        }
        gcode, errors = _build_drilling_gcode(None, None, params)
        assert gcode is None
        assert len(errors) > 0

    def test_build_no_visible_tools(self):
        tools = {
            '1': {'diameter': 1.0, 'holes': [(0, 0)], 'visible': False},
        }
        params = {
            'safe_z': 5.0, 'drill_z': -2.5, 'feed_rate': 100,
            'rapid_rate': 500, 'park_z': 30,
        }
        gcode, errors = _build_drilling_gcode(tools, "test.drl", params)
        assert gcode is None
        assert any("видим" in e.lower() for e in errors)


class TestBuildMillingGcode:
    def test_build_valid(self):
        tools = {
            '1': {'diameter': 2.0, 'slots': [((0, 0), (10, 10))], 'visible': True},
        }
        params = {
            'safe_z': 5.0, 'drill_z': -2.5, 'feed_rate': 100,
            'mill_feed': 50, 'rapid_rate': 500, 'park_z': 30,
        }
        gcode, errors = _build_milling_gcode(tools, "slots.drl", params)
        assert errors == []
        assert gcode is not None
        assert "Milling feed: 50" in gcode

    def test_build_no_tools(self):
        params = {
            'safe_z': 5.0, 'drill_z': -2.5, 'feed_rate': 100,
            'mill_feed': 50, 'rapid_rate': 500, 'park_z': 30,
        }
        gcode, errors = _build_milling_gcode(None, None, params)
        assert gcode is None
        assert len(errors) > 0


class TestBuildCombinedGcode:
    def test_build_drilling_only(self):
        drilling = {
            '1': {'diameter': 1.0, 'holes': [(0, 0)], 'visible': True},
        }
        params = {
            'safe_z': 5.0, 'drill_z': -2.5, 'feed_rate': 100,
            'mill_feed': 50, 'rapid_rate': 500, 'park_z': 30,
        }
        gcode, errors = _build_combined_gcode(drilling, "holes.drl", None, None, params)
        assert errors == []
        assert gcode is not None
        assert "DRILLING SECTION" in gcode

    def test_build_milling_only(self):
        milling = {
            '1': {'diameter': 2.0, 'slots': [((0, 0), (10, 10))], 'visible': True},
        }
        params = {
            'safe_z': 5.0, 'drill_z': -2.5, 'feed_rate': 100,
            'mill_feed': 50, 'rapid_rate': 500, 'park_z': 30,
        }
        gcode, errors = _build_combined_gcode(None, None, milling, "slots.drl", params)
        assert errors == []
        assert "SLOT MILLING SECTION" in gcode

    def test_build_no_data(self):
        params = {
            'safe_z': 5.0, 'drill_z': -2.5, 'feed_rate': 100,
            'mill_feed': 50, 'rapid_rate': 500, 'park_z': 30,
        }
        gcode, errors = _build_combined_gcode(None, None, None, None, params)
        assert gcode is None
        assert len(errors) > 0

    def test_build_all_hidden(self):
        drilling = {
            '1': {'diameter': 1.0, 'holes': [(0, 0)], 'visible': False},
        }
        milling = {
            '1': {'diameter': 2.0, 'slots': [((0, 0), (10, 10))], 'visible': False},
        }
        params = {
            'safe_z': 5.0, 'drill_z': -2.5, 'feed_rate': 100,
            'mill_feed': 50, 'rapid_rate': 500, 'park_z': 30,
        }
        gcode, errors = _build_combined_gcode(drilling, "h.drl", milling, "s.drl", params)
        assert gcode is None
        assert any("видим" in e.lower() for e in errors)

    def test_build_combined(self):
        drilling = {
            '1': {'diameter': 1.0, 'holes': [(0, 0)], 'visible': True},
        }
        milling = {
            '1': {'diameter': 2.0, 'slots': [((0, 0), (10, 10))], 'visible': True},
        }
        params = {
            'safe_z': 5.0, 'drill_z': -2.5, 'feed_rate': 100,
            'mill_feed': 50, 'rapid_rate': 500, 'park_z': 30,
        }
        gcode, errors = _build_combined_gcode(drilling, "h.drl", milling, "s.drl", params)
        assert errors == []
        assert "DRILLING SECTION" in gcode
        assert "SLOT MILLING SECTION" in gcode


class TestWriteToolParking:
    def test_parking_output(self):
        buf = io.StringIO()
        write_tool_parking(buf, park_z=30.0, rapid_rate=500)
        output = buf.getvalue()
        assert "M05" in output
        assert "G00 Z30.00" in output
        assert "G00 X0 Y0" in output


class TestWriteToolStart:
    def test_tool_start_output(self):
        buf = io.StringIO()
        write_tool_start(buf, tool=1, diameter=1.5, count=10, unit="holes",
                         safe_z=5.0, rapid_rate=500)
        output = buf.getvalue()
        assert "T1" in output
        assert "D=1.50mm" in output
        assert "M00" in output
        assert "M03" in output
        assert "G00 Z5.00" in output

    def test_slots_unit(self):
        buf = io.StringIO()
        write_tool_start(buf, tool=2, diameter=2.0, count=5, unit="slots",
                         safe_z=10.0, rapid_rate=600)
        output = buf.getvalue()
        assert "slots" in output
        assert "D=2.00mm" in output


class TestCalcMultipassOffsets:
    def test_symmetric_center_first(self):
        # W=3, d=1, stepover=50% → step=0.5 → offsets: 0, +0.5, -0.5, +1.0, -1.0
        offsets = _calc_multipass_offsets(3.0, 1.0, 50)
        assert 0.0 in offsets
        assert len(offsets) == 5
        # симметричность: для каждого положительного есть отрицательное
        positives = sorted(o for o in offsets if o > 1e-9)
        negatives = sorted(abs(o) for o in offsets if o < -1e-9)
        assert positives == negatives

    def test_covers_full_width(self):
        # крайние проходы должны доходить до стенок слота
        slot_w, tool_d = 3.0, 1.0
        offsets = _calc_multipass_offsets(slot_w, tool_d, 50)
        max_offset = max(abs(o) for o in offsets)
        # крайний проход: центр на max_offset, край инструмента на max_offset + d/2 <= W/2
        assert max_offset + tool_d / 2 <= slot_w / 2 + 1e-9

    def test_single_pass_when_tool_fits(self):
        # фреза = ширина слота → один центральный проход
        offsets = _calc_multipass_offsets(2.0, 2.0, 50)
        assert offsets == [0.0]

    def test_stepover_zero_uses_fifty_percent(self):
        offsets_zero = _calc_multipass_offsets(3.0, 1.0, 0)
        offsets_fifty = _calc_multipass_offsets(3.0, 1.0, 50)
        assert offsets_zero == offsets_fifty

    def test_wall_touch_passes_added_when_stepover_too_large(self):
        # slot=1.0мм, tool=0.8мм: stepover-шаг (0.4) больше допустимого смещения (0.1)
        # → граничные проходы ±0.1 должны добавиться явно
        offsets = _calc_multipass_offsets(1.0, 0.8, 50)
        assert len(offsets) == 3
        assert 0.0 in offsets
        assert any(abs(o - 0.1) < 1e-9 for o in offsets)
        assert any(abs(o + 0.1) < 1e-9 for o in offsets)
        # Граничный проход касается стенки: 0.1 + 0.4 = 0.5 = slot_width/2
        max_offset = max(abs(o) for o in offsets)
        assert abs(max_offset + 0.8 / 2 - 1.0 / 2) < 1e-9

    def test_multipass_gcode_zigzag(self):
        # При multi_pass=True зигзаг: одно погружение и один подъём на весь слот
        slot_tools = {1: {'diameter': 3.0, 'slots': [((0.0, 0.0), (10.0, 0.0))],
                          'visible': True, 'var': None}}
        params = {'safe_z': 5.0, 'drill_z': -2.0, 'feed_rate': 100,
                  'mill_feed': 50, 'rapid_rate': 500, 'park_z': 30}
        t_params = {1: {'spindle_speed': 0, 'feed_rate': 100, 'mill_feed': 50,
                        'rapid_rate': 500, 'safe_z': 5.0, 'drill_z': -2.0,
                        'park_z': 30, 'multi_pass': True,
                        'slot_width': 3.0, 'diameter': 1.0, 'stepover': 50}}
        gcode, errors = _build_milling_gcode(slot_tools, "test.drl", params, t_params)
        assert errors == []
        # Зигзаг: только одно погружение на весь слот
        assert gcode.count("G01 Z-2.00") == 1
        # Только один подъём после слота (второй G00 Z5.00 — в write_tool_start)
        retract_lines = [l for l in gcode.splitlines() if "G00 Z5.00" in l]
        # write_tool_start даёт один G00 Z5.00, _write_slot_passes даёт ещё один
        assert len(retract_lines) == 2
        # Несколько проходов по XY
        xy_moves = [l for l in gcode.splitlines() if l.startswith("G01 X")]
        assert len(xy_moves) >= 3  # центр + минимум 2 боковых прохода
