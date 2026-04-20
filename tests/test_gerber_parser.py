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
