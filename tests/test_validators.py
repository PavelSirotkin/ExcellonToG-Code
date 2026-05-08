"""
Тесты для модуля validators.
"""
import pytest
import os
from core.validators import (
    validate_coordinate_format,
    validate_gcode_params,
    validate_gcode_params_strict,
    validate_file_exists,
    validate_file_readable,
    validate_excellon_header,
    validate_slot_file_structure,
    validate_tool_data,
    validate_tools_dict,
    validate_coordinate,
    validate_points_list,
    validate_gcode_segment,
    validate_gcode_segments,
)


FIXTURES_DIR = os.path.join(os.path.dirname(__file__), 'fixtures')


class TestValidateCoordinateFormat:
    def test_valid_formats(self):
        assert validate_coordinate_format("3.3") is True
        assert validate_coordinate_format("4.2") is True
        assert validate_coordinate_format("2.4") is True

    def test_invalid_formats(self):
        assert validate_coordinate_format("") is False
        assert validate_coordinate_format("abc") is False
        assert validate_coordinate_format("3,3") is False
        assert validate_coordinate_format("3") is False
        assert validate_coordinate_format("0.0") is False

    def test_edge_cases(self):
        assert validate_coordinate_format("1.1") is True
        assert validate_coordinate_format("9.9") is True

    def test_explicit_format(self):
        # "Exp" — координаты с явной десятичной точкой (KiCAD-стиль)
        assert validate_coordinate_format("Exp") is True
        # case-sensitive: "exp"/"EXP" не должны проходить
        assert validate_coordinate_format("exp") is False
        assert validate_coordinate_format("EXP") is False


class TestValidateGcodeParams:
    def test_valid_params(self):
        params = {
            'safe_z': 5.0,
            'drill_z': -2.5,
            'feed_rate': 100,
            'rapid_rate': 500,
            'park_z': 30,
        }
        assert validate_gcode_params(params) == []

    def test_all_errors(self):
        params = {
            'safe_z': -5.0,
            'drill_z': 2.5,
            'feed_rate': -100,
            'rapid_rate': 0,
            'park_z': 2,  # ниже safe_z (если safe_z положительный)
        }
        errors = validate_gcode_params(params)
        assert len(errors) >= 4

    def test_strict_valid(self):
        params = {'safe_z': 5.0, 'drill_z': -2.5, 'feed_rate': 100, 'rapid_rate': 500, 'park_z': 30}
        ok, msg = validate_gcode_params_strict(params)
        assert ok is True
        assert msg == "OK"

    def test_strict_invalid(self):
        params = {'safe_z': -5.0}
        ok, msg = validate_gcode_params_strict(params)
        assert ok is False
        assert "Безопасная Z" in msg


class TestValidateFile:
    def test_file_exists_valid(self):
        path = os.path.join(FIXTURES_DIR, 'test_3_3.drl')
        assert validate_file_exists(path) is True

    def test_file_exists_nonexistent(self):
        assert validate_file_exists("nonexistent_file.txt") is False

    def test_file_readable_valid(self):
        path = os.path.join(FIXTURES_DIR, 'test_3_3.drl')
        assert validate_file_readable(path) is True


class TestValidateExcellonHeader:
    def test_valid_excellon(self):
        path = os.path.join(FIXTURES_DIR, 'test_3_3.drl')
        assert validate_excellon_header(path) is True

    def test_invalid_excellon(self):
        path = os.path.join(FIXTURES_DIR, 'test_gcode.tap')
        assert validate_excellon_header(path) is False


class TestValidateSlotFileStructure:
    def test_valid_slots(self):
        path = os.path.join(FIXTURES_DIR, 'test_slots.drl')
        assert validate_slot_file_structure(path) is True

    def test_no_slots(self):
        path = os.path.join(FIXTURES_DIR, 'test_3_3.drl')
        assert validate_slot_file_structure(path) is False


