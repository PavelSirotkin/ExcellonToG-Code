"""
Тесты для модуля parser.
"""
import pytest
import os
from core.parser import (
    detect_coordinate_format,
    detect_zero_suppression,
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

    def test_explicit_decimal_in_body_returns_exp(self):
        # G-code .tap содержит координаты вида "X1.000 Y2.000" — явный
        # десятичный формат. detect_coordinate_format должен вернуть 'Exp',
        # т.к. явная точка перебивает любые позиционные форматные подсказки.
        path = os.path.join(FIXTURES_DIR, 'test_gcode.tap')
        result = detect_coordinate_format(path)
        assert result == "Exp"


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


class TestCoordinateFormatValidation:
    def test_parse_excellon_invalid_format_string(self):
        """parse_excellon_file должен выбросить ValueError при некорректном формате."""
        path = os.path.join(FIXTURES_DIR, 'test_3_3.drl')
        with pytest.raises(ValueError, match="Неверный формат координат 'invalid'"):
            parse_excellon_file(path, coord_format="invalid")

    def test_parse_excellon_invalid_format_no_dot(self):
        """parse_excellon_file должен выбросить ValueError при формате без точки."""
        path = os.path.join(FIXTURES_DIR, 'test_3_3.drl')
        with pytest.raises(ValueError, match="Неверный формат координат '33'"):
            parse_excellon_file(path, coord_format="33")

    def test_parse_excellon_invalid_format_non_numeric(self):
        """parse_excellon_file должен выбросить ValueError при нечисловом формате."""
        path = os.path.join(FIXTURES_DIR, 'test_3_3.drl')
        with pytest.raises(ValueError, match="Неверный формат координат 'a.b'"):
            parse_excellon_file(path, coord_format="a.b")

    def test_parse_excellon_invalid_format_empty(self):
        """parse_excellon_file должен выбросить ValueError при пустом формате."""
        path = os.path.join(FIXTURES_DIR, 'test_3_3.drl')
        with pytest.raises(ValueError, match="Неверный формат координат ''"):
            parse_excellon_file(path, coord_format="")

    def test_parse_slot_invalid_format_string(self):
        """parse_slot_file должен выбросить ValueError при некорректном формате."""
        path = os.path.join(FIXTURES_DIR, 'test_slots.drl')
        with pytest.raises(ValueError, match="Неверный формат координат 'bad'"):
            parse_slot_file(path, coord_format="bad")

    def test_parse_slot_invalid_format_empty(self):
        """parse_slot_file должен выбросить ValueError при пустом формате."""
        path = os.path.join(FIXTURES_DIR, 'test_slots.drl')
        with pytest.raises(ValueError, match="Неверный формат координат ''"):
            parse_slot_file(path, coord_format="")

    def test_parse_slot_invalid_format_no_dot(self):
        """parse_slot_file должен выбросить ValueError при формате без точки."""
        path = os.path.join(FIXTURES_DIR, 'test_slots.drl')
        with pytest.raises(ValueError, match="Неверный формат координат '42'"):
            parse_slot_file(path, coord_format="42")

    def test_parse_excellon_zero_fractional_part(self):
        """parse_excellon_file должен выбросить ValueError при нулевой дробной части."""
        path = os.path.join(FIXTURES_DIR, 'test_3_3.drl')
        with pytest.raises(ValueError, match="Дробная часть должна быть > 0"):
            parse_excellon_file(path, coord_format="3.0")

    def test_parse_slot_zero_fractional_part(self):
        """parse_slot_file должен выбросить ValueError при нулевой дробной части."""
        path = os.path.join(FIXTURES_DIR, 'test_slots.drl')
        with pytest.raises(ValueError, match="Дробная часть должна быть > 0"):
            parse_slot_file(path, coord_format="4.0")


class TestDetectZeroSuppression:
    """Автоопределение режима подавления нулей (LZ/TZ) из заголовка."""

    def test_explicit_lz_marker(self, tmp_path):
        f = tmp_path / "test.drl"
        f.write_text("M48\nMETRIC,LZ\nFORMAT,3.3\n%\n")
        assert detect_zero_suppression(str(f)) == "LZ"

    def test_explicit_tz_marker(self, tmp_path):
        f = tmp_path / "test.drl"
        f.write_text("M48\nMETRIC,TZ\nFORMAT,3.3\n%\n")
        assert detect_zero_suppression(str(f)) == "TZ"

    def test_inch_lz(self, tmp_path):
        f = tmp_path / "test.drl"
        f.write_text("M48\nINCH,LZ\nFORMAT,2.4\n%\n")
        assert detect_zero_suppression(str(f)) == "LZ"

    def test_inch_tz_with_format_suffix(self, tmp_path):
        # Реальный заголовок Altium: "METRIC,TZ,000.000"
        f = tmp_path / "test.drl"
        f.write_text("M48\nMETRIC,TZ,000.000\n%\n")
        assert detect_zero_suppression(str(f)) == "TZ"

    def test_comment_trailing_zeros_included_means_lz(self, tmp_path):
        # ";TRAILING ZEROS INCLUDED" = подавлены ведущие = LZ
        f = tmp_path / "test.drl"
        f.write_text("M48\n;TRAILING ZEROS INCLUDED\nFORMAT,3.3\n%\n")
        assert detect_zero_suppression(str(f)) == "LZ"

    def test_comment_leading_zeros_included_means_tz(self, tmp_path):
        # ";LEADING ZEROS INCLUDED" = подавлены конечные = TZ
        f = tmp_path / "test.drl"
        f.write_text("M48\n;LEADING ZEROS INCLUDED\nFORMAT,3.3\n%\n")
        assert detect_zero_suppression(str(f)) == "TZ"

    def test_no_marker_returns_none(self, tmp_path):
        f = tmp_path / "test.drl"
        f.write_text("M48\nMETRIC\nFORMAT,3.3\n%\n")
        assert detect_zero_suppression(str(f)) is None

    def test_nonexistent_file(self):
        assert detect_zero_suppression("nonexistent_file.drl") is None

    def test_does_not_match_lzip_or_tzero(self, tmp_path):
        # Не должно срабатывать на словах, где LZ/TZ — часть другого слова
        f = tmp_path / "test.drl"
        f.write_text("M48\n; built with LZIP compression and TZERO test\nFORMAT,3.3\n%\n")
        assert detect_zero_suppression(str(f)) is None


class TestExplicitDecimalFormat:
    """Поддержка формата 'Exp' — явная десятичная точка в координатах
    (характерно для KiCAD/Pcbnew).
    """

    def test_detect_exp_from_kicad_body(self, tmp_path):
        """KiCAD-стиль: тело содержит X1.0Y59.0 → автодетект 'Exp'."""
        content = (
            "M48\n"
            "; FORMAT={-:-/ absolute / metric / decimal}\n"
            "FMAT,2\n"
            "METRIC\n"
            "T1C0.600\n"
            "%\n"
            "G90\n"
            "G05\n"
            "T1\n"
            "X1.0Y59.0\n"
            "X99.0Y1.0\n"
            "M30\n"
        )
        f = tmp_path / "kicad.drl"
        f.write_text(content)
        assert detect_coordinate_format(str(f)) == "Exp"

    def test_detect_exp_overrides_header_format(self, tmp_path):
        """Если в заголовке есть FORMAT,3.3, но в теле явные десятичные —
        автодетект всё равно возвращает 'Exp' (явное побеждает позиционное)."""
        content = (
            "M48\nMETRIC\nFORMAT,3.3\nT1C0.5\n%\n"
            "T1\nX10.5Y20.25\nM30\n"
        )
        f = tmp_path / "mixed.drl"
        f.write_text(content)
        assert detect_coordinate_format(str(f)) == "Exp"

    def test_detect_does_not_misfire_on_format_decimal_comment(self, tmp_path):
        """Комментарий 'FORMAT={... decimal}' в заголовке не должен сам по себе
        давать 'Exp' — нужны именно X/Y координаты с точкой в теле."""
        content = (
            "M48\n"
            "; FORMAT={-:-/ absolute / metric / decimal}\n"
            "FMAT,2\nMETRIC\nFORMAT,3.3\nT1C0.5\n%\n"
            "T1\nX1500Y2500\nM30\n"
        )
        f = tmp_path / "no_explicit_body.drl"
        f.write_text(content)
        # Тело — целочисленное → должно сработать заголовочное правило 3.3
        assert detect_coordinate_format(str(f)) == "3.3"

    def test_parse_kicad_exp_file(self, tmp_path):
        """Полный парс KiCAD-файла: координаты совпадают с записанными в файле."""
        content = (
            "M48\n"
            "; FORMAT={-:-/ absolute / metric / decimal}\n"
            "FMAT,2\nMETRIC\n"
            "T1C0.600\n"
            "%\nG90\nG05\nT1\n"
            "X1.0Y59.0\n"
            "X1.0Y1.0\n"
            "X99.0Y59.0\n"
            "X99.0Y1.0\n"
            "M30\n"
        )
        f = tmp_path / "kicad_full.drl"
        f.write_text(content)
        tools = parse_excellon_file(str(f), coord_format="Exp")
        assert len(tools) == 1
        assert tools['1']['diameter'] == 0.6
        # 4 отверстия с теми же координатами, что в файле
        coords = set(tools['1']['holes'])
        assert coords == {(1.0, 59.0), (1.0, 1.0), (99.0, 59.0), (99.0, 1.0)}

    def test_parse_exp_negative_and_fractional(self, tmp_path):
        content = (
            "M48\nMETRIC\nT1C0.5\n%\nT1\n"
            "X-12.345Y6.789\n"
            "X+0.001Y-0.001\n"
            "M30\n"
        )
        f = tmp_path / "neg.drl"
        f.write_text(content)
        tools = parse_excellon_file(str(f), coord_format="Exp")
        coords = set(tools['1']['holes'])
        assert coords == {(-12.345, 6.789), (0.001, -0.001)}

    def test_parse_exp_slot_file(self, tmp_path):
        content = (
            "M48\nMETRIC\nT1C1.0\n%\n"
            "T1\nG00X1.5Y2.5\nM15\nG01X3.5Y4.5\nM16\nM30\n"
        )
        f = tmp_path / "slot_exp.drl"
        f.write_text(content)
        tools = parse_slot_file(str(f), coord_format="Exp")
        assert tools['1']['slots'] == [((1.5, 2.5), (3.5, 4.5))]

    def test_decimal_in_integer_format_falls_back_to_literal(self, tmp_path):
        """Если в файле смешаны целые и явные десятичные — _decode_coord
        обрабатывает явные десятичные литерально независимо от coord_format.
        Это даёт устойчивость к нестандартным комбинациям."""
        content = (
            "M48\nMETRIC\nFORMAT,3.3\nT1C0.5\n%\n"
            "T1\nX1.0Y2.0\nM30\n"
        )
        f = tmp_path / "mixed.drl"
        f.write_text(content)
        # Даже с coord_format="3.3" явная точка читается как float
        tools = parse_excellon_file(str(f), coord_format="3.3")
        assert tools['1']['holes'] == [(1.0, 2.0)]


class TestZeroSuppressionParsing:
    """Корректное декодирование координат для LZ/TZ/NONE режимов (находка C1)."""

    def test_lz_mode_default_for_legacy_files(self, tmp_path):
        """Файл без LZ/TZ-маркера → дефолт LZ. Поведение совместимо со старым."""
        content = "M48\nMETRIC\nFORMAT,3.3\nT1C1.0\n%\nT1\nX1500Y2500\nM30\n"
        f = tmp_path / "no_marker.drl"
        f.write_text(content)
        tools = parse_excellon_file(str(f), coord_format="3.3")
        # 1500/1000 = 1.5; 2500/1000 = 2.5
        assert tools['1']['holes'] == [(1.5, 2.5)]

    def test_lz_explicit_header(self, tmp_path):
        """Явный INCH,LZ заголовок: ведущие нули подавлены."""
        content = "M48\nMETRIC,LZ\nFORMAT,3.3\nT1C1.0\n%\nT1\nX1500Y2500\nM30\n"
        f = tmp_path / "lz.drl"
        f.write_text(content)
        tools = parse_excellon_file(str(f), coord_format="3.3")
        assert tools['1']['holes'] == [(1.5, 2.5)]

    def test_tz_mode_pads_right(self, tmp_path):
        """TZ: цифры выравнены влево, конечные нули подавлены.
        В формате 3.3 (ширина=6) X15 → "150000" → 150 → 150мм."""
        content = "M48\nMETRIC,TZ\nFORMAT,3.3\nT1C1.0\n%\nT1\nX15Y25\nM30\n"
        f = tmp_path / "tz.drl"
        f.write_text(content)
        tools = parse_excellon_file(str(f), coord_format="3.3")
        assert tools['1']['holes'] == [(150.0, 250.0)]

    def test_tz_with_full_width_coords(self, tmp_path):
        """TZ с уже полной шириной координат — поведение как у LZ."""
        content = "M48\nMETRIC,TZ\nFORMAT,3.3\nT1C1.0\n%\nT1\nX001500Y002500\nM30\n"
        f = tmp_path / "tz_full.drl"
        f.write_text(content)
        tools = parse_excellon_file(str(f), coord_format="3.3")
        # "001500" уже 6 цифр, ljust не меняет → 1500 / 1000 = 1.5
        assert tools['1']['holes'] == [(1.5, 2.5)]

    def test_explicit_zero_mode_overrides_header(self, tmp_path):
        """Явный zero_mode=... перебивает автодетект из заголовка."""
        content = "M48\nMETRIC,LZ\nFORMAT,3.3\nT1C1.0\n%\nT1\nX15Y25\nM30\n"
        f = tmp_path / "lz_overridden.drl"
        f.write_text(content)
        tools = parse_excellon_file(str(f), coord_format="3.3", zero_mode="TZ")
        assert tools['1']['holes'] == [(150.0, 250.0)]

    def test_invalid_zero_mode(self, tmp_path):
        f = tmp_path / "test.drl"
        f.write_text("M48\nMETRIC\nFORMAT,3.3\nT1C1.0\n%\nT1\nX100Y200\n")
        with pytest.raises(ValueError, match="Неверный zero_mode"):
            parse_excellon_file(str(f), coord_format="3.3", zero_mode="INVALID")

    def test_negative_coordinates_lz(self, tmp_path):
        content = "M48\nMETRIC,LZ\nFORMAT,3.3\nT1C1.0\n%\nT1\nX-1500Y-2500\nM30\n"
        f = tmp_path / "neg_lz.drl"
        f.write_text(content)
        tools = parse_excellon_file(str(f), coord_format="3.3")
        assert tools['1']['holes'] == [(-1.5, -2.5)]

    def test_negative_coordinates_tz(self, tmp_path):
        content = "M48\nMETRIC,TZ\nFORMAT,3.3\nT1C1.0\n%\nT1\nX-15Y-25\nM30\n"
        f = tmp_path / "neg_tz.drl"
        f.write_text(content)
        tools = parse_excellon_file(str(f), coord_format="3.3")
        # "-15" → знак отделён, "15" → "150000" → 150, со знаком → -150
        assert tools['1']['holes'] == [(-150.0, -250.0)]

    def test_slot_file_respects_zero_mode(self, tmp_path):
        """parse_slot_file тоже декодирует с учётом TZ."""
        content = (
            "M48\nMETRIC,TZ\nFORMAT,3.3\nT1C1.0\n%\n"
            "T1\nG00X1Y2\nM15\nG01X3Y4\nM16\nM30\n"
        )
        f = tmp_path / "slot_tz.drl"
        f.write_text(content)
        tools = parse_slot_file(str(f), coord_format="3.3")
        slots = tools['1']['slots']
        assert len(slots) == 1
        # X1→100мм, Y2→200мм, X3→300мм, Y4→400мм
        assert slots[0] == ((100.0, 200.0), (300.0, 400.0))


class TestSlotPartialCoordinatesH1:
    """H1: slot-парсер строго требует обе координаты на G00; G01 может
    наследовать модально. Раньше отсутствие координаты молча подменялось 0."""

    def test_g00_missing_y_is_skipped(self, tmp_path, caplog):
        """G00 только с X → слот пропускается, в лог пишется warning."""
        content = (
            "M48\nMETRIC\nFORMAT,3.3\nT1C1.0\n%\n"
            "T1\nG00X10000\nM15\nG01Y20000\nM16\nM30\n"
        )
        f = tmp_path / "partial.drl"
        f.write_text(content)
        with caplog.at_level("WARNING", logger="core.parser"):
            tools = parse_slot_file(str(f), coord_format="3.3")
        # Слотов быть не должно
        assert tools['1']['slots'] == []
        # Должен быть warning о пропуске
        assert any("G00 must have both X and Y" in rec.message for rec in caplog.records)

    def test_g00_missing_x_is_skipped(self, tmp_path, caplog):
        content = (
            "M48\nMETRIC\nFORMAT,3.3\nT1C1.0\n%\n"
            "T1\nG00Y10000\nM15\nG01X30000Y20000\nM16\nM30\n"
        )
        f = tmp_path / "partial2.drl"
        f.write_text(content)
        with caplog.at_level("WARNING", logger="core.parser"):
            tools = parse_slot_file(str(f), coord_format="3.3")
        assert tools['1']['slots'] == []

    def test_g01_modal_x_inherits_from_g00(self, tmp_path):
        """Стандартное Excellon-поведение: G01 без X наследует X из G00."""
        content = (
            "M48\nMETRIC\nFORMAT,3.3\nT1C1.0\n%\n"
            "T1\nG00X10000Y10000\nM15\nG01Y30000\nM16\nM30\n"
        )
        f = tmp_path / "modal_g01_x.drl"
        f.write_text(content)
        tools = parse_slot_file(str(f), coord_format="3.3")
        slots = tools['1']['slots']
        assert len(slots) == 1
        assert slots[0] == ((10.0, 10.0), (10.0, 30.0))  # X модально из G00

    def test_g01_modal_y_inherits_from_g00(self, tmp_path):
        content = (
            "M48\nMETRIC\nFORMAT,3.3\nT1C1.0\n%\n"
            "T1\nG00X10000Y10000\nM15\nG01X30000\nM16\nM30\n"
        )
        f = tmp_path / "modal_g01_y.drl"
        f.write_text(content)
        tools = parse_slot_file(str(f), coord_format="3.3")
        slots = tools['1']['slots']
        assert len(slots) == 1
        assert slots[0] == ((10.0, 10.0), (30.0, 10.0))  # Y модально из G00

    def test_full_slot_still_works(self, tmp_path):
        """Регрессия: полные слоты с обоими X и Y продолжают работать."""
        content = (
            "M48\nMETRIC\nFORMAT,3.3\nT1C1.0\n%\n"
            "T1\nG00X10000Y10000\nM15\nG01X30000Y30000\nM16\nM30\n"
        )
        f = tmp_path / "full.drl"
        f.write_text(content)
        tools = parse_slot_file(str(f), coord_format="3.3")
        assert tools['1']['slots'] == [((10.0, 10.0), (30.0, 30.0))]


class TestModalCoordinatesAcrossToolChangeH2:
    """H2: модальный контекст координат сохраняется через смену инструмента.
    Раньше last_x/last_y сбрасывались на каждой T-команде, и первое отверстие
    нового инструмента, использующее модальную координату, терялось."""

    def test_modal_x_across_tool_change(self, tmp_path):
        """T2 начинается с Y-only — X наследуется от последнего отверстия T1."""
        content = (
            "M48\nMETRIC\nFORMAT,3.3\nT1C0.5\nT2C1.0\n%\n"
            "T1\nX10000Y20000\n"
            "T2\nY40000\n"
            "M30\n"
        )
        f = tmp_path / "modal_tool_change.drl"
        f.write_text(content)
        tools = parse_excellon_file(str(f), coord_format="3.3")
        assert len(tools['2']['holes']) == 1
        # X унаследован от T1 (10.0), Y из текущей строки (40.0)
        assert tools['2']['holes'][0] == (10.0, 40.0)

    def test_modal_y_across_tool_change(self, tmp_path):
        """T2 начинается с X-only — Y наследуется от последнего отверстия T1."""
        content = (
            "M48\nMETRIC\nFORMAT,3.3\nT1C0.5\nT2C1.0\n%\n"
            "T1\nX10000Y20000\n"
            "T2\nX50000\n"
            "M30\n"
        )
        f = tmp_path / "modal_tool_change2.drl"
        f.write_text(content)
        tools = parse_excellon_file(str(f), coord_format="3.3")
        assert len(tools['2']['holes']) == 1
        assert tools['2']['holes'][0] == (50.0, 20.0)

    def test_partial_coord_without_modal_context_is_skipped(self, tmp_path, caplog):
        """Если модального контекста нет (первое отверстие T1 — X-only без
        предшествующих Y), отверстие пропускается с warning, как и раньше."""
        content = (
            "M48\nMETRIC\nFORMAT,3.3\nT1C0.5\n%\n"
            "T1\nX10000\n"
            "M30\n"
        )
        f = tmp_path / "no_modal.drl"
        f.write_text(content)
        with caplog.at_level("WARNING", logger="core.parser"):
            tools = parse_excellon_file(str(f), coord_format="3.3")
        assert tools['1']['holes'] == []
        assert any("incomplete coordinates" in rec.message for rec in caplog.records)

    def test_existing_pattern_still_works(self, tmp_path):
        """Регрессия: классический файл с полными координатами обрабатывается
        так же, как и раньше."""
        content = (
            "M48\nMETRIC\nFORMAT,3.3\nT1C0.5\nT2C1.0\n%\n"
            "T1\nX10000Y20000\nX30000Y40000\n"
            "T2\nX50000Y60000\n"
            "M30\n"
        )
        f = tmp_path / "classic.drl"
        f.write_text(content)
        tools = parse_excellon_file(str(f), coord_format="3.3")
        # Координаты T1: после TSP порядок может измениться, но множество то же
        assert set(tools['1']['holes']) == {(10.0, 20.0), (30.0, 40.0)}
        assert tools['2']['holes'] == [(50.0, 60.0)]


class TestToolDefinitionVsCoordinateLineM1:
    """M1: строка-определение инструмента не должна давать фантомное отверстие.

    Раньше парсер обрабатывал каждую строку через два независимых `if`:
    `if line.startswith('T'):` и `if current_tool and ('X' in line or ...):` —
    нестандартные постпроцессоры, кладущие T<N>C<D>X<x>Y<y> в одну строку,
    давали лишнее отверстие в координатах из определения.
    """

    def test_inline_tool_def_with_coords_no_phantom_hole(self, tmp_path):
        """T02C1.6X1000Y1000 должен только зарегистрировать инструмент."""
        content = (
            "M48\nMETRIC\nFORMAT,3.3\n%\n"
            "T1C0.5X1000Y2000\n"   # ← нестандартная строка с координатами
            "X3000Y4000\n"          # ← реальное отверстие
            "M30\n"
        )
        f = tmp_path / "inline.drl"
        f.write_text(content)
        tools = parse_excellon_file(str(f), coord_format="3.3")
        # Должно быть ровно ОДНО отверстие — из второй строки.
        # Если бы M1 не был исправлен, получили бы 2: (1.0, 2.0) и (3.0, 4.0).
        assert tools['1']['holes'] == [(3.0, 4.0)]

    def test_separate_t_and_coord_lines_still_works(self, tmp_path):
        """Регрессия: стандартное разделение T и координатных строк работает."""
        content = (
            "M48\nMETRIC\nFORMAT,3.3\nT1C0.5\n%\n"
            "T1\n"
            "X1000Y2000\n"
            "X3000Y4000\n"
            "M30\n"
        )
        f = tmp_path / "standard.drl"
        f.write_text(content)
        tools = parse_excellon_file(str(f), coord_format="3.3")
        assert set(tools['1']['holes']) == {(1.0, 2.0), (3.0, 4.0)}

    def test_multiple_inline_tool_defs(self, tmp_path):
        """Несколько инструментов с inline-координатами + реальные отверстия."""
        content = (
            "M48\nMETRIC\nFORMAT,3.3\n%\n"
            "T1C0.5X1000Y1000\n"  # фантом не должен попасть
            "X5000Y5000\n"          # реальное отверстие T1
            "T2C1.0X2000Y2000\n"  # фантом не должен попасть
            "X7000Y7000\n"          # реальное отверстие T2
            "M30\n"
        )
        f = tmp_path / "multi_inline.drl"
        f.write_text(content)
        tools = parse_excellon_file(str(f), coord_format="3.3")
        assert tools['1']['holes'] == [(5.0, 5.0)]
        assert tools['2']['holes'] == [(7.0, 7.0)]


class TestStableSortingM3:
    """M3: при одинаковых диаметрах сортировка инструментов должна быть
    детерминированной — tie-breaker по числовому T-номеру."""

    def test_same_diameter_sorted_by_tool_number(self, tmp_path):
        """T1 и T3 с одинаковым диаметром: в результате T1 идёт раньше T3."""
        # Намеренно объявляем T3 раньше T1 в заголовке, чтобы Python dict
        # без tie-breaker'а мог дать недетерминированный порядок при равенстве.
        content = (
            "M48\nMETRIC\nFORMAT,3.3\n"
            "T3C0.8\nT1C0.8\nT2C1.5\n%\n"
            "T3\nX1000Y1000\n"
            "T1\nX2000Y2000\n"
            "T2\nX3000Y3000\n"
            "M30\n"
        )
        f = tmp_path / "same_diam.drl"
        f.write_text(content)
        tools = parse_excellon_file(str(f), coord_format="3.3")
        keys_in_order = list(tools.keys())
        # Среди T1/T3 (оба 0.8мм) T1 должен идти раньше T3.
        # T2 (1.5мм) — последним.
        assert keys_in_order.index('1') < keys_in_order.index('3')
        assert keys_in_order[-1] == '2'

    def test_different_diameters_still_sorted_by_diameter(self, tmp_path):
        """Регрессия: основная сортировка по диаметру не сломана."""
        content = (
            "M48\nMETRIC\nFORMAT,3.3\nT1C2.0\nT2C0.5\nT3C1.0\n%\n"
            "T1\nX1000Y1000\n"
            "T2\nX2000Y2000\n"
            "T3\nX3000Y3000\n"
            "M30\n"
        )
        f = tmp_path / "diff_diam.drl"
        f.write_text(content)
        tools = parse_excellon_file(str(f), coord_format="3.3")
        diameters = [data['diameter'] for data in tools.values()]
        assert diameters == sorted(diameters)
        # T2 (0.5) → T3 (1.0) → T1 (2.0)
        assert list(tools.keys()) == ['2', '3', '1']

    def test_leading_zeros_in_tool_number_handled(self, tmp_path):
        """T01, T02, T10 (с ведущими нулями) сортируются как 1, 2, 10
        при равных диаметрах, а не лексикографически (где '10' < '2')."""
        content = (
            "M48\nMETRIC\nFORMAT,3.3\n"
            "T01C1.0\nT02C1.0\nT10C1.0\n%\n"
            "T01\nX1000Y1000\n"
            "T02\nX2000Y2000\n"
            "T10\nX3000Y3000\n"
            "M30\n"
        )
        f = tmp_path / "leading_zeros.drl"
        f.write_text(content)
        tools = parse_excellon_file(str(f), coord_format="3.3")
        keys = list(tools.keys())
        # Ключи должны идти в численном порядке: T01 → T02 → T10.
        # Без int()-tie-breaker'а лексикографически было бы T01 → T10 → T02.
        assert keys.index('01') < keys.index('02') < keys.index('10')


class TestSlotHeaderBodyKeyMismatchM4:
    """M4: рассинхронизация форматирования T-номеров между header и body
    в slot-парсере. До фикса header_tools использовал ключ "T01", а в body
    встречалось "T1" — header_tools.get('1', 0.0) промахивался и диаметр
    тихо падал в 0.0."""

    def test_header_t01_body_t1(self, tmp_path):
        """Заголовок объявляет T01 с диаметром 1.5; body использует T1.
        Диаметр должен корректно дотянуться до результирующего инструмента."""
        content = (
            "M48\nMETRIC\nFORMAT,3.3\n"
            "T01C1.5\n%\n"
            "T1\nG00X10000Y10000\nM15\nG01X30000Y30000\nM16\n"
            "M30\n"
        )
        f = tmp_path / "mismatch1.drl"
        f.write_text(content)
        tools = parse_slot_file(str(f), coord_format="3.3")
        # Ключ tools — строка из body ("1"), но диаметр взят из header ("01")
        assert tools['1']['diameter'] == 1.5

    def test_header_t1_body_t01(self, tmp_path):
        """Обратный случай: T1 в заголовке, T01 в теле."""
        content = (
            "M48\nMETRIC\nFORMAT,3.3\n"
            "T1C0.8\n%\n"
            "T01\nG00X10000Y10000\nM15\nG01X30000Y30000\nM16\n"
            "M30\n"
        )
        f = tmp_path / "mismatch2.drl"
        f.write_text(content)
        tools = parse_slot_file(str(f), coord_format="3.3")
        assert tools['01']['diameter'] == 0.8

    def test_consistent_keys_still_work(self, tmp_path):
        """Регрессия: если форматирование одинаковое, всё работает как раньше."""
        content = (
            "M48\nMETRIC\nFORMAT,3.3\n"
            "T01C2.0\n%\n"
            "T01\nG00X10000Y10000\nM15\nG01X30000Y30000\nM16\n"
            "M30\n"
        )
        f = tmp_path / "consistent.drl"
        f.write_text(content)
        tools = parse_slot_file(str(f), coord_format="3.3")
        assert tools['01']['diameter'] == 2.0

    def test_multiple_tools_with_mixed_padding(self, tmp_path):
        """Несколько инструментов с разной шириной ведущих нулей."""
        content = (
            "M48\nMETRIC\nFORMAT,3.3\n"
            "T1C0.5\nT02C1.0\n%\n"
            "T01\nG00X10000Y10000\nM15\nG01X20000Y20000\nM16\n"
            "T2\nG00X30000Y30000\nM15\nG01X40000Y40000\nM16\n"
            "M30\n"
        )
        f = tmp_path / "mixed.drl"
        f.write_text(content)
        tools = parse_slot_file(str(f), coord_format="3.3")
        # T01 в body должен подхватить диаметр от T1 в заголовке
        assert tools['01']['diameter'] == 0.5
        # T2 в body должен подхватить диаметр от T02 в заголовке
        assert tools['2']['diameter'] == 1.0
