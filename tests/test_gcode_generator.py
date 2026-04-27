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
    _build_outline_only_gcode,
    _calc_multipass_offsets,
    _pick_outline_tool_num,
    emit_rapid_xy,
    emit_mill_xy,
    emit_plunge_z,
    emit_retract_z,
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

    # --- Защита от вырожденных входов (раньше зависало на этих) ---

    def test_zero_tool_diameter_returns_empty(self):
        """tool_diameter=0 ранее давал бесконечный цикл; должно быть []."""
        assert _calc_multipass_offsets(3.0, 0.0, 50) == []

    def test_negative_tool_diameter_returns_empty(self):
        assert _calc_multipass_offsets(3.0, -1.0, 50) == []

    def test_zero_slot_width_returns_empty(self):
        assert _calc_multipass_offsets(0.0, 1.0, 50) == []

    def test_negative_slot_width_returns_empty(self):
        assert _calc_multipass_offsets(-3.0, 1.0, 50) == []

    def test_tool_wider_than_slot_returns_empty(self):
        """Фреза шире слота — multi-pass невозможен."""
        assert _calc_multipass_offsets(1.0, 2.0, 50) == []

    def test_nan_inputs_return_empty(self):
        nan = float('nan')
        assert _calc_multipass_offsets(nan, 1.0, 50) == []
        assert _calc_multipass_offsets(3.0, nan, 50) == []

    def test_inf_inputs_return_empty(self):
        inf = float('inf')
        assert _calc_multipass_offsets(inf, 1.0, 50) == []
        assert _calc_multipass_offsets(3.0, inf, 50) == []

    def test_completes_under_max_iter_for_typical_params(self):
        """Типичный slot, типичная фреза → разумное число проходов, не упирается в MAX_ITER."""
        offsets = _calc_multipass_offsets(50.0, 1.0, 50)  # slot 50мм, фреза 1мм
        # Шаг 0.5; проходы 0, ±0.5, ±1.0, ... до края (24.5).
        # Должно быть около 99 проходов (центр + 49 пар), точно меньше MAX_ITER.
        assert 0 < len(offsets) < 200

    def test_multipass_skipped_when_offsets_empty(self):
        """_write_slot_passes не должен падать на пустых offsets."""
        from core.gcode_generator import _write_slot_passes
        buf = io.StringIO()
        # Пустой список offsets — раньше IndexError на passes[0]
        _write_slot_passes(buf, 0.0, 0.0, 10.0, 0.0, [],
                           drill_z=-2.0, safe_z=5.0,
                           eff_plunge=100, eff_retract=500,
                           eff_mill=50, rapid_rate=500)
        out = buf.getvalue()
        assert "Slot skipped" in out
        # Никаких реальных движений в G-code
        assert "G01 Z" not in out
        assert "G00 X" not in out

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


class TestEmitHelpers:
    """Тесты низкоуровневых хелперов вывода G-code."""

    def test_emit_rapid_xy_format(self):
        buf = io.StringIO()
        emit_rapid_xy(buf, 12.3456, -7.89, 500)
        assert buf.getvalue() == "G00 X12.346 Y-7.890 F500\n"

    def test_emit_mill_xy_format(self):
        buf = io.StringIO()
        emit_mill_xy(buf, 1.0, 2.0, 50.7)
        # Подача округляется до целого
        assert buf.getvalue() == "G01 X1.000 Y2.000 F51\n"

    def test_emit_plunge_z_format(self):
        buf = io.StringIO()
        emit_plunge_z(buf, -2.567, 100)
        assert buf.getvalue() == "G01 Z-2.57 F100\n"

    def test_emit_retract_z_format(self):
        buf = io.StringIO()
        emit_retract_z(buf, 5.0, 500)
        assert buf.getvalue() == "G00 Z5.00 F500\n"