class TestValidateToolData:
    def test_valid_tool(self):
        tool = {
            'diameter': 1.5,
            'holes': [(0, 0), (10, 10)],
            'visible': True,
        }
        assert validate_tool_data(tool) == []

    def test_missing_diameter(self):
        tool = {'holes': [(0, 0)]}
        errors = validate_tool_data(tool)
        assert len(errors) > 0
        assert any("diameter" in e for e in errors)

    def test_negative_diameter(self):
        tool = {'diameter': -1.0}
        errors = validate_tool_data(tool)
        assert len(errors) > 0

    def test_invalid_holes_type(self):
        tool = {'diameter': 1.0, 'holes': "not a list"}
        errors = validate_tool_data(tool)
        assert any("holes" in e for e in errors)

    def test_invalid_hole_coordinates(self):
        tool = {'diameter': 1.0, 'holes': [(0, 0), "invalid"]}
        errors = validate_tool_data(tool)
        assert len(errors) > 0

    def test_invalid_visible_type(self):
        tool = {'diameter': 1.0, 'visible': "yes"}
        errors = validate_tool_data(tool)
        assert any("visible" in e for e in errors)


class TestValidateToolsDict:
    def test_valid_tools(self):
        tools = {
            '1': {'diameter': 1.0, 'holes': [(0, 0)], 'visible': True},
            '2': {'diameter': 2.0, 'holes': [(10, 10)], 'visible': False},
        }
        assert validate_tools_dict(tools) == []

    def test_invalid_tools_type(self):
        errors = validate_tools_dict("not a dict")
        assert len(errors) > 0
        assert any("словарём" in e for e in errors)


class TestValidateCoordinate:
    def test_valid_coordinate(self):
        assert validate_coordinate(100.0) is True
        assert validate_coordinate(-200.0) is True

    def test_out_of_range(self):
        assert validate_coordinate(500.0) is False
        assert validate_coordinate(-500.0) is False

    def test_invalid_type(self):
        assert validate_coordinate("100") is False
        assert validate_coordinate(None) is False


class TestValidatePointsList:
    def test_valid_points(self):
        points = [(0, 0), (100, 100), (-50, 50)]
        assert validate_points_list(points) == []

    def test_invalid_point_type(self):
        points = [(0, 0), "invalid"]
        errors = validate_points_list(points)
        assert len(errors) > 0

    def test_out_of_range_point(self):
        points = [(0, 0), (500, 500)]
        errors = validate_points_list(points)
        assert len(errors) > 0


class TestValidateGcodeSegment:
    def test_valid_segment(self):
        seg = {
            'type': 'rapid',
            'x0': 0, 'y0': 0, 'z0': 5,
            'x1': 10, 'y1': 10, 'z1': 5,
        }
        assert validate_gcode_segment(seg) == []

    def test_missing_keys(self):
        seg = {'type': 'rapid'}
        errors = validate_gcode_segment(seg)
        assert len(errors) > 0
        assert any("Отсутствуют" in e for e in errors)

    def test_invalid_type(self):
        seg = {
            'type': 'invalid_type',
            'x0': 0, 'y0': 0, 'z0': 5,
            'x1': 10, 'y1': 10, 'z1': 5,
        }
        errors = validate_gcode_segment(seg)
        assert any("Неизвестный тип" in e for e in errors)

    def test_non_numeric_coordinates(self):
        seg = {
            'type': 'rapid',
            'x0': 'a', 'y0': 0, 'z0': 5,
            'x1': 10, 'y1': 10, 'z1': 5,
        }
        errors = validate_gcode_segment(seg)
        assert len(errors) > 0
        assert any("x0" in e for e in errors)


class TestValidateGcodeSegments:
    def test_valid_segments(self):
        segments = [
            {'type': 'rapid', 'x0': 0, 'y0': 0, 'z0': 5, 'x1': 10, 'y1': 10, 'z1': 5},
            {'type': 'drill_down', 'x0': 10, 'y0': 10, 'z0': 5, 'x1': 10, 'y1': 10, 'z1': -2},
        ]
        assert validate_gcode_segments(segments) == []

    def test_not_a_list(self):
        errors = validate_gcode_segments("not a list")
        assert len(errors) > 0

    def test_invalid_segment_in_list(self):
        segments = [{'type': 'rapid'}]
        errors = validate_gcode_segments(segments)
        assert len(errors) > 0
