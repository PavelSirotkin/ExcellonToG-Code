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


def _scan_zero_suppression(lines):
    """Поиск маркера LZ/TZ в наборе строк заголовка."""
    for line in lines:
        upper = line.upper()
        # Явные модификаторы Excellon: INCH,LZ / METRIC,TZ / METRIC,LZ,000.000 и т.п.
        if re.search(r'\bLZ\b', upper):
            return "LZ"
        if re.search(r'\bTZ\b', upper):
            return "TZ"
        # Альтернативные комментарии. Внимание на инверсии терминологии:
        # "TRAILING ZEROS INCLUDED" = ведущие подавлены  → LZ
        # "LEADING ZEROS INCLUDED"  = конечные подавлены → TZ
        if "TRAILING ZEROS INCLUDED" in upper:
            return "LZ"
        if "LEADING ZEROS INCLUDED" in upper:
            return "TZ"
    return None


def detect_zero_suppression(filename):
    """Автоопределение режима подавления нулей из заголовка Excellon-файла.

    Возвращает 'LZ', 'TZ' или None если маркер не найден (вызывающий код должен
    выбрать дефолт; рекомендуется 'LZ' — наиболее частый режим у современных CAD).

    Распознаваемые маркеры:
      - INCH,LZ / METRIC,LZ — leading zero suppression (опущены ведущие нули)
      - INCH,TZ / METRIC,TZ — trailing zero suppression (опущены конечные нули)
      - ;TRAILING ZEROS INCLUDED — эквивалентно LZ
      - ;LEADING ZEROS INCLUDED — эквивалентно TZ
    """
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            lines = [f.readline() for _ in range(50)]
        return _scan_zero_suppression(lines)
    except UnicodeDecodeError:
        logger.warning("UTF-8 decode failed for %s, trying latin-1", filename)
        try:
            with open(filename, 'r', encoding='latin-1') as f:
                lines = [f.readline() for _ in range(50)]
            return _scan_zero_suppression(lines)
        except (OSError, UnicodeDecodeError) as e:
            logger.warning("detect_zero_suppression: cannot read %s: %s", filename, e)
            return None
    except (OSError, PermissionError, FileNotFoundError) as e:
        logger.warning("detect_zero_suppression: cannot read %s: %s", filename, e)
        return None


def _decode_coord(digits_str: str, format_x: int, format_y: int, zero_mode: str) -> float:
    """Декодировать строку Excellon-координаты в миллиметры.

    digits_str: исходные цифры с опциональным знаком, например "1500", "-15", "+001500".
    format_x, format_y: длины целой и дробной частей (для "3.3" это 3 и 3).
    zero_mode: "LZ" (подавлены ведущие), "TZ" (подавлены конечные) или "NONE".

    Для LZ и NONE int() корректно отбрасывает ведущие нули и деление на 10**format_y
    даёт правильный результат — старое поведение парсера. Для TZ необходимо
    дополнить строку справа нулями до полной ширины (format_x + format_y),
    чтобы сохранить позиционную величину цифр.
    """
    sign = ""
    body = digits_str
    if body and body[0] in "+-":
        sign, body = body[0], body[1:]
    if zero_mode == "TZ":
        body = body.ljust(format_x + format_y, "0")
    return int(sign + body) / (10 ** format_y)


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


def parse_excellon_file(filename, coord_format=None, zero_mode=None):
    """Парсинг файла круглых отверстий.

    Параметры:
        filename: путь к Excellon-файлу.
        coord_format: формат координат (например, '3.3'). По умолчанию — из cfg.
        zero_mode: режим подавления нулей ('LZ', 'TZ', 'NONE'). По умолчанию —
                   автодетект через detect_zero_suppression(); при отсутствии маркера
                   используется 'LZ' (стандартный режим современных CAD).

    Возвращает dict: {tool_number: {diameter, holes[], visible, var}}.
    """
    if coord_format is None:
        coord_format = cfg.coordinate_format
    tools = {}
    current_tool = None

    # Парсинг формата координат с обработкой ошибок
    try:
        format_x, format_y = map(int, coord_format.split('.'))
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

    # Определение режима подавления нулей
    if zero_mode is None:
        zero_mode = detect_zero_suppression(filename) or "LZ"
    if zero_mode not in ("LZ", "TZ", "NONE"):
        raise ValueError(
            f"Неверный zero_mode '{zero_mode}'. Ожидается 'LZ', 'TZ' или 'NONE'."
        )
    logger.info("Excellon parse: %s, format=%s, zero_mode=%s", filename, coord_format, zero_mode)

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
                # H2: модальный контекст координат сохраняется через смену
                # инструмента — по стандарту Excellon отверстия после T-команды
                # могут указывать только X или только Y, наследуя недостающую
                # координату от предыдущего отверстия. Сброс приводил к молчаливой
                # потере первого отверстия каждого нового инструмента.
        # M1: elif (а не второй if) — строка-определение инструмента не должна
        # одновременно интерпретироваться как координата отверстия. Иначе
        # нестандартные T-строки вида "T02C1.6X1000Y1000", встречающиеся
        # у некоторых постпроцессоров, давали фантомное отверстие.
        elif current_tool and ('X' in line or 'Y' in line):
            x_match = re.search(r'X([+-]?\d+)', line)
            y_match = re.search(r'Y([+-]?\d+)', line)
            if x_match:
                last_x = _decode_coord(x_match.group(1), format_x, format_y, zero_mode)
            if y_match:
                last_y = _decode_coord(y_match.group(1), format_x, format_y, zero_mode)
            # Требуем обе координаты — отверстие без X или Y невалидно.
            # При наличии модального контекста (предыдущая координата) — наследуем.
            if last_x is not None and last_y is not None:
                tools[current_tool]['holes'].append((last_x, last_y))
            else:
                logger.warning(
                    "Skipping hole line %r: incomplete coordinates "
                    "(no modal context yet, last_x=%s, last_y=%s)",
                    line, last_x, last_y
                )
    # M3: tie-breaker по int(tool_number) — при одинаковых диаметрах порядок
    # детерминирован (T01 раньше T02), что важно для читаемости G-code и
    # эталонных тестов. int() корректно обрабатывает ведущие нули ("01" == 1).
    sorted_tools = dict(sorted(
        tools.items(),
        key=lambda item: (item[1]['diameter'], int(item[0]))
    ))
    for tool, data in sorted_tools.items():
        data['holes'] = nearest_neighbor_tsp(data['holes'])
    return sorted_tools


