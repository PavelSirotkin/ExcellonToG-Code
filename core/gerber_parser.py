"""
Парсинг Gerber-файлов (RS-274X) для импорта контура платы (edge-cuts).
Поддерживает минимальное подмножество, достаточное для KiCad/EasyEDA outline.
"""
import re
import math
import logging
from typing import List, Dict, Tuple, Optional

logger = logging.getLogger(__name__)


# ==========================================================
# Типы сегментов контура
# ==========================================================

def make_line(p1: Tuple[float, float], p2: Tuple[float, float]) -> Dict:
    """Создать линейный сегмент."""
    return {'type': 'line', 'p1': p1, 'p2': p2}


def make_arc(center: Tuple[float, float], r: float,
             start: Tuple[float, float], end: Tuple[float, float],
             ccw: bool) -> Dict:
    """Создать дуговой сегмент.
    center: центр дуги
    r: радиус
    start: начальная точка
    end: конечная точка
    ccw: True = против часовой стрелки
    """
    return {
        'type': 'arc',
        'center': center,
        'r': r,
        'start': start,
        'end': end,
        'ccw': ccw
    }


# ==========================================================
# Парсер Gerber
# ==========================================================

class GerberParser:
    """State machine парсер Gerber RS-274X."""

    def __init__(self):
        self.integer_digits = 2
        self.decimal_digits = 4
        self.unit = "mm"  # "mm" или "inch"
        self.coordinate_mode = "absolute"  # всегда absolute в MVP
        self.interpolation = "linear"  # "linear", "cw", "ccw"
        self.current_x = 0.0
        self.current_y = 0.0
        # Предыдущая позиция (до текущей D01/D02).
        # Критично: инициализируем явно (0,0), иначе первая D01 без
        # предварительного D02 создаст вырожденный нуль-сегмент
        # (prev_x подхватится из уже обновлённого current_x).
        self._prev_x = 0.0
        self._prev_y = 0.0
        self.region_mode = False
        self.region_points = []  # точки текущего региона
        self.segments = []  # итоговые сегменты
        self.in_region = False
        # Флаг: следующий построенный сегмент — начало нового подконтура.
        # Контур платы из Gerber может состоять из нескольких независимых
        # замкнутых путей (например, внешний контур + регион-вырез G36/G37).
        # Без разбиения они попадают в один плоский список и рендер/проверка
        # замкнутости трактуют их как единый разорванный путь.
        self._pending_subpath_start = True

    def _parse_coordinate(self, val_str: str) -> float:
        """Парсинг координаты с учётом формата.

        Знак вынесен ДО zfill: иначе `"-40".zfill(6)` даёт `"-00040"`,
        и срез по integer_digits отделяет `"-000"` (это всё ещё 0), а
        дробь `"40"` оказывается без знака. Раньше из-за этого все
        отрицательные координаты (включая I/J центров дуг и Y<0
        внешнего контура) парсились как положительные — отсюда bbox
        без отрицательной части и неверные радиусы скруглений.
        """
        if not val_str:
            return None

        sign = 1
        if val_str[0] == '-':
            sign = -1
            val_str = val_str[1:]
        elif val_str[0] == '+':
            val_str = val_str[1:]

        if not val_str:
            return 0.0

        total_digits = self.integer_digits + self.decimal_digits
        val_str = val_str.zfill(total_digits)
        int_part = val_str[:self.integer_digits]
        frac_part = val_str[self.integer_digits:]
        value = int(int_part) + int(frac_part) / (10 ** self.decimal_digits)
        return sign * value

    def _extract_xy(self, line: str) -> Tuple[Optional[float], Optional[float]]:
        """Извлечь X и Y из строки."""
        x_match = re.search(r'X([+-]?\d+)', line)
        y_match = re.search(r'Y([+-]?\d+)', line)
        x = self._parse_coordinate(x_match.group(1)) if x_match else None
        y = self._parse_coordinate(y_match.group(1)) if y_match else None
        return x, y

    def _extract_ij(self, line: str) -> Tuple[Optional[float], Optional[float]]:
        """Извлечь I и J (смещение центра дуги)."""
        i_match = re.search(r'I([+-]?\d+)', line)
        j_match = re.search(r'J([+-]?\d+)', line)
        i = self._parse_coordinate(i_match.group(1)) if i_match else 0.0
        j = self._parse_coordinate(j_match.group(1)) if j_match else 0.0
        return i, j

    def _convert_to_mm(self, value: float) -> float:
        """Конвертация в мм если нужно."""
        if self.unit == "inch":
            return value * 25.4
        return value

    def _add_segment(self, x1: float, y1: float, x2: float, y2: float,
                     i: float = 0.0, j: float = 0.0):
        """Добавить сегмент (линию или дугу).

        Нуль-длинные сегменты (D01 без изменения позиции, в том числе
        одиночный `D01*` после закрытия региона) пропускаются — они
        не несут геометрии и портят последующие операции (offset, length).
        Первый реальный сегмент после move/G36/G37 помечается
        `subpath_start=True`.
        """
        x1_mm = self._convert_to_mm(x1)
        y1_mm = self._convert_to_mm(y1)
        x2_mm = self._convert_to_mm(x2)
        y2_mm = self._convert_to_mm(y2)

        if self.interpolation == "linear":
            if abs(x1_mm - x2_mm) < 1e-9 and abs(y1_mm - y2_mm) < 1e-9:
                return  # вырожденная линия — игнорируем, флаг subpath сохраняется
            seg = make_line((x1_mm, y1_mm), (x2_mm, y2_mm))
        else:
            # Дуга
            i_mm = self._convert_to_mm(i)
            j_mm = self._convert_to_mm(j)
            r = math.sqrt(i_mm ** 2 + j_mm ** 2)
            if r < 1e-9:
                return  # вырожденная дуга
            center_x = x1 + i
            center_y = y1 + j
            ccw = (self.interpolation == "ccw")
            seg = make_arc(
                (self._convert_to_mm(center_x), self._convert_to_mm(center_y)),
                r,
                (x1_mm, y1_mm),
                (x2_mm, y2_mm),
                ccw
            )

        if self._pending_subpath_start:
            seg['subpath_start'] = True
            self._pending_subpath_start = False

        self.segments.append(seg)
        if self.in_region:
            self.region_points.append((x2_mm, y2_mm))

    def parse_line(self, line: str):
        """Обработать одну строку Gerber."""
        line = line.strip()
        if not line:
            return

        # Формат координат: %FSLAX25Y25*%
        if line.startswith('%FS'):
            match = re.search(r'FSLAX(\d)(\d)Y(\d)(\d)', line)
            if match:
                self.integer_digits = int(match.group(1))
                self.decimal_digits = int(match.group(2))
            return

        # Единицы измерения
        if '%MO' in line:
            if 'MOMM' in line:
                self.unit = "mm"
            elif 'MOIN' in line:
                self.unit = "inch"
            return

        # Режим интерполяции
        if 'G01' in line:
            self.interpolation = "linear"
            return
        if 'G02' in line:
            self.interpolation = "cw"
            return
        if 'G03' in line:
            self.interpolation = "ccw"
            return

        # Начало региона — отдельный замкнутый подконтур
        if line == 'G36*':
            self.in_region = True
            self.region_points = []
            self._pending_subpath_start = True
            return

        # Конец региона — следующий путь начнёт новый подконтур
        if line == 'G37*':
            self.in_region = False
            self._pending_subpath_start = True
            return

        # Конец файла
        if 'M02' in line:
            return

        # Координаты с D-кодом
        d_match = re.search(r'D0(\d)\*$', line)
        if d_match:
            d_code = int(d_match.group(1))
            x, y = self._extract_xy(line)

            # Захватываем предыдущую позицию ДО обновления current_*.
            # Это ключевое отличие: раньше код обновлял current_x/current_y
            # сразу, а потом пытался достать _prev_x через getattr(fallback=current_x),
            # что ломало самую первую D01 (она получала нуль-сегмент).
            prev_x = self._prev_x
            prev_y = self._prev_y

            if x is not None:
                self.current_x = x
            if y is not None:
                self.current_y = y

            if d_code == 1:  # D01 = резка
                if self.interpolation in ("cw", "ccw"):
                    i, j = self._extract_ij(line)
                else:
                    i, j = 0.0, 0.0

                self._add_segment(prev_x, prev_y, self.current_x, self.current_y, i, j)

                if self.in_region and not self.region_points:
                    self.region_points.append((self._convert_to_mm(prev_x), self._convert_to_mm(prev_y)))

            elif d_code == 2:  # D02 = move без резки
                # Реальное перемещение пера разрывает путь — следующий
                # D01-сегмент стартует новый подконтур. Чистый `D02*`
                # без новых координат не считается перемещением.
                if (x is not None and abs(self.current_x - prev_x) > 1e-9) or \
                   (y is not None and abs(self.current_y - prev_y) > 1e-9):
                    self._pending_subpath_start = True

            self._prev_x = self.current_x
            self._prev_y = self.current_y
            return

        # Просто координаты без D-кода (иногда встречается)
        if 'X' in line or 'Y' in line:
            x, y = self._extract_xy(line)
            if x is not None:
                self.current_x = x
            if y is not None:
                self.current_y = y
            self._prev_x = self.current_x
            self._prev_y = self.current_y


