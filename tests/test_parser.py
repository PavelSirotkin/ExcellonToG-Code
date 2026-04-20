"""
Тесты для модуля parser.
"""
import pytest
import os
from core.parser import (
    detect_coordinate_format,
    is_excellon_file,
    parse_excellon_file,
    parse_slot_file,
)


FIXTURES_DIR = os.path.join(os.path.dirname(__file__), 'fixtures')


class TestDetectCoordinateFormat:
    def test_3_3_format(self):
        path = os.path.join(FIXTURES_DIR, 'test_3_3.drl')
        result = detect_coordinate_format(path)
        assert result == "3.3"

    def test_4_2_format(self):
        path = os.path.join(FIXTURES_DIR, 'test_4_2.drl')
        result = detect_coordinate_format(path)
        assert result == "4.2"

    def test_nonexistent_file(self):
        result = detect_coordinate_format("nonexistent_file.drl")
        assert result is None

    def test_no_format_in_file(self):
        # Создаём временный файл без формата
        path = os.path.join(FIXTURES_DIR, 'test_gcode.tap')
        result = detect_coordinate_format(path)
        assert result is None


class TestIsExcellonFile:
    def test_valid_3_3_file(self):
        path = os.path.join(FIXTURES_DIR, 'test_3_3.drl')
        assert is_excellon_file(path) is True

    def test_valid_4_2_file(self):
        path = os.path.join(FIXTURES_DIR, 'test_4_2.drl')
        assert is_excellon_file(path) is True

    def test_non_excellon_file(self):
        path = os.path.join(FIXTURES_DIR, 'test_gcode.tap')
        assert is_excellon_file(path) is False

    def test_nonexistent_file(self):
        assert is_excellon_file("nonexistent_file.drl") is False


class TestParseExcellonFile:
    def test_parse_3_3_file(self):
        path = os.path.join(FIXTURES_DIR, 'test_3_3.drl')
        tools = parse_excellon_file(path, coord_format="3.3")
        assert len(tools) == 3
        # T1 должен иметь 3 отверстия
        assert len(tools['1']['holes']) == 3
        # T2 — 2 отверстия
        assert len(tools['2']['holes']) == 2
        # T3 — 4 отверстия
        assert len(tools['3']['holes']) == 4

    def test_parse_4_2_file(self):
        path = os.path.join(FIXTURES_DIR, 'test_4_2.drl')
        tools = parse_excellon_file(path, coord_format="4.2")
        assert len(tools) == 2
        assert len(tools['01']['holes']) == 2
        assert len(tools['02']['holes']) == 2

    def test_coordinates_are_correct(self):
        path = os.path.join(FIXTURES_DIR, 'test_3_3.drl')
        tools = parse_excellon_file(path, coord_format="3.3")
        # Формат 3.3 -> делим на 10^3 = 1000
        # X10000Y20000 -> X=10.0, Y=20.0
        t1_holes = tools['1']['holes']
        # После TSP порядок может измениться, но точки должны совпасть
        coords_set = set((round(h[0], 3), round(h[1], 3)) for h in t1_holes)
        expected = {(10.0, 20.0), (30.0, 40.0), (50.0, 60.0)}
        assert coords_set == expected

    def test_tools_sorted_by_diameter(self):
        path = os.path.join(FIXTURES_DIR, 'test_3_3.drl')
        tools = parse_excellon_file(path, coord_format="3.3")
        diameters = [data['diameter'] for data in tools.values()]
        assert diameters == sorted(diameters)


class TestParseSlotFile:
    def test_parse_slots(self):
        path = os.path.join(FIXTURES_DIR, 'test_slots.drl')
        tools = parse_slot_file(path, coord_format="3.3")
        assert len(tools) == 1
        assert len(tools['1']['slots']) == 2

    def test_slot_coordinates(self):
        path = os.path.join(FIXTURES_DIR, 'test_slots.drl')
        tools = parse_slot_file(path, coord_format="3.3")
        slots = tools['1']['slots']
        # Формат 3.3 -> /1000
        # Slot 1: (10, 10) -> (30, 30)
        # Slot 2: (50, 50) -> (70, 70)
        coords = set()
        for start, end in slots:
            coords.add((round(start[0], 1), round(start[1], 1),
                        round(end[0], 1), round(end[1], 1)))
        expected = {(10.0, 10.0, 30.0, 30.0), (50.0, 50.0, 70.0, 70.0)}
        assert coords == expected
