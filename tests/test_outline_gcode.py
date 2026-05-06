"""
Тесты для генерации G-code обрезки по контуру.
"""
import pytest
import re
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


class TestOutlineWithCutout:
    """Контур с вырезом: каждый подконтур фрезеруется отдельно,
    переход между ними — через safe Z, без рабочего движения над платой."""

    def _outer_with_cutout(self):
        """Плата 30x30 с квадратным вырезом 10x10 по центру."""
        outline = [
            {**make_line((0, 0), (30, 0)), 'subpath_start': True},
            make_line((30, 0), (30, 30)),
            make_line((30, 30), (0, 30)),
            make_line((0, 30), (0, 0)),
        ]
        cutout = [
            {**make_line((10, 10), (20, 10)), 'subpath_start': True},
            make_line((20, 10), (20, 20)),
            make_line((20, 20), (10, 20)),
            make_line((10, 20), (10, 10)),
        ]
        return outline + cutout

    def _params(self, **outline_overrides):
        params = {'safe_z': 5.0, 'drill_z': -1.0, 'rapid_rate': 500}
        outline_params = {
            'tool_diameter': 1.0,
            'depth_per_pass': 1.0,
            'n_tabs': 4,
            'tab_width': 2.0,
            'tab_height': 0.5,
            'direction': 'CCW',
        }
        outline_params.update(outline_overrides)
        return params, outline_params

    def test_outer_milled_before_inner(self):
        """Внешний контур должен идти раньше выреза."""
        segments = self._outer_with_cutout()
        params, outline_params = self._params()
        buf = io.StringIO()
        build_outline_section(buf, segments, "x.gbr", params, outline_params)
        gcode = buf.getvalue()
        outer_pos = gcode.find("outer contour")
        inner_pos = gcode.find("inner cutout")
        assert outer_pos != -1 and inner_pos != -1
        assert outer_pos < inner_pos

    def test_safe_z_retract_between_subpaths(self):
        """Между подконтурами фреза должна выйти на safe_z, иначе
        переезд пройдёт по платe на рабочей глубине."""
        segments = self._outer_with_cutout()
        params, outline_params = self._params()
        buf = io.StringIO()
        build_outline_section(buf, segments, "x.gbr", params, outline_params)
        gcode = buf.getvalue()

        # Вырезаем участок между концом outer и началом inner
        outer_marker = "outer contour"
        inner_marker = "inner cutout"
        outer_idx = gcode.find(outer_marker)
        inner_idx = gcode.find(inner_marker)
        assert outer_idx >= 0 and inner_idx > outer_idx
        between = gcode[outer_idx:inner_idx]

        # В переходе обязан быть подъём до safe_z (5.0)
        assert re.search(r"Z\s*5\.0+", between), (
            "Между подконтурами должен быть retract на safe_z=5.0; "
            f"фрагмент:\n{between}"
        )

    def test_tabs_only_on_outer(self):
        """Tabs должны присутствовать ТОЛЬКО на участке внешнего контура.
        На вырезе перемычки бессмысленны (плата вокруг выреза цела)."""
        segments = self._outer_with_cutout()
        # drill_z=-1.0, tab_height=0.5 → tab_start_z=-0.5;
        # depth_per_pass=0.5 → проходы -0.5, -1.0; tabs на обоих
        params, outline_params = self._params(
            drill_z=-1.0, depth_per_pass=0.5, tab_height=0.5)
        buf = io.StringIO()
        build_outline_section(buf, segments, "x.gbr", params, outline_params)
        gcode = buf.getvalue()

        outer_section = gcode[gcode.find("outer contour"):gcode.find("inner cutout")]
        inner_section = gcode[gcode.find("inner cutout"):]
        assert "TAB BEGIN" in outer_section
        assert "TAB BEGIN" not in inner_section, (
            f"На вырезе не должно быть tabs:\n{inner_section}"
        )

    def test_inner_uses_inward_offset(self):
        """Для выреза offset должен быть ВНУТРЬ — фреза идёт по
        окружности МЕНЬШЕ чем граница выреза. Проверяем через bbox
        XY-координат: внутренний путь не должен выходить за пределы
        исходного выреза [10..20] x [10..20]."""
        segments = self._outer_with_cutout()
        params, outline_params = self._params(tool_diameter=2.0, n_tabs=0)
        buf = io.StringIO()
        build_outline_section(buf, segments, "x.gbr", params, outline_params)
        gcode = buf.getvalue()

        inner_section = gcode[gcode.find("inner cutout"):]
        # Извлекаем X/Y координаты из inner-секции
        coords = re.findall(r"X(-?\d+\.\d+)\s+Y(-?\d+\.\d+)", inner_section)
        # Должны быть координаты в районе выреза, без выхода за [10..20]
        xs = [float(x) for x, _ in coords]
        ys = [float(y) for _, y in coords]
        assert xs and ys, "В inner-секции должны быть координаты"
        # Радиус фрезы 1.0 → offset inward 1.0; путь по [11..19]
        assert min(xs) >= 10.5, f"min_x={min(xs)} вышел за вырез"
        assert max(xs) <= 19.5, f"max_x={max(xs)} вышел за вырез"
        assert min(ys) >= 10.5, f"min_y={min(ys)} вышел за вырез"
        assert max(ys) <= 19.5, f"max_y={max(ys)} вышел за вырез"
