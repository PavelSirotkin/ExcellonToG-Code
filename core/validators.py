"""
Валидаторы входных данных приложения.
"""
import os
import re
from typing import Dict, Any, List, Tuple


# ==========================================================
# Парсинг чисел (с поддержкой запятой как разделителя)
# ==========================================================

def parse_decimal(s, default=None):
    """Преобразовать строку в float, принимая запятую как разделитель ('0,3' -> 0.3)."""
    try:
        return float(str(s).replace(',', '.').strip())
    except (ValueError, AttributeError):
        return default


def parse_int(s, default=None):
    """Преобразовать строку в int через float (принимает запятую: '4,0' -> 4)."""
    v = parse_decimal(s, None)
    return int(v) if v is not None else default


# ==========================================================
# Валидация формата координат
# ==========================================================

def validate_coordinate_format(format_str: str) -> bool:
    """Проверка формата координат (например "3.3", "4.2", "2.4", "Exp").
    Допустимы: N.N (обе части > 0) или специальное значение "Exp" —
    координаты с явной десятичной точкой."""
    if not format_str:
        return False
    if format_str == "Exp":
        return True
    match = re.match(r'^(\d+)\.(\d+)$', format_str)
    if not match:
        return False
    integer_part = int(match.group(1))
    fractional_part = int(match.group(2))
    return integer_part > 0 and fractional_part > 0


# ==========================================================
# Валидация параметров G-code
# ==========================================================

def validate_gcode_params(params: Dict[str, float]) -> List[str]:
    """Комплексная проверка параметров G-code.
    Возвращает список ошибок (пустой = всё валидно)."""
    errors = []
    safe_z = params.get('safe_z')
    drill_z = params.get('drill_z')
    feed_rate = params.get('feed_rate')
    rapid_rate = params.get('rapid_rate')
    park_z = params.get('park_z')
    mill_feed = params.get('mill_feed')

    if safe_z is not None:
        if safe_z <= 0:
            errors.append("Безопасная Z должна быть > 0")
    if drill_z is not None:
        if drill_z >= 0:
            errors.append("Глубина сверления должна быть < 0")
    if feed_rate is not None:
        if feed_rate <= 0:
            errors.append("Подача должна быть > 0")
    if rapid_rate is not None:
        if rapid_rate <= 0:
            errors.append("Холостой ход должен быть > 0")
    if mill_feed is not None:
        if mill_feed <= 0:
            errors.append("Подача фрезы должна быть > 0")
    if park_z is not None and safe_z is not None:
        if park_z < safe_z:
            errors.append("Парковка Z должна быть >= Безопасной Z")

    return errors


def validate_gcode_params_strict(params: Dict[str, float]) -> Tuple[bool, str]:
    """Строгая валидация с возвратом (успех, сообщение)."""
    errors = validate_gcode_params(params)
    if errors:
        return False, "\n".join(errors)
    return True, "OK"


# ==========================================================
# Валидация файлов
# ==========================================================

def validate_file_exists(filename: str) -> bool:
    """Проверка что файл существует."""
    return filename is not None and os.path.isfile(filename)


def validate_file_readable(filename: str) -> bool:
    """Проверка что файл существует и доступен для чтения."""
    if not validate_file_exists(filename):
        return False
    try:
        with open(filename, 'r', encoding='utf-8', errors='ignore') as f:
            f.read(1)
        return True
    except (IOError, PermissionError):
        return False


def validate_excellon_header(filename: str) -> bool:
    """Проверка что файл начинается с заголовка Excellon.
    Ищет M48, %, METRIC, G90 в первых строках."""
    try:
        with open(filename, 'r', encoding='utf-8', errors='ignore') as f:
            for _ in range(5):
                line = f.readline().strip()
                if not line:
                    continue
                if any(marker in line.upper() for marker in ['M48', 'METRIC', 'G90']):
                    return True
                if line.startswith('%'):
                    return True
        return False
    except (IOError, UnicodeDecodeError):
        return False


