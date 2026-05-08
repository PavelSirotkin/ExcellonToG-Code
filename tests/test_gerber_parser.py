"""
Тесты для парсера Gerber файлов.
"""
import pytest
import os
from core.gerber_parser import (
    parse_gerber_outline, is_gerber_file, check_contour_closed,
    make_line, make_arc
)


class TestMakeLine:
    def test_make_line(self):
        seg = make_line((0, 0), (10, 10))
        assert seg['type'] == 'line'
        assert seg['p1'] == (0, 0)
        assert seg['p2'] == (10, 10)


class TestMakeArc:
    def test_make_arc(self):
        seg = make_arc((5, 5), 5, (0, 5), (10, 5), True)
        assert seg['type'] == 'arc'
        assert seg['center'] == (5, 5)
        assert seg['r'] == 5
        assert seg['start'] == (0, 5)
        assert seg['end'] == (10, 5)
        assert seg['ccw'] is True


class TestIsGerberFile:
    def test_valid_gerber(self, tmp_path):
        f = tmp_path / "test.gbr"
        f.write_text("%FSLAX25Y25*%\nG04 Test*\nM02*")
        assert is_gerber_file(str(f)) is True

    def test_invalid_file(self, tmp_path):
        f = tmp_path / "test.txt"
        f.write_text("This is not a gerber file")
        assert is_gerber_file(str(f)) is False

    def test_nonexistent_file(self):
        assert is_gerber_file("/nonexistent/file.gbr") is False


class TestParseGerberOutline:
    def test_parse_rectangle_mm(self, tmp_path):
        """Парсинг прямоугольника 10x15 мм."""
        content = """G04 Rectangle 10x15mm*
%FSLAX25Y25*%
%MOMM*%
%LPD*%
G01*
G36*
X0000000Y0000000D02*
X1000000D01*
Y1500000D01*
X0000000D01*
Y0000000D01*
G37*
M02*
"""
        f = tmp_path / "rect.gbr"
        f.write_text(content)

        segments, unit, bbox = parse_gerber_outline(str(f))

        assert unit == "mm"
        assert len(segments) >= 4  # Минимум 4 стороны прямоугольника
        assert bbox[0] <= 0  # min_x
        assert bbox[1] <= 0  # min_y
        assert bbox[2] >= 10  # max_x
        assert bbox[3] >= 15  # max_y

    def test_parse_with_inch(self, tmp_path):
        """Парсинг с конвертацией из дюймов."""
        content = """G04 Test inch*
%FSLAX25Y25*%
%MOIN*%
G01*
G36*
X0393700Y0000000D01*
M02*
"""
        f = tmp_path / "inch.gbr"
        f.write_text(content)

        segments, unit, bbox = parse_gerber_outline(str(f))

        assert unit == "inch"
        # 1 дюйм = 25.4 мм
        assert bbox[2] >= 25.4 or bbox[3] >= 25.4

    def test_empty_file(self, tmp_path):
        f = tmp_path / "empty.gbr"
        f.write_text("M02*")

        segments, unit, bbox = parse_gerber_outline(str(f))

        assert len(segments) == 0
        assert bbox == (0, 0, 0, 0)


class TestCheckContourClosed:
    def test_closed_contour(self):
        segments = [
            make_line((0, 0), (10, 0)),
            make_line((10, 0), (10, 10)),
            make_line((10, 10), (0, 10)),
            make_line((0, 10), (0, 0)),
        ]
        assert check_contour_closed(segments) is True

    def test_open_contour(self):
        segments = [
            make_line((0, 0), (10, 0)),
            make_line((10, 0), (10, 10)),
            make_line((10, 10), (0, 10)),
            # Нет замыкающей линии
        ]
        assert check_contour_closed(segments) is False

    def test_empty_contour(self):
        assert check_contour_closed([]) is False

    def test_single_segment(self):
        segments = [make_line((0, 0), (10, 0))]
        assert check_contour_closed(segments) is False

    def test_closed_with_cutout(self):
        """Замкнутый внешний контур + замкнутый вырез — должен быть закрыт."""
        outline = [
            {**make_line((0, 0), (10, 0)), 'subpath_start': True},
            make_line((10, 0), (10, 10)),
            make_line((10, 10), (0, 10)),
            make_line((0, 10), (0, 0)),
        ]
        cutout = [
            {**make_line((3, 3), (7, 3)), 'subpath_start': True},
            make_line((7, 3), (7, 7)),
            make_line((7, 7), (3, 7)),
            make_line((3, 7), (3, 3)),
        ]
        assert check_contour_closed(outline + cutout) is True


