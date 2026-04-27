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
    
    def test_tabs_start_at_correct_pass(self):
        """Тест корректного начала формирования tabs при multi-pass.
        
        Пример из issue: drill_z=-2.5, depth_per_pass=0.5, tab_height=1.0
        Проходы: -0.5, -1.0, -1.5, -2.0, -2.5
        tab_start_z = -2.5 + 1.0 = -1.5
        
        Tabs должны начинаться на проходе 3 (z=-1.5), потому что -1.5 <= -1.5.
        Это гарантирует, что итоговая высота перемычки будет 1.0 мм.
        """
        segments = [
            make_line((0, 0), (100, 0)),
            make_line((100, 0), (100, 50)),
            make_line((100, 50), (0, 50)),
            make_line((0, 50), (0, 0)),
        ]
        params = {
            'safe_z': 5.0,
            'drill_z': -2.5,
            'rapid_rate': 500,
        }
        outline_params = {
            'tool_diameter': 3.0,
            'depth_per_pass': 0.5,
            'n_tabs': 4,
            'tab_width': 5.0,
            'tab_height': 1.0,
            'direction': 'CCW',
        }

        buf = io.StringIO()
        build_outline_section(buf, segments, "test.gbr", params, outline_params, tool_num=100)

        gcode = buf.getvalue()

        # Должно быть 5 проходов
        assert "Pass 1/5" in gcode
        assert "Pass 2/5" in gcode
        assert "Pass 3/5" in gcode
        assert "Pass 4/5" in gcode
        assert "Pass 5/5" in gcode

        # Разбиваем G-code на проходы
        passes = gcode.split("; Pass ")
        
        # Проходы 1 и 2 (z=-0.5, z=-1.0) НЕ должны содержать TAB BEGIN/END
        # потому что они выше уровня tab_start_z = -1.5
        pass1 = passes[1]  # "1/5, Z=-0.50\n..."
        pass2 = passes[2]  # "2/5, Z=-1.00\n..."
        assert "TAB BEGIN" not in pass1, "Проход 1 не должен содержать tabs"
        assert "TAB BEGIN" not in pass2, "Проход 2 не должен содержать tabs"

        # Проходы 3, 4, 5 (z=-1.5, z=-2.0, z=-2.5) ДОЛЖНЫ содержать TAB BEGIN/END
        # потому что они на уровне или ниже tab_start_z = -1.5
        pass3 = passes[3]  # "3/5, Z=-1.50\n..."
        pass4 = passes[4]  # "4/5, Z=-2.00\n..."
        pass5 = passes[5]  # "5/5, Z=-2.50\n..."
        assert "TAB BEGIN" in pass3, "Проход 3 должен содержать tabs (z=-1.5 = tab_start_z)"
        assert "TAB BEGIN" in pass4, "Проход 4 должен содержать tabs"
        assert "TAB BEGIN" in pass5, "Проход 5 должен содержать tabs"
        
        # Проверяем, что в проходах с tabs есть подъём на tab_height
        # Формат: G01 Z-1.50 (или -0.50 для tab_height=1.0 на проходе z=-1.5)
        # На проходе 3 (z=-1.5): tab_z = -1.5 + 1.0 = -0.5
        assert "Z-0.50" in pass3, "Проход 3 должен содержать подъём до z=-0.5 (tab level)"
