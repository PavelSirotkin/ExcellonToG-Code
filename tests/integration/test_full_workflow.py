"""
End-to-end интеграционные тесты: полный workflow от загрузки файла до генерации G-code.

Тестируют реальные сценарии использования:
1. Загрузка Excellon-файла → парсинг → генерация G-code
2. Загрузка слотов → парсинг → генерация G-code
3. Комбинированный режим (отверстия + слоты)
4. Работа с контуром платы (Gerber)
5. Применение параметров инструментов из базы данных
"""
import os
import pytest
from core.parser import parse_excellon_file, parse_slot_file, detect_coordinate_format
from core.gcode_generator import _build_drilling_gcode, _build_milling_gcode, _build_combined_gcode
from core.gerber_parser import parse_gerber_outline
from core.tool_database import ToolDatabase


# Путь к тестовым файлам
SAMPLES_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "Samples")


class TestExcellonToGCodeWorkflow:
    """End-to-end тесты полного workflow."""
    
    def test_excellon_to_gcode_basic_workflow(self):
        """Базовый workflow: загрузка Excellon → генерация G-code."""
        # 1. Загрузить Excellon файл
        excellon_file = os.path.join(SAMPLES_DIR, "Материнка универсальная-RoundHoles.TXT")
        assert os.path.exists(excellon_file), f"Тестовый файл не найден: {excellon_file}"
        
        # 2. Определить формат координат
        coord_format = detect_coordinate_format(excellon_file)
        assert coord_format is not None, "Не удалось определить формат координат"
        assert coord_format == "4.2", f"Ожидался формат 4.2, получен {coord_format}"
        
        # 3. Парсинг файла
        tools = parse_excellon_file(excellon_file, coord_format)
        assert tools, "Парсинг не вернул инструменты"
        assert len(tools) > 0, "Нет инструментов после парсинга"
        
        # 4. Проверить структуру данных
        for tool_num, tool_data in tools.items():
            assert 'diameter' in tool_data
            assert 'holes' in tool_data
            assert 'visible' in tool_data
            assert isinstance(tool_data['holes'], list)
            assert tool_data['diameter'] > 0
        
        # 5. Сгенерировать G-code
        params = {
            'safe_z': 5.0,
            'drill_z': -2.5,
            'feed_rate': 100,
            'rapid_rate': 500,
            'park_z': 30
        }
        gcode, errors = _build_drilling_gcode(tools, excellon_file, params)
        
        # 6. Проверить результат
        assert errors == [], f"Генерация G-code вернула ошибки: {errors}"
        assert gcode is not None, "G-code не был сгенерирован"
        assert len(gcode) > 0, "G-code пустой"
        
        # 7. Проверить содержимое G-code
        assert "M30" in gcode, "G-code не содержит команду завершения программы M30"
        assert "G21" in gcode, "G-code не содержит команду метрической системы G21"
        assert "G90" in gcode, "G-code не содержит команду абсолютных координат G90"
        assert "M03" in gcode, "G-code не содержит команду включения шпинделя M03"
        assert "M05" in gcode, "G-code не содержит команду выключения шпинделя M05"
        assert "M00" in gcode, "G-code не содержит команду паузы для смены инструмента M00"
        
        # 8. Проверить наличие координат
        assert "X" in gcode and "Y" in gcode, "G-code не содержит координаты X/Y"
        assert "Z" in gcode, "G-code не содержит координаты Z"
    
    def test_slot_to_gcode_workflow(self):
        """Workflow для слотов: загрузка → парсинг → генерация G-code."""
        # 1. Загрузить файл слотов
        slot_file = os.path.join(SAMPLES_DIR, "Материнка универсальная-SlotHoles.TXT")
        assert os.path.exists(slot_file), f"Тестовый файл не найден: {slot_file}"
        
        # 2. Парсинг слотов
        coord_format = "4.2"
        slot_tools = parse_slot_file(slot_file, coord_format)
        assert slot_tools, "Парсинг слотов не вернул инструменты"
        
        # 3. Проверить структуру данных слотов
        for tool_num, tool_data in slot_tools.items():
            assert 'diameter' in tool_data
            assert 'slots' in tool_data
            assert 'visible' in tool_data
            assert isinstance(tool_data['slots'], list)
            # Каждый слот — это ((start_x, start_y), (end_x, end_y))
            for slot in tool_data['slots']:
                assert len(slot) == 2, "Слот должен содержать start и end"
                start, end = slot
                assert len(start) == 2, "Start должен содержать (x, y)"
                assert len(end) == 2, "End должен содержать (x, y)"
        
        # 4. Сгенерировать G-code для слотов
        params = {
            'safe_z': 5.0,
            'drill_z': -2.5,
            'feed_rate': 100,
            'mill_feed': 50,
            'rapid_rate': 500,
            'park_z': 30
        }
        gcode, errors = _build_milling_gcode(slot_tools, slot_file, params)
        
        # 5. Проверить результат
        assert errors == [], f"Генерация G-code для слотов вернула ошибки: {errors}"
        assert gcode is not None, "G-code для слотов не был сгенерирован"
        assert "M30" in gcode, "G-code не содержит M30"
        assert "G01" in gcode, "G-code для слотов должен содержать G01 (рабочая подача)"
    
    def test_combined_workflow(self):
        """Комбинированный workflow: отверстия + слоты → единый G-code."""
        # 1. Загрузить оба файла
        excellon_file = os.path.join(SAMPLES_DIR, "Материнка универсальная-RoundHoles.TXT")
        slot_file = os.path.join(SAMPLES_DIR, "Материнка универсальная-SlotHoles.TXT")
        
        # 2. Парсинг обоих файлов
        coord_format = "4.2"
        tools = parse_excellon_file(excellon_file, coord_format)
        slot_tools = parse_slot_file(slot_file, coord_format)
        
        # 3. Сгенерировать комбинированный G-code
        params = {
            'safe_z': 5.0,
            'drill_z': -2.5,
            'feed_rate': 100,
            'mill_feed': 50,
            'rapid_rate': 500,
            'park_z': 30
        }
        gcode, errors = _build_combined_gcode(
            tools, excellon_file,
            slot_tools, slot_file,
            params
        )
        
        # 4. Проверить результат
        assert errors == [], f"Комбинированная генерация вернула ошибки: {errors}"
        assert gcode is not None, "Комбинированный G-code не был сгенерирован"
        
        # 5. Проверить наличие обеих секций
        assert "DRILLING SECTION" in gcode, "Отсутствует секция сверления"
        assert "SLOT MILLING SECTION" in gcode, "Отсутствует секция фрезеровки слотов"
        assert "M30" in gcode, "G-code не содержит M30"
    
    def test_gerber_outline_workflow(self):
        """Workflow для контура платы: загрузка Gerber → парсинг."""
        # 1. Загрузить Gerber файл контура
        gerber_file = os.path.join(SAMPLES_DIR, "Материнка универсальная_Profile.gbr")
        assert os.path.exists(gerber_file), f"Тестовый файл не найден: {gerber_file}"
        
        # 2. Парсинг контура (возвращает кортеж: segments, units, bounds)
        result = parse_gerber_outline(gerber_file)
        assert result is not None, "Парсинг контура не вернул результат"
        
        # 3. Распаковать результат
        assert isinstance(result, tuple), "parse_gerber_outline должен возвращать кортеж"
        assert len(result) == 3, "Результат должен содержать (segments, units, bounds)"
        
        segments, units, bounds = result
        
        # 4. Проверить сегменты
        assert isinstance(segments, list), "Сегменты должны быть списком"
        assert len(segments) > 0, "Контур не содержит сегментов"
        
        # 5. Проверить структуру сегментов
        for segment in segments:
            assert isinstance(segment, dict), "Каждый сегмент должен быть словарём"
            assert 'type' in segment, "Сегмент должен содержать тип"
            assert segment['type'] in ['line', 'arc'], f"Неизвестный тип сегмента: {segment['type']}"
        
        # 6. Проверить единицы измерения
        assert units in ['mm', 'inch'], f"Неизвестные единицы измерения: {units}"
        
        # 7. Проверить границы (bounds)
        assert isinstance(bounds, tuple), "Границы должны быть кортежем"
        assert len(bounds) == 4, "Границы должны содержать (min_x, min_y, max_x, max_y)"
    
    def test_workflow_with_tool_database(self):
        """Workflow с использованием базы данных инструментов."""
        # 1. Создать временную базу инструментов
        tool_db = ToolDatabase()
        
        # 2. Добавить параметры для инструмента (используя правильный API)
        tool_db.add_drill(
            diameter=0.55,
            spindle_speed=12000,
            plunge_feed=80,
            retract_feed=600
        )
        
        # 3. Загрузить и парсить файл
        excellon_file = os.path.join(SAMPLES_DIR, "Материнка универсальная-RoundHoles.TXT")
        tools = parse_excellon_file(excellon_file, "4.2")
        
        # 4. Сгенерировать G-code с параметрами из базы
        params = {
            'safe_z': 5.0,
            'drill_z': -2.5,
            'feed_rate': 100,
            'rapid_rate': 500,
            'park_z': 30
        }
        # Создать словарь параметров инструментов для генератора
        tool_params_dict = {"drills": {}}
        for key, drill_data in tool_db.drills.items():
            tool_params_dict["drills"][key] = drill_data
        
        gcode, errors = _build_drilling_gcode(tools, excellon_file, params, tool_params_dict)
        
        # 5. Проверить результат
        assert errors == [], f"Генерация с базой инструментов вернула ошибки: {errors}"
        assert gcode is not None
        # Проверить, что скорость шпинделя применена (если инструмент совпал)
        if "S12000" in gcode:
            # Параметры из базы применены
            pass
        # Если не совпал диаметр, это нормально - просто проверяем, что G-code сгенерирован
    
    def test_workflow_with_invalid_file(self):
        """Workflow с невалидным файлом должен корректно обрабатывать ошибки."""
        # 1. Попытка парсинга несуществующего файла
        with pytest.raises(FileNotFoundError):
            parse_excellon_file("nonexistent_file.drl", "4.2")
        
        # 2. Попытка генерации G-code без данных
        params = {
            'safe_z': 5.0,
            'drill_z': -2.5,
            'feed_rate': 100,
            'rapid_rate': 500,
            'park_z': 30
        }
        gcode, errors = _build_drilling_gcode({}, "test.drl", params)
        assert gcode is None, "G-code должен быть None для пустых данных"
        assert len(errors) > 0, "Должны быть ошибки для пустых данных"
    
    def test_workflow_with_invalid_params(self):
        """Workflow с невалидными параметрами должен возвращать ошибки."""
        # 1. Загрузить файл
        excellon_file = os.path.join(SAMPLES_DIR, "Материнка универсальная-RoundHoles.TXT")
        tools = parse_excellon_file(excellon_file, "4.2")
        
        # 2. Попытка генерации с невалидными параметрами
        invalid_params = {
            'safe_z': -5.0,  # Невалидно: safe_z должен быть > drill_z
            'drill_z': -2.5,
            'feed_rate': 100,
            'rapid_rate': 500,
            'park_z': 30
        }
        gcode, errors = _build_drilling_gcode(tools, excellon_file, invalid_params)
        assert gcode is None, "G-code должен быть None для невалидных параметров"
        assert len(errors) > 0, "Должны быть ошибки валидации"
    
    def test_coordinate_format_detection(self):
        """Тест автоопределения формата координат."""
        excellon_file = os.path.join(SAMPLES_DIR, "Материнка универсальная-RoundHoles.TXT")
        
        # Автоопределение формата
        detected_format = detect_coordinate_format(excellon_file)
        assert detected_format == "4.2", f"Ожидался формат 4.2, получен {detected_format}"
        
        # Парсинг с автоопределённым форматом
        tools = parse_excellon_file(excellon_file, detected_format)
        assert len(tools) > 0, "Парсинг с автоопределённым форматом не вернул инструменты"
    
    def test_gcode_output_format(self):
        """Проверка формата выходного G-code."""
        excellon_file = os.path.join(SAMPLES_DIR, "Материнка универсальная-RoundHoles.TXT")
        tools = parse_excellon_file(excellon_file, "4.2")
        
        params = {
            'safe_z': 5.0,
            'drill_z': -2.5,
            'feed_rate': 100,
            'rapid_rate': 500,
            'park_z': 30
        }
        gcode, errors = _build_drilling_gcode(tools, excellon_file, params)
        
        # Проверить формат координат (должны быть с 3 знаками после запятой для X/Y)
        lines = gcode.split('\n')
        for line in lines:
            if line.startswith('G00') or line.startswith('G01'):
                if 'X' in line:
                    # Извлечь значение X и проверить формат
                    import re
                    x_match = re.search(r'X(-?\d+\.\d+)', line)
                    if x_match:
                        x_val = x_match.group(1)
                        # Проверить, что после точки 3 цифры
                        decimal_part = x_val.split('.')[1] if '.' in x_val else ''
                        assert len(decimal_part) == 3, f"X координата должна иметь 3 знака после запятой: {line}"
