"""
Парсинг Excellon-файлов (отверстия и слоты).
"""
import logging
import re
from core.tsp_optimizer import nearest_neighbor_tsp, nearest_neighbor_tsp_slots
import core.config as cfg

logger = logging.getLogger(__name__)


def detect_coordinate_format(filename):
    """Автоопределение формата координат из заголовка Excellon файла.
    Ищет слово 'format' (без учёта регистра) и извлекает формат вида N.N или N:N.
    Возвращает строку формата (например '3.3') или None если не найден."""
    try:
        # Сначала пробуем UTF-8
        with open(filename, 'r', encoding='utf-8') as f:
            for _ in range(20):
                line = f.readline()
                if not line:
                    break
                if re.search(r'format', line, re.IGNORECASE):
                    m = re.search(r'(\d)[.:,](\d)', line)
                    if m:
                        return f"{m.group(1)}.{m.group(2)}"
    except UnicodeDecodeError:
        # Если не получилось, пробуем latin-1
        logger.warning("UTF-8 decode failed for %s, trying latin-1", filename)
        try:
            with open(filename, 'r', encoding='latin-1') as f:
                for _ in range(20):
                    line = f.readline()
                    if not line:
                        break
                    if re.search(r'format', line, re.IGNORECASE):
                        m = re.search(r'(\d)[.:,](\d)', line)
                        if m:
                            return f"{m.group(1)}.{m.group(2)}"
        except (OSError, UnicodeDecodeError) as e:
            logger.warning("detect_coordinate_format: cannot read %s: %s", filename, e)
    except (OSError, PermissionError, FileNotFoundError) as e:
        logger.warning("detect_coordinate_format: cannot read %s: %s", filename, e)
    return None


def is_excellon_file(filename):
    """Проверка, является ли файл Excellon-формата."""
    try:
        # Сначала пробуем UTF-8
        with open(filename, 'r', encoding='utf-8') as f:
            for _ in range(cfg.EXCELLON_HEADER_LINES):
                line = f.readline()
                if not line:
                    break
                line = line.strip()
                if line.startswith('M48') or line.startswith('%') or 'METRIC' in line or 'G90' in line:
                    return True
        return False
    except UnicodeDecodeError:
        # Если не получилось, пробуем latin-1
        logger.warning("UTF-8 decode failed for %s, trying latin-1", filename)
        try:
            with open(filename, 'r', encoding='latin-1') as f:
                for _ in range(cfg.EXCELLON_HEADER_LINES):
                    line = f.readline()
                    if not line:
                        break
                    line = line.strip()
                    if line.startswith('M48') or line.startswith('%') or 'METRIC' in line or 'G90' in line:
                        return True
            return False
        except (OSError, UnicodeDecodeError) as e:
            logger.warning("is_excellon_file: cannot read %s: %s", filename, e)
            return False
    except (OSError, PermissionError, FileNotFoundError) as e:
        logger.warning("is_excellon_file: cannot read %s: %s", filename, e)
        return False


def parse_excellon_file(filename, coord_format=None):
    """Парсинг файла круглых отверстий.
    Возвращает dict: {tool_number: {diameter, holes[], visible, var}}"""
    if coord_format is None:
        coord_format = cfg.coordinate_format
    tools = {}
    current_tool = None
    
    # Парсинг формата координат с обработкой ошибок
    try:
        _, format_y = map(int, coord_format.split('.'))
    except (ValueError, AttributeError) as e:
        raise ValueError(
            f"Неверный формат координат '{coord_format}'. "
            f"Ожидается N.N (например, '3.3' или '4.2'). Подробности: {e}"
        )
    
    # Защита от нулевой дробной части
    if format_y == 0:
        raise ValueError(
            f"Неверный формат координат '{coord_format}'. "
            f"Дробная часть должна быть > 0 (например, '3.3', '4.2', но не '3.0')."
        )
    
    last_x = None
    last_y = None
    
    # Чтение файла с правильной обработкой кодировок
    try:
        # Сначала пробуем UTF-8
        with open(filename, 'r', encoding='utf-8') as f:
            content = f.read()
    except UnicodeDecodeError:
        # Если не получилось, пробуем latin-1
        logger.warning("UTF-8 decode failed for %s, trying latin-1", filename)
        try:
            with open(filename, 'r', encoding='latin-1') as f:
                content = f.read()
        except UnicodeDecodeError as e:
            logger.error("Failed to decode file %s with both UTF-8 and latin-1: %s", filename, e)
            raise ValueError(f"Не удалось прочитать файл {filename}: проблема с кодировкой") from e
    except PermissionError as e:
        logger.error("Permission denied reading file %s: %s", filename, e)
        raise PermissionError(f"Нет доступа к файлу {filename}") from e
    except FileNotFoundError as e:
        logger.error("File not found: %s", filename)
        raise FileNotFoundError(f"Файл не найден: {filename}") from e
    except OSError as e:
        logger.error("OS error reading file %s: %s", filename, e)
        raise OSError(f"Ошибка чтения файла {filename}: {e}") from e
    
    # Парсим содержимое построчно
    for line in content.splitlines():
        line = line.strip()
        if not line:
            continue
        if line.startswith('T'):
            tool_number = None
            diameter = 0.0
            tool_match = re.match(r'T(\d+)', line)
            if tool_match:
                tool_number = tool_match.group(1)
            c_match = re.search(r'C([0-9.]+)', line)
            if c_match:
                diameter = float(c_match.group(1))
            if tool_number:
                current_tool = tool_number
                if current_tool not in tools:
                    tools[current_tool] = {
                        'diameter': diameter,
                        'holes': [],
                        'visible': True,
                        'var': None
                    }
                last_x = None
                last_y = None
        if current_tool and ('X' in line or 'Y' in line):
            x_match = re.search(r'X([+-]?\d+)', line)
            y_match = re.search(r'Y([+-]?\d+)', line)
            if x_match:
                last_x = int(x_match.group(1))
            if y_match:
                last_y = int(y_match.group(1))
            # Требуем обе координаты — отверстие без X или Y невалидно
            if last_x is not None and last_y is not None:
                x_mm = last_x / (10 ** format_y)
                y_mm = last_y / (10 ** format_y)
                tools[current_tool]['holes'].append((x_mm, y_mm))
    sorted_tools = dict(sorted(tools.items(), key=lambda item: item[1]['diameter']))
    for tool, data in sorted_tools.items():
        data['holes'] = nearest_neighbor_tsp(data['holes'])
    return sorted_tools


