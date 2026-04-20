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
        valid_types = {'rapid', 'feed', 'drill_down', 'drill_up', 'slot_h', 'outline'}
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

    def test_outline_section_detection(self):
        """Проверка что сегменты в секции outline milling получают тип 'outline'."""
        gcode = """; Tool T100 D=2.00mm
; ===== BOARD OUTLINE MILLING =====
G00 X0 Y0 F500
G01 Z-0.5 F500
G01 X10 Y0 F500
G01 X10 Y10 F500
G01 X0 Y10 F500
G01 X0 Y0 F500
G00 Z5 F500
; ===== END =====
"""
        segments = parse_gcode_for_viz(gcode)
        # Фильтруем только feed/outline сегменты (не rapid, не drill)
        outline_segments = [s for s in segments if s['type'] == 'outline']
        # Должны быть сегменты типа outline
        assert len(outline_segments) > 0
        # Проверяем что это именно outline, а не slot_h
        for seg in outline_segments:
            assert seg['type'] == 'outline'

    def test_slot_h_not_affected_by_outline(self):
        """Проверка что slot_h сегменты вне outline секции не меняют тип."""
        gcode = """; Tool T1 D=1.00mm
; ===== DRILLING =====
G00 X0 Y0 F500
G01 Z-0.5 F500
G01 X10 Y0 F500
G00 Z5 F500
"""
        segments = parse_gcode_for_viz(gcode)
        # Сегмент G01 с X,Y должен быть slot_h, не outline
        slot_segments = [s for s in segments if s['type'] == 'slot_h']
        assert len(slot_segments) > 0