def validate_slot_file_structure(filename: str) -> bool:
    """Проверка базовой структуры файла слотов.
    Должен содержать T<n>, G00, M15, G01, M16."""
    try:
        with open(filename, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        has_tool = bool(re.search(r'^T\d+$', content, re.MULTILINE))
        has_slot = 'M15' in content and 'M16' in content
        return has_tool and has_slot
    except (IOError, UnicodeDecodeError):
        return False


# ==========================================================
# Валидация данных инструментов
# ==========================================================

def validate_tool_data(tool_dict: Dict[str, Any]) -> List[str]:
    """Проверка структуры данных инструмента.
    Ожидается: {diameter: float, holes: list или slots: list, visible: bool}."""
    errors = []

    if 'diameter' not in tool_dict:
        errors.append("Отсутствует 'diameter'")
    else:
        d = tool_dict['diameter']
        if not isinstance(d, (int, float)):
            errors.append(f"diameter должен быть числом, получен {type(d)}")
        elif d <= 0:
            errors.append(f"diameter должен быть > 0, получен {d}")

    if 'holes' in tool_dict:
        holes = tool_dict['holes']
        if not isinstance(holes, list):
            errors.append("'holes' должен быть списком")
        else:
            for i, h in enumerate(holes):
                if not isinstance(h, (list, tuple)) or len(h) != 2:
                    errors.append(f"hole[{i}] должен быть (x, y)")
                else:
                    if not all(isinstance(c, (int, float)) for c in h):
                        errors.append(f"hole[{i}] координаты должны быть числами")

    if 'slots' in tool_dict:
        slots = tool_dict['slots']
        if not isinstance(slots, list):
            errors.append("'slots' должен быть списком")
        else:
            for i, s in enumerate(slots):
                if not isinstance(s, (list, tuple)) or len(s) != 2:
                    errors.append(f"slot[{i}] должен быть ((x1,y1), (x2,y2))")

    if 'visible' in tool_dict:
        if not isinstance(tool_dict['visible'], bool):
            errors.append("'visible' должен быть bool")

    return errors


def validate_tools_dict(tools: Dict[str, Any]) -> List[str]:
    """Проверка полного словаря инструментов.
    Ключи — номера инструментов, значения — dict с данными."""
    errors = []
    if not isinstance(tools, dict):
        return ["tools должен быть словарём"]
    for tool_key, tool_data in tools.items():
        if not isinstance(tool_data, dict):
            errors.append(f"Инструмент {tool_key}: данные не являются словарём")
            continue
        tool_errors = validate_tool_data(tool_data)
        for err in tool_errors:
            errors.append(f"Инструмент {tool_key}: {err}")
    return errors


# ==========================================================
# Валидация точек и координат
# ==========================================================

def validate_coordinate(value: float, min_val: float = -300, max_val: float = 300) -> bool:
    """Проверка что координата в допустимых пределах."""
    return isinstance(value, (int, float)) and min_val <= value <= max_val


def validate_points_list(points: List[Tuple[float, float]],
                          min_val: float = -300, max_val: float = 300) -> List[str]:
    """Проверка списка точек."""
    errors = []
    if not isinstance(points, list):
        return ["points должен быть списком"]
    for i, p in enumerate(points):
        if not isinstance(p, (list, tuple)) or len(p) != 2:
            errors.append(f"point[{i}] должен быть (x, y)")
        else:
            for j, coord in enumerate(p):
                if not validate_coordinate(coord, min_val, max_val):
                    errors.append(f"point[{i}][{j}] = {coord} вне диапазона [{min_val}, {max_val}]")
    return errors


# ==========================================================
# Валидация G-code сегментов (для визуализатора)
# ==========================================================

VALID_SEGMENT_TYPES = {'rapid', 'feed', 'drill_down', 'drill_up', 'slot_h'}


def validate_gcode_segment(segment: Dict[str, Any]) -> List[str]:
    """Проверка одного сегмента G-code."""
    errors = []
    required_keys = {'type', 'x0', 'y0', 'z0', 'x1', 'y1', 'z1'}
    missing = required_keys - set(segment.keys())
    if missing:
        errors.append(f"Отсутствуют ключи: {missing}")
        return errors

    if segment['type'] not in VALID_SEGMENT_TYPES:
        errors.append(f"Неизвестный тип сегмента: {segment['type']}")

    for key in ['x0', 'y0', 'z0', 'x1', 'y1', 'z1']:
        if not isinstance(segment[key], (int, float)):
            errors.append(f"{key} должен быть числом")

    return errors


def validate_gcode_segments(segments: List[Dict[str, Any]]) -> List[str]:
    """Проверка списка сегментов G-code."""
    errors = []
    if not isinstance(segments, list):
        return ["segments должен быть списком"]
    for i, seg in enumerate(segments):
        seg_errors = validate_gcode_segment(seg)
        for err in seg_errors:
            errors.append(f"segment[{i}]: {err}")
    return errors


# ==========================================================
# Валидация контура платы (Gerber outline)
# ==========================================================

def validate_outline_segments(segments: List[Dict]) -> List[str]:
    """Проверка сегментов контура платы.
    Возвращает список ошибок (пустой = всё валидно)."""
    errors = []
    if not segments:
        errors.append("Контур пуст")
        return errors
    if len(segments) < 3:
        errors.append("Контур должен содержать минимум 3 сегмента")
        return errors
    return errors


def validate_holes_within_outline(tools_drill, tools_slots, outline_polygon) -> List[Tuple[str, Tuple[float, float]]]:
    """
    Проверка, что отверстия и слоты лежат внутри контура платы.

    Args:
        tools_drill: dict сверл {tool_num: {diameter, holes: [(x,y), ...]}}
        tools_slots: dict слотов {tool_num: {diameter, slots: [((x1,y1), (x2,y2)), ...]}}
        outline_polygon: список точек контура [(x,y), ...]

    Returns:
        Список кортежей (описание, (x, y)) для каждого нарушения
    """
    from core.polygon_ops import point_in_polygon

    violations = []

    if not outline_polygon or len(outline_polygon) < 3:
        return violations

    # Проверяем отверстия
    if tools_drill:
        for tool_num, data in tools_drill.items():
            if not data.get('visible', True):
                continue
            for hole in data.get('holes', []):
                x, y = hole
                if not point_in_polygon((x, y), outline_polygon):
                    violations.append((f"Отверстие T{tool_num} ({x:.2f}, {y:.2f})", (x, y)))

    # Проверяем слоты (оба конца)
    if tools_slots:
        for tool_num, data in tools_slots.items():
            if not data.get('visible', True):
                continue
            for slot in data.get('slots', []):
                (x1, y1), (x2, y2) = slot
                if not point_in_polygon((x1, y1), outline_polygon):
                    violations.append((f"Слот T{tool_num} начало ({x1:.2f}, {y1:.2f})", (x1, y1)))
                if not point_in_polygon((x2, y2), outline_polygon):
                    violations.append((f"Слот T{tool_num} конец ({x2:.2f}, {y2:.2f})", (x2, y2)))

    return violations


def validate_outline_params(outline_params: Dict[str, Any], drill_z: float) -> List[str]:
    """
    Проверка параметров обрезки по контуру.

    Args:
        outline_params: {tool_diameter, depth_per_pass, n_tabs, tab_width, tab_height}
        drill_z: глубина сверления (отрицательное число)

    Returns:
        Список ошибок
    """
    errors = []

    tool_diameter = outline_params.get('tool_diameter', 0)
    depth_per_pass = outline_params.get('depth_per_pass', 0)
    n_tabs = outline_params.get('n_tabs', 0)
    tab_width = outline_params.get('tab_width', 0)
    tab_height = outline_params.get('tab_height', 0)

    if tool_diameter <= 0:
        errors.append("Диаметр фрезы должен быть > 0")

    if depth_per_pass <= 0:
        errors.append("Глубина прохода должна быть > 0")

    if n_tabs < 0 or n_tabs > 50:
        errors.append("Количество tabs должно быть от 0 до 50")

    if tab_width < 0:
        errors.append("Ширина tab должна быть >= 0")

    if tab_height < 0:
        errors.append("Высота tab должна быть >= 0")

    if drill_z >= 0:
        errors.append("Глубина сверления должна быть отрицательной")
    elif tab_height > abs(drill_z):
        errors.append(f"Высота tab ({tab_height}) не может превышать глубину сверления ({abs(drill_z)})")

    return errors
