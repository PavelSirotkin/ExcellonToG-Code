"""
Тесты для модуля gcode_parser.
"""
import pytest
import os
from core.gcode_parser import parse_gcode_for_viz


FIXTURES_DIR = os.path.join(os.path.dirname(__file__), 'fixtures')


class TestParseGcodeForViz:
    def test_parse_basic_gcode(self):
        path = os.path.join(FIXTURES_DIR, 'test_gcode.tap')
        with open(path, 'r') as f:
            gcode_text = f.read()
        segments = parse_gcode_for_viz(gcode_text)
        assert len(segments) > 0

    def test_segment_has_required_keys(self):
        path = os.path.join(FIXTURES_DIR, 'test_gcode.tap')
        with open(path, 'r') as f:
            gcode_text = f.read()
        segments = parse_gcode_for_viz(gcode_text)
        required_keys = {'type', 'x0', 'y0', 'z0', 'x1', 'y1', 'z1', 'tool', 'diameter'}
        for seg in segments:
            assert required_keys.issubset(seg.keys())

    def test_segment_types(self):
        path = os.path.join(FIXTURES_DIR, 'test_gcode.tap')
        with open(path, 'r') as f:
            gcode_text = f.read()
        segments = parse_gcode_for_viz(gcode_text)
        valid_types = {'rapid', 'feed', 'drill_down', 'drill_up', 'slot_h'}
        for seg in segments:
            assert seg['type'] in valid_types

    def test_drill_down_up_sequence(self):
        path = os.path.join(FIXTURES_DIR, 'test_gcode.tap')
        with open(path, 'r') as f:
            gcode_text = f.read()
        segments = parse_gcode_for_viz(gcode_text)
        # В файле 3 отверстия, значит должны быть drill_down и drill_up
        types = [seg['type'] for seg in segments]
        assert 'drill_down' in types
        assert 'drill_up' in types

    def test_coordinates_are_numeric(self):
        path = os.path.join(FIXTURES_DIR, 'test_gcode.tap')
        with open(path, 'r') as f:
            gcode_text = f.read()
        segments = parse_gcode_for_viz(gcode_text)
        for seg in segments:
            for key in ['x0', 'y0', 'z0', 'x1', 'y1', 'z1']:
                assert isinstance(seg[key], (int, float)), f"{key} не число: {seg[key]}"

    def test_empty_gcode(self):
        segments = parse_gcode_for_viz("")
        assert segments == []

    def test_comments_only_gcode(self):
        segments = parse_gcode_for_viz("; Comment 1\n; Comment 2\n")
        assert segments == []

    def test_tool_extraction_from_comments(self):
        """Проверка что инструмент извлекается из комментариев."""
        gcode = """; Tool T1 D=1.00mm
G00 X0 Y0
G00 X10 Y10
"""
        segments = parse_gcode_for_viz(gcode)
        assert len(segments) > 0
        # Первый сегмент должен иметь T1
        assert segments[0]['tool'] == '1'