def parse_slot_file(filename, coord_format=None):
    """Парсинг файла слотов.
    Возвращает dict: {tool_number: {diameter, slots[], visible, var}}.
    Каждый слот: ((start_x, start_y), (end_x, end_y))."""
    if coord_format is None:
        coord_format = cfg.coordinate_format
    tools = {}
    current_tool = None
    
    # Парсинг формата координат с обработкой ошибок
    try:
        _, format_y = map(int, coord_format.split('.'))
    except (ValueError, AttributeError) as e:
        raise ValueError(
            f"Неверный формат координат '{coord_format}'. "
            f"Ожидается N.N (например, '3.3' или '4.2'). Подробности: {e}"
        )
    
    # Защита от нулевой дробной части
    if format_y == 0:
        raise ValueError(
            f"Неверный формат координат '{coord_format}'. "
            f"Дробная часть должна быть > 0 (например, '3.3', '4.2', но не '3.0')."
        )
    
    # Чтение файла с правильной обработкой кодировок
    try:
        # Сначала пробуем UTF-8
        with open(filename, 'r', encoding='utf-8') as f:
            content = f.read()
    except UnicodeDecodeError:
        # Если не получилось, пробуем latin-1
        logger.warning("UTF-8 decode failed for %s, trying latin-1", filename)
        try:
            with open(filename, 'r', encoding='latin-1') as f:
                content = f.read()
        except UnicodeDecodeError as e:
            logger.error("Failed to decode file %s with both UTF-8 and latin-1: %s", filename, e)
            raise ValueError(f"Не удалось прочитать файл {filename}: проблема с кодировкой") from e
    except PermissionError as e:
        logger.error("Permission denied reading file %s: %s", filename, e)
        raise PermissionError(f"Нет доступа к файлу {filename}") from e
    except FileNotFoundError as e:
        logger.error("File not found: %s", filename)
        raise FileNotFoundError(f"Файл не найден: {filename}") from e
    except OSError as e:
        logger.error("OS error reading file %s: %s", filename, e)
        raise OSError(f"Ошибка чтения файла {filename}: {e}") from e
    
    lines = [l.strip() for l in content.splitlines()]
    header_tools = {}
    in_header = True
    for line in lines:
        if line == '%':
            in_header = False
            continue
        if in_header:
            tool_match = re.match(r'T(\d+)', line)
            if tool_match:
                tool_number = tool_match.group(1)
                c_match = re.search(r'C([0-9.]+)', line)
                diameter = float(c_match.group(1)) if c_match else 0.0
                header_tools[tool_number] = diameter
    current_tool = None
    i = 0
    while i < len(lines):
        line = lines[i]
        tool_match = re.match(r'^T(\d+)$', line)
        if tool_match:
            tool_number = tool_match.group(1)
            current_tool = tool_number
            if current_tool not in tools:
                diameter = header_tools.get(current_tool, 0.0)
                tools[current_tool] = {
                    'diameter': diameter,
                    'slots': [],
                    'visible': True,
                    'var': None
                }
            i += 1
            continue
        if current_tool and line.startswith('G00'):
            x_match = re.search(r'X([+-]?\d+)', line)
            y_match = re.search(r'Y([+-]?\d+)', line)
            if x_match or y_match:
                g00_x = int(x_match.group(1)) if x_match else None
                g00_y = int(y_match.group(1)) if y_match else None
                if i + 1 < len(lines) and lines[i + 1] == 'M15':
                    if i + 2 < len(lines) and lines[i + 2].startswith('G01'):
                        g01_line = lines[i + 2]
                        g01_x_match = re.search(r'X([+-]?\d+)', g01_line)
                        g01_y_match = re.search(r'Y([+-]?\d+)', g01_line)
                        g01_x = int(g01_x_match.group(1)) if g01_x_match else g00_x
                        g01_y = int(g01_y_match.group(1)) if g01_y_match else g00_y
                        if i + 3 < len(lines) and lines[i + 3] == 'M16':
                            start_x = (g00_x or 0) / (10 ** format_y)
                            start_y = (g00_y or 0) / (10 ** format_y)
                            end_x = (g01_x or 0) / (10 ** format_y)
                            end_y = (g01_y or 0) / (10 ** format_y)
                            tools[current_tool]['slots'].append(
                                ((start_x, start_y), (end_x, end_y))
                            )
                            i += 4
                            continue
            i += 1
            continue
        i += 1
    for tool, data in tools.items():
        if data['slots']:
            data['slots'] = nearest_neighbor_tsp_slots(data['slots'])
    return tools