def parse_gerber_outline(filename: str) -> Tuple[List[Dict], str, Tuple[float, float, float, float]]:
    """
    Парсинг Gerber-файла контура платы.

    Returns:
        segments: список сегментов {'type': 'line'|'arc', ...}
        unit: единица измерения ('mm' или 'inch')
        bbox: (min_x, min_y, max_x, max_y) в мм
    """
    parser = GerberParser()

    try:
        # Сначала пробуем UTF-8
        with open(filename, 'r', encoding='utf-8') as f:
            content = f.read()
    except UnicodeDecodeError:
        # Если не получилось, пробуем latin-1 (ISO-8859-1)
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
        # Убираем возможные переносы строк и пробелы
        line = line.strip()
        parser.parse_line(line)

    # Вычисляем bbox
    if not parser.segments:
        return [], parser.unit, (0, 0, 0, 0)

    all_points = []
    for seg in parser.segments:
        if seg['type'] == 'line':
            all_points.extend([seg['p1'], seg['p2']])
        elif seg['type'] == 'arc':
            all_points.extend([seg['start'], seg['end']])

    xs = [p[0] for p in all_points]
    ys = [p[1] for p in all_points]
    bbox = (min(xs), min(ys), max(xs), max(ys))

    return parser.segments, parser.unit, bbox