class TestPickOutlineToolNum:
    """Тесты подбора свободного номера инструмента для секции обрезки контура."""

    def test_no_tools_returns_default(self):
        assert _pick_outline_tool_num() == 100
        assert _pick_outline_tool_num(None, None) == 100
        assert _pick_outline_tool_num({}, {}) == 100

    def test_uses_default_when_max_below(self):
        # Все инструменты ниже 100 — берём 100, чтобы контур был "выше"
        assert _pick_outline_tool_num({"1": {}, "2": {}, "10": {}}) == 100

    def test_max_plus_one_when_above_default(self):
        # Если уже есть T100 — берём 101
        assert _pick_outline_tool_num({"1": {}, "100": {}}) == 101
        # Несколько словарей — учитывает максимум среди всех
        assert _pick_outline_tool_num({"1": {}, "100": {}}, {"50": {}, "150": {}}) == 151

    def test_int_keys(self):
        # Ключи могут быть int (а не str)
        assert _pick_outline_tool_num({1: {}, 200: {}}) == 201

    def test_skips_non_numeric_keys(self):
        # Нечисловые ключи игнорируются, не валят функцию
        assert _pick_outline_tool_num({"abc": {}, "5": {}}) == 100
        assert _pick_outline_tool_num({"foo": {}}) == 100  # вернуть default


class TestOutlineToolNumIntegration:
    """Интеграционная проверка: T-номер контура не конфликтует с Excellon."""

    def _make_outline_segments(self):
        from core.gerber_parser import make_line
        return [
            make_line((0, 0), (10, 0)),
            make_line((10, 0), (10, 10)),
            make_line((10, 10), (0, 10)),
            make_line((0, 10), (0, 0)),
        ]

    def _outline_params(self):
        return {
            'tool_diameter': 2.0,
            'depth_per_pass': 1.0,
            'n_tabs': 0,
            'tab_width': 0,
            'tab_height': 0,
            'direction': 'CCW',
        }

    def _params(self):
        return {'safe_z': 5.0, 'drill_z': -1.0, 'feed_rate': 100,
                'mill_feed': 50, 'rapid_rate': 500, 'park_z': 30}

    def test_combined_picks_unique_when_t100_exists(self):
        """Если в Excellon есть T100, контур получает T101."""
        current_tools = {"100": {'diameter': 1.0, 'holes': [(0.0, 0.0)],
                                 'visible': True, 'var': None}}
        gcode, errors = _build_combined_gcode(
            current_tools, "holes.drl", None, None,
            self._params(), tool_params_dict=None,
            board_outline=self._make_outline_segments(),
            board_outline_filename="outline.gbr",
            outline_params=self._outline_params(),
        )
        assert errors == []
        # В выводе обе T-метки: T100 от сверления и T101 от контура
        assert "T100" in gcode
        assert "T101" in gcode

    def test_combined_default_100_when_no_conflict(self):
        """Если Excellon-инструменты ниже 100, контур получает T100."""
        current_tools = {"1": {'diameter': 1.0, 'holes': [(0.0, 0.0)],
                               'visible': True, 'var': None}}
        gcode, errors = _build_combined_gcode(
            current_tools, "holes.drl", None, None,
            self._params(), tool_params_dict=None,
            board_outline=self._make_outline_segments(),
            board_outline_filename="outline.gbr",
            outline_params=self._outline_params(),
        )
        assert errors == []
        assert "T100" in gcode

    def test_outline_only_avoids_loaded_tools(self):
        """Outline-only тоже учитывает уже загруженные dict'ы инструментов."""
        current_tools = {"100": {'diameter': 1.0, 'holes': [(0.0, 0.0)],
                                 'visible': True, 'var': None}}
        slot_tools = {"105": {'diameter': 2.0, 'slots': [((0.0, 0.0), (1.0, 0.0))],
                              'visible': True, 'var': None}}
        gcode, errors = _build_outline_only_gcode(
            self._make_outline_segments(), "outline.gbr",
            self._params(), self._outline_params(),
            current_tools=current_tools, slot_tools=slot_tools,
        )
        assert errors == []
        # T106 — следующий после max(100, 105)=105
        assert "T106" in gcode