def parse_slot_file(filename, coord_format=None, zero_mode=None):
    """Парсинг файла слотов.

    Параметры аналогичны parse_excellon_file (см. выше). Возвращает dict:
    {tool_number: {diameter, slots[], visible, var}}, где каждый слот —
    кортеж ((start_x, start_y), (end_x, end_y)) в миллиметрах.
    """
    if coord_format is None:
        coord_format = cfg.coordinate_format
    tools = {}
    current_tool = None

    # Парсинг формата координат с обработкой ошибок
    try:
        format_x, format_y = map(int, coord_format.split('.'))
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

    # Определение режима подавления нулей
    if zero_mode is None:
        zero_mode = detect_zero_suppression(filename) or "LZ"
    if zero_mode not in ("LZ", "TZ", "NONE"):
        raise ValueError(
            f"Неверный zero_mode '{zero_mode}'. Ожидается 'LZ', 'TZ' или 'NONE'."
        )
    logger.info("Slot parse: %s, format=%s, zero_mode=%s", filename, coord_format, zero_mode)
    
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
    # M4: ключи header_tools нормализуем через int(), чтобы устранить
    # рассинхронизацию между секциями. Если в заголовке "T01", а в теле "T1"
    # (или наоборот), без int()-нормализации второй lookup промахивается и
    # диаметр молча падает до 0.0 — ровно та ситуация из аудита.
    # Публичный словарь tools продолжает использовать строковые ключи в той
    # форме, в какой они в файле — это сохраняет совместимость со всеми
    # callers (UI, тесты, интеграция) без необходимости массовой миграции.
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
                header_tools[int(tool_number)] = diameter
    current_tool = None
    i = 0
    while i < len(lines):
        line = lines[i]
        tool_match = re.match(r'^T(\d+)$', line)
        if tool_match:
            tool_number = tool_match.group(1)
            current_tool = tool_number
            if current_tool not in tools:
                diameter = header_tools.get(int(current_tool), 0.0)
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
            # H1: строго требуем обе координаты на G00. Старый код принимал
            # любую и подменял отсутствующую нулём, что давало слот в начале
            # координат вместо ожидаемого. Слот без полной начальной точки —
            # некорректный ввод; сообщаем в лог и пропускаем.
            if x_match and y_match:
                g00_x = _decode_coord(x_match.group(1), format_x, format_y, zero_mode)
                g00_y = _decode_coord(y_match.group(1), format_x, format_y, zero_mode)
                if i + 1 < len(lines) and lines[i + 1] == 'M15':
                    if i + 2 < len(lines) and lines[i + 2].startswith('G01'):
                        g01_line = lines[i + 2]
                        g01_x_match = re.search(r'X([+-]?\d+)', g01_line)
                        g01_y_match = re.search(r'Y([+-]?\d+)', g01_line)
                        # G01 может опускать одну координату — модальное
                        # наследование от G00 это стандартное поведение Excellon.
                        g01_x = _decode_coord(g01_x_match.group(1), format_x, format_y, zero_mode) if g01_x_match else g00_x
                        g01_y = _decode_coord(g01_y_match.group(1), format_x, format_y, zero_mode) if g01_y_match else g00_y
                        if i + 3 < len(lines) and lines[i + 3] == 'M16':
                            tools[current_tool]['slots'].append(
                                ((g00_x, g00_y), (g01_x, g01_y))
                            )
                            i += 4
                            continue
            elif x_match or y_match:
                logger.warning(
                    "Skipping slot at line %d: G00 must have both X and Y "
                    "(got %r)", i, line
                )
            i += 1
            continue
        i += 1
    for tool, data in tools.items():
        if data['slots']:
            data['slots'] = nearest_neighbor_tsp_slots(data['slots'])
    return tools