class TestNegativeCoordinates:
    def test_negative_y_in_outline(self, tmp_path):
        """Y<0 не должны парситься как Y>0 (старая ошибка zfill знака)."""
        # Линия из (0, -5) в (10, -5) при формате FSLAX42Y42 (mm)
        content = """%FSLAX42Y42*%
%MOMM*%
G01*
X0000Y-0500D02*
X1000D01*
M02*
"""
        f = tmp_path / "neg.gbr"
        f.write_text(content)
        segments, _, bbox = parse_gerber_outline(str(f))
        assert segments[0]['p1'] == (0.0, -5.0)
        assert segments[0]['p2'] == (10.0, -5.0)
        assert bbox[1] == -5.0

    def test_negative_arc_offsets(self, tmp_path):
        """I/J с минусом должны давать центр в правильном квадранте."""
        # Arc CW от (10, 0) к (0, -10) с центром (0, 0): I=-10, J=0
        content = """%FSLAX42Y42*%
%MOMM*%
G01*
X1000Y0000D02*
G02*
X0000Y-1000I-1000J0000D01*
M02*
"""
        f = tmp_path / "arc_neg.gbr"
        f.write_text(content)
        segments, _, _ = parse_gerber_outline(str(f))
        arc = segments[0]
        assert arc['type'] == 'arc'
        assert arc['center'] == (0.0, 0.0)
        # Радиус должен совпадать с расстоянием до начала и конца
        import math as _m
        cx, cy = arc['center']
        assert abs(_m.hypot(arc['start'][0]-cx, arc['start'][1]-cy) - arc['r']) < 1e-6
        assert abs(_m.hypot(arc['end'][0]-cx, arc['end'][1]-cy) - arc['r']) < 1e-6


class TestSubpathParsing:
    def test_region_then_outline_marks_subpaths(self, tmp_path):
        """G36-регион и внешний контур должны попасть в РАЗНЫЕ подконтуры."""
        # 5x5 регион + 20x20 внешний контур, оба замкнуты
        content = """%FSLAX42Y42*%
%MOMM*%
G01*
G36*
X0000Y0000D02*
X0500D01*
Y0500D01*
X0000D01*
Y0000D01*
G37*
X1000Y1000D02*
X3000D01*
Y3000D01*
X1000D01*
Y1000D01*
M02*
"""
        f = tmp_path / "with_cutout.gbr"
        f.write_text(content)

        segments, _, _ = parse_gerber_outline(str(f))

        # Должно быть РОВНО два сегмента с subpath_start=True
        starts = [s for s in segments if s.get('subpath_start')]
        assert len(starts) == 2, (
            f"ожидалось 2 подконтура, найдено {len(starts)}: {starts}")

        # Контур с вырезом должен распознаваться как замкнутый
        assert check_contour_closed(segments) is True

    def test_real_sample_profile_gbr(self):
        """Парсинг реального Samples_Profile.gbr (плата с круглым вырезом).
        Должно получиться два замкнутых подконтура и контур должен
        считаться замкнутым."""
        sample = os.path.join(
            os.path.dirname(__file__), '..', 'Samples', 'Samples_Profile.gbr')
        if not os.path.exists(sample):
            pytest.skip("Samples_Profile.gbr отсутствует")
        from core.polygon_ops import split_subpaths

        segments, unit, bbox = parse_gerber_outline(sample)
        assert unit == "mm"

        subpaths = split_subpaths(segments)
        # внешний контур + один круглый вырез
        assert len(subpaths) == 2

        assert check_contour_closed(segments) is True

    def test_real_kicad_periphery_board(self):
        """KiCad-файл Edge.Cuts со штриховым описанием контура +
        внутренним круглым вырезом. После сшивки должны получиться
        2 замкнутых подконтура: 1 outer + 1 inner."""
        sample = os.path.join(
            os.path.dirname(__file__), '..', 'Samples',
            'simplified_periphery_board-Edge_Cuts.gbr')
        if not os.path.exists(sample):
            pytest.skip("simplified_periphery_board-Edge_Cuts.gbr отсутствует")
        from core.polygon_ops import split_subpaths, classify_subpaths

        segments, unit, bbox = parse_gerber_outline(sample)
        assert unit == "mm"

        subpaths = split_subpaths(segments)
        # До сшивки было бы много подконтуров по 1 сегменту;
        # после сшивки — ровно 2 петли (внешний + круглый вырез).
        assert len(subpaths) == 2, (
            f"ожидалось 2 петли после сшивки, получено {len(subpaths)}")

        # Обе петли замкнуты
        assert check_contour_closed(segments) is True

        # Классификация: 1 outer + 1 inner
        cls = classify_subpaths(segments)
        outer = [c for c in cls if c['is_outer']]
        inner = [c for c in cls if not c['is_outer']]
        assert len(outer) == 1, f"должен быть 1 outer, получено {len(outer)}"
        assert len(inner) == 1, f"должен быть 1 inner, получено {len(inner)}"
        # Inner — круглый вырез ⌀22 мм с центром (0, -18) — задан
        # двумя CW-полуокружностями I=±11, J=0 при формате X4.6.
        # → bbox внутреннего ~ x∈[-11,11], y∈[-29,-7].
        inner_polygon = inner[0]['polygon']
        ixs = [p[0] for p in inner_polygon]
        iys = [p[1] for p in inner_polygon]
        assert -11.5 <= min(ixs) and max(ixs) <= 11.5
        assert -29.5 <= min(iys) and max(iys) <= -6.5
