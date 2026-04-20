"""
Тесты для генерации G-code обрезки по контуру.
"""
import pytest
import io
from core.outline_gcode import build_outline_section
from core.gerber_parser import make_line


class TestBuildOutlineSection:
    def test_simple_outline(self):
        """Тест генерации G-code для простого контура."""
        segments = [
            make_line((0, 0), (10, 0)),
            make_line((10, 0), (10, 15)),
            make_line((10, 15), (0, 15)),
            make_line((0, 15), (0, 0)),
        ]
        params = {
            'safe_z': 5.0,
            'drill_z': -1.6,
            'rapid_rate': 500,
        }
        outline_params = {
            'tool_diameter': 2.0,
            'depth_per_pass': 1.0,
            'n_tabs': 4,
            'tab_width': 3.0,
            'tab_height': 0.5,
            'direction': 'CCW',
        }

        buf = io.StringIO()
        build_outline_section(buf, segments, "test.gbr", params, outline_params, tool_num=100)

        gcode = buf.getvalue()

        # Проверяем наличие ключевых элементов
        assert "BOARD OUTLINE MILLING" in gcode
        assert "T100" in gcode or "Tool T100" in gcode
        assert "D=2.00mm" in gcode
        assert "G00" in gcode
        assert "G01" in gcode
        assert "M30" not in gcode  # M30 не должен быть в секции

    def test_multipass_z_levels(self):
        """Тест многоуровневой обработки по Z."""
        segments = [
            make_line((0, 0), (10, 0)),
            make_line((10, 0), (10, 10)),
            make_line((10, 10), (0, 10)),
            make_line((0, 10), (0, 0)),
        ]
        params = {
            'safe_z': 5.0,
            'drill_z': -1.6,  # Глубина 1.6 мм
            'rapid_rate': 500,
        }
        outline_params = {
            'tool_diameter': 2.0,
            'depth_per_pass': 0.5,  # Шаг 0.5 мм
            'n_tabs': 0,  # Без tabs для простоты
            'tab_width': 0,
            'tab_height': 0,
            'direction': 'CCW',
        }

        buf = io.StringIO()
        build_outline_section(buf, segments, "test.gbr", params, outline_params, tool_num=100)

        gcode = buf.getvalue()

        # Должно быть 4 прохода: -0.5, -1.0, -1.5, -1.6
        assert "Pass 1" in gcode
        assert "Pass 2" in gcode
        assert "Pass 3" in gcode
        assert "Pass 4" in gcode

    def test_empty_outline(self):
        """Тест с пустым контуром."""
        params = {
            'safe_z': 5.0,
            'drill_z': -1.6,
            'rapid_rate': 500,
        }
        outline_params = {
            'tool_diameter': 2.0,
            'depth_per_pass': 0.5,
            'n_tabs': 4,
            'tab_width': 3.0,
            'tab_height': 0.5,
            'direction': 'CCW',
        }

        buf = io.StringIO()
        build_outline_section(buf, [], "test.gbr", params, outline_params, tool_num=100)

        gcode = buf.getvalue()
        assert gcode == ""  # Пустой вывод для пустого контура

    def test_cw_direction(self):
        """Тест направления CW."""
        segments = [
            make_line((0, 0), (10, 0)),
            make_line((10, 0), (10, 10)),
            make_line((10, 10), (0, 10)),
            make_line((0, 10), (0, 0)),
        ]
        params = {
            'safe_z': 5.0,
            'drill_z': -1.0,
            'rapid_rate': 500,
        }
        outline_params = {
            'tool_diameter': 2.0,
            'depth_per_pass': 1.0,
            'n_tabs': 0,
            'tab_width': 0,
            'tab_height': 0,
            'direction': 'CW',
        }

        buf = io.StringIO()
        build_outline_section(buf, segments, "test.gbr", params, outline_params, tool_num=100)

        gcode = buf.getvalue()
        assert "Direction: CW" in gcode