def is_gerber_file(filename: str) -> bool:
    """Проверка, является ли файл Gerber-формата."""
    try:
        with open(filename, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read(1024)
        # Ищем характерные признаки Gerber
        return ('%FS' in content or 'G04' in content or
                'M02' in content or 'D01' in content or
                'G36' in content or 'G01' in content)
    except Exception:
        return False


def check_contour_closed(segments: List[Dict], eps: float = 1e-3) -> bool:
    """Проверка замкнутости контура.

    Контур из Gerber может состоять из нескольких подконтуров (внешний
    контур + регионы-вырезы). Считаем контур замкнутым, если ВСЕ его
    подконтуры замкнуты (start первого сегмента подконтура совпадает
    с end последнего).
    """
    if not segments:
        return False

    # Делим на подконтуры по флагу 'subpath_start'.
    # Совместимость со старыми данными: если флагов нет вообще,
    # трактуем как один подконтур.
    subpaths: List[List[Dict]] = []
    current: List[Dict] = []
    for seg in segments:
        if seg.get('subpath_start') and current:
            subpaths.append(current)
            current = []
        current.append(seg)
    if current:
        subpaths.append(current)

    if not subpaths:
        return False

    def _start(seg):
        return seg['p1'] if seg['type'] == 'line' else seg['start']

    def _end(seg):
        return seg['p2'] if seg['type'] == 'line' else seg['end']

    for sp in subpaths:
        if len(sp) < 2:
            return False
        first = _start(sp[0])
        last = _end(sp[-1])
        if math.hypot(first[0] - last[0], first[1] - last[1]) >= eps:
            return False
    return True
