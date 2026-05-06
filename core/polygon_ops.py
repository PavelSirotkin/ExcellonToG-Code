"""
Геометрические операции с полигонами и контурами.
"""
import math
from typing import List, Dict, Tuple, Optional, Any


# ==========================================================
# Базовые операции
# ==========================================================

def bounding_box(segments: List[Dict[str, Any]]) -> Tuple[float, float, float, float]:
    """Вычислить bounding box списка сегментов.
    Returns: (min_x, min_y, max_x, max_y)
    """
    if not segments:
        return (0, 0, 0, 0)

    all_points = []
    for seg in segments:
        if seg['type'] == 'line':
            all_points.extend([seg['p1'], seg['p2']])
        elif seg['type'] == 'arc':
            all_points.extend([seg['start'], seg['end']])

    xs = [p[0] for p in all_points]
    ys = [p[1] for p in all_points]
    return (min(xs), min(ys), max(xs), max(ys))


def polygon_signed_area(points: List[Tuple[float, float]]) -> float:
    """Вычислить ориентированную площадь многоугольника.
    Положительная = CCW, отрицательная = CW.
    """
    if len(points) < 3:
        return 0.0
    area = 0.0
    n = len(points)
    for i in range(n):
        x1, y1 = points[i]
        x2, y2 = points[(i + 1) % n]
        area += (x2 - x1) * (y2 + y1)
    return area / 2.0


def is_ccw(points: List[Tuple[float, float]]) -> bool:
    """True если многоугольник ориентирован против часовой стрелки."""
    return polygon_signed_area(points) > 0


def normalize_to_ccw(points: List[Tuple[float, float]]) -> List[Tuple[float, float]]:
    """Нормализовать многоугольник к CCW ориентации."""
    if is_ccw(points):
        return points
    return list(reversed(points))


def _seg_start(seg: Dict[str, Any]) -> Tuple[float, float]:
    return seg['p1'] if seg['type'] == 'line' else seg['start']


def _seg_end(seg: Dict[str, Any]) -> Tuple[float, float]:
    return seg['p2'] if seg['type'] == 'line' else seg['end']


def split_subpaths(segments: List[Dict[str, Any]]) -> List[List[Dict[str, Any]]]:
    """Разбить плоский список сегментов на подконтуры.

    Подконтур начинается с сегмента, помеченного `subpath_start=True`
    парсером (внешний контур, каждый G36/G37 регион, путь после явного
    D02-перемещения). Если флагов нет ни на одном сегменте — возвращаем
    единый подконтур (поведение для исторических данных).
    """
    if not segments:
        return []
    subpaths: List[List[Dict[str, Any]]] = []
    current: List[Dict[str, Any]] = []
    for seg in segments:
        if seg.get('subpath_start') and current:
            subpaths.append(current)
            current = []
        current.append(seg)
    if current:
        subpaths.append(current)
    return subpaths


def is_closed_contour(segments: List[Dict[str, Any]], tol_mm: float = 1e-3) -> bool:
    """Проверить, что контур замкнут.

    Если контур состоит из нескольких подконтуров (внешний контур +
    G36/G37-вырезы), требуем замкнутости КАЖДОГО — иначе offset/tabs
    дадут мусор. Старая реализация сравнивала только общий start/end,
    из-за чего платы с вырезами считались незамкнутыми и блокировали
    генерацию обрезного G-code.

    Args:
        segments: список сегментов 'line'/'arc'
        tol_mm: допуск на стыковку start ↔ end (по умолчанию 1 микрон)
    Returns:
        True если все подконтуры замкнуты, иначе False
    """
    if not segments or len(segments) < 2:
        return False

    subpaths = split_subpaths(segments)
    if not subpaths:
        return False

    for sp in subpaths:
        if len(sp) < 2:
            return False
        first = _seg_start(sp[0])
        last = _seg_end(sp[-1])
        if math.hypot(first[0] - last[0], first[1] - last[1]) > tol_mm:
            return False
    return True


# ==========================================================
# Point in polygon (ray casting)
# ==========================================================

def point_in_polygon(point: Tuple[float, float],
                     polygon: List[Tuple[float, float]],
                     eps: float = 1e-9) -> bool:
    """
    Проверка, находится ли точка внутри многоугольника.
    Использует алгоритм ray casting.
    Точка на ребре считается внутри (для безопасности).
    """
    x, y = point
    n = len(polygon)
    if n < 3:
        return False

    inside = False
    for i in range(n):
        x1, y1 = polygon[i]
        x2, y2 = polygon[(i + 1) % n]

        # Проверка, лежит ли точка на отрезке
        # Коллинеарность
        cross = (x2 - x1) * (y - y1) - (y2 - y1) * (x - x1)
        if abs(cross) < eps:
            # Проверяем, что точка между концами отрезка
            dot = (x - x1) * (x - x2) + (y - y1) * (y - y2)
            if dot <= eps:
                return True  # На ребре

        # Ray casting
        if ((y1 > y) != (y2 > y)):
            x_intersect = x1 + (y - y1) * (x2 - x1) / (y2 - y1)
            if x_intersect > x:
                inside = not inside

    return inside


# ==========================================================
# Flatten arcs to chords
# ==========================================================

def flatten(segments: List[Dict[str, Any]], tol_mm: float = 0.02) -> List[Tuple[float, float]]:
    """
    Преобразовать сегменты в список точек (дуги → хорды).
    Возвращает список точек контура.

    Внимание: для контуров с несколькими подконтурами возвращает все
    точки подряд без разделителя — точки соседних подконтуров окажутся
    «соединёнными» в линию. Для рендера/обхода с разрывами используйте
    `flatten_subpaths`.
    """
    if not segments:
        return []

    points = []
    for seg in segments:
        if seg['type'] == 'line':
            if not points:
                points.append(seg['p1'])
            points.append(seg['p2'])
        elif seg['type'] == 'arc':
            arc_points = _flatten_arc(seg, tol_mm)
            if not points:
                points.extend(arc_points)
            else:
                points.extend(arc_points[1:])  # Пропускаем первую точку (дублируется)

    return points


def flatten_subpaths(segments: List[Dict[str, Any]],
                     tol_mm: float = 0.02) -> List[List[Tuple[float, float]]]:
    """Развернуть сегменты в список подконтуров (каждый — список точек).

    Используется рендером, чтобы внешний контур и G36/G37-вырезы
    рисовались независимо и между ними не появлялись паразитные линии.
    """
    return [flatten(sp, tol_mm=tol_mm) for sp in split_subpaths(segments)]


def classify_subpaths(segments: List[Dict[str, Any]],
                      tol_mm: float = 0.5) -> List[Dict[str, Any]]:
    """Классифицировать подконтуры на внешние и внутренние.

    Для каждого подконтура вычисляем уровень вложенности — сколько
    ДРУГИХ подконтуров содержат его внутри себя (через
    point_in_polygon по тестовой точке). Чётный уровень (включая 0) —
    внешний контур (нужен offset НАРУЖУ), нечётный — внутренний вырез
    (нужен offset ВНУТРЬ). Это корректно для произвольной глубины
    «остров в дыре в острове в плате».

    Args:
        segments: плоский список сегментов с метками subpath_start
        tol_mm: точность аппроксимации дуг при проверке (грубее — быстрее)

    Returns:
        Список словарей в том же порядке, что и подконтуры:
        [{'segments': [...], 'is_outer': bool, 'depth': int, 'polygon': [...]}, ...]
    """
    sps = split_subpaths(segments)
    polys = [flatten(sp, tol_mm=tol_mm) for sp in sps]

    # Для каждого подконтура берём «надёжную» тестовую точку.
    # Первая точка лежит на границе соседнего подконтура только если
    # они касаются — что для PCB не норма. Но для пущей надёжности
    # пробуем несколько точек и берём большинство.
    def _depth_of(idx: int) -> int:
        poly = polys[idx]
        if not poly:
            return 0
        # Несколько проб по подконтуру
        n = len(poly)
        sample_idxs = [0, n // 3, (2 * n) // 3] if n >= 3 else [0]
        depths: List[int] = []
        for s_idx in sample_idxs:
            test_pt = poly[s_idx]
            d = 0
            for j, pj in enumerate(polys):
                if j == idx or len(pj) < 3:
                    continue
                if point_in_polygon(test_pt, pj):
                    d += 1
            depths.append(d)
        # «Голосование» — самое частое значение
        return max(set(depths), key=depths.count)

    result: List[Dict[str, Any]] = []
    for i, sp in enumerate(sps):
        depth = _depth_of(i)
        result.append({
            'segments': sp,
            'is_outer': (depth % 2 == 0),
            'depth': depth,
            'polygon': polys[i],
        })
    return result


def _flatten_arc(arc: Dict[str, Any], tol_mm: float) -> List[Tuple[float, float]]:
    """Аппроксимировать дугу хордами с заданной точностью."""
    center = arc['center']
    r = arc['r']
    start = arc['start']
    end = arc['end']
    ccw = arc['ccw']

    # Вычисляем углы
    start_angle = math.atan2(start[1] - center[1], start[0] - center[0])
    end_angle = math.atan2(end[1] - center[1], end[0] - center[0])

    # Нормализуем углы
    if ccw:
        while end_angle < start_angle:
            end_angle += 2 * math.pi
    else:
        while end_angle > start_angle:
            end_angle -= 2 * math.pi

    delta_angle = abs(end_angle - start_angle)

    # Вычисляем количество сегментов
    # Стрелка прогиба: h = r * (1 - cos(theta/2))
    # theta = 2 * acos(1 - h/r)
    if tol_mm >= r:
        n_segments = 1
    else:
        theta = 2 * math.acos(1 - tol_mm / r)
        n_segments = max(1, int(math.ceil(delta_angle / theta)))

    points = [start]
    for i in range(1, n_segments):
        t = i / n_segments
        angle = start_angle + t * (end_angle - start_angle) if ccw else start_angle - t * abs(end_angle - start_angle)
        x = center[0] + r * math.cos(angle)
        y = center[1] + r * math.sin(angle)
        points.append((x, y))
    points.append(end)

    return points


# ==========================================================
# Offset operations
# ==========================================================

def _normalize(v: Tuple[float, float]) -> Tuple[float, float]:
    """Нормализовать вектор."""
    x, y = v
    length = math.sqrt(x * x + y * y)
    if length < 1e-10:
        return (0, 0)
    return (x / length, y / length)


def _perpendicular(v: Tuple[float, float], outward: bool = True) -> Tuple[float, float]:
    """Получить перпендикуляр к вектору (поворот на 90°)."""
    x, y = v
    if outward:
        return (-y, x)  # Поворот на +90° (внешняя нормаль для CCW)
    else:
        return (y, -x)  # Поворот на -90°


def _line_intersection(p1: Tuple[float, float], d1: Tuple[float, float],
                       p2: Tuple[float, float], d2: Tuple[float, float]) -> Optional[Tuple[float, float]]:
    """Найти пересечение двух линий (p1 + t*d1) и (p2 + s*d2)."""
    x1, y1 = p1
    dx1, dy1 = d1
    x2, y2 = p2
    dx2, dy2 = d2

    det = dx1 * (-dy2) - dy1 * (-dx2)
    if abs(det) < 1e-10:
        return None  # Параллельны

    dx = x2 - x1
    dy = y2 - y1
    t = (dx * (-dy2) - dy * (-dx2)) / det

    return (x1 + t * dx1, y1 + t * dy1)


def offset_segments(segments: List[Dict[str, Any]], delta: float,
                    outward: bool = True) -> List[Dict[str, Any]]:
    """
    Создать offset контура на расстояние delta.
    Для выпуклых углов — простое пересечение смещённых рёбер.
    Для вогнутых — дуга скругления (в MVP — упрощённо).

    Args:
        segments: исходные сегменты
        delta: расстояние offset (положительное = наружу)
        outward: True = наружу, False = внутрь

    Returns:
        Список смещённых сегментов
    """
    if not segments or delta == 0:
        return segments

    # Контур должен быть замкнут. На незамкнутом offset/tabs давали бы мусор молча
    # (последний сегмент не стыковался бы с первым). Возвращаем [] — caller
    # увидит "Could not create offset contour" и сообщит пользователю.
    if not is_closed_contour(segments):
        return []

    # Преобразуем в точки для упрощения
    points = flatten(segments, tol_mm=0.01)
    if len(points) < 3:
        return segments

    # Удаляем последовательные дубликаты и замыкающую копию первой точки.
    # flatten для замкнутого контура обычно возвращает [A, B, C, D, A] —
    # финальная A мешает при обходе и создаёт нуль-длинное ребро.
    # Также на всякий случай убираем любые совпадающие подряд точки,
    # которые могут прийти из кривого входного сегмента (нуль-длинная линия),
    # иначе нормаль к такому ребру вырождается и смещение даёт мусорный угол.
    eps = 1e-6
    dedup: List[Tuple[float, float]] = [points[0]]
    for p in points[1:]:
        if math.hypot(p[0] - dedup[-1][0], p[1] - dedup[-1][1]) > eps:
            dedup.append(p)
    # Если первая и последняя точки совпали (замкнутый контур) — убираем хвост.
    if (len(dedup) > 1 and
            math.hypot(dedup[-1][0] - dedup[0][0],
                       dedup[-1][1] - dedup[0][1]) <= eps):
        dedup.pop()
    if len(dedup) < 3:
        return segments
    points = dedup

    # Нормализуем к CCW
    points = normalize_to_ccw(points)

    # Для outward=True с CCW: смещаем вправо от направления (внешняя нормаль)
    # Для outward=False: смещаем влево
    n = len(points)
    offset_points = []

    for i in range(n):
        p_prev = points[(i - 1) % n]
        p_curr = points[i]
        p_next = points[(i + 1) % n]

        # Векторы рёбер
        v1 = (p_curr[0] - p_prev[0], p_curr[1] - p_prev[1])
        v2 = (p_next[0] - p_curr[0], p_next[1] - p_curr[1])

        # Нормали к рёбрам
        n1 = _perpendicular(_normalize(v1), outward=outward)
        n2 = _perpendicular(_normalize(v2), outward=outward)

        # Смещённые точки рёбер
        p1_offset = (p_prev[0] + delta * n1[0], p_prev[1] + delta * n1[1])
        p2_offset = (p_curr[0] + delta * n1[0], p_curr[1] + delta * n1[1])
        p3_offset = (p_curr[0] + delta * n2[0], p_curr[1] + delta * n2[1])
        p4_offset = (p_next[0] + delta * n2[0], p_next[1] + delta * n2[1])

        # Находим пересечение смещённых рёбер
        d1 = (p2_offset[0] - p1_offset[0], p2_offset[1] - p1_offset[1])
        d2 = (p4_offset[0] - p3_offset[0], p4_offset[1] - p3_offset[1])

        intersection = _line_intersection(p1_offset, d1, p3_offset, d2)

        if intersection:
            offset_points.append(intersection)
        else:
            # Параллельные рёбра — берём среднюю точку
            mid = ((p2_offset[0] + p3_offset[0]) / 2,
                   (p2_offset[1] + p3_offset[1]) / 2)
            offset_points.append(mid)

    # Преобразуем обратно в сегменты
    result = []
    for i in range(len(offset_points)):
        p1 = offset_points[i]
        p2 = offset_points[(i + 1) % len(offset_points)]
        result.append({'type': 'line', 'p1': p1, 'p2': p2})

    return result


# ==========================================================
# Tabs insertion
# ==========================================================

def segment_length(seg: Dict[str, Any]) -> float:
    """Вычислить длину одного сегмента (линия или дуга).

    Для линии — евклидово расстояние между p1 и p2.
    Для дуги — `r * |end_angle - start_angle|` с учётом направления (`ccw`).

    Если у дуги отсутствуют обязательные поля (`r`/`center`/`ccw`) — возвращается
    длина хорды (грубая нижняя оценка). Это бывает только на повреждённых данных,
    реальный gerber_parser всегда заполняет все поля.
    """
    if seg['type'] == 'line':
        x1, y1 = seg['p1']
        x2, y2 = seg['p2']
        return math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)
    if seg['type'] == 'arc':
        try:
            r = seg['r']
            start = seg['start']
            end = seg['end']
            center = seg['center']
            ccw = seg['ccw']
        except KeyError:
            # Битая arc-структура — возвращаем длину хорды
            start = seg.get('start', (0, 0))
            end = seg.get('end', (0, 0))
            return math.hypot(end[0] - start[0], end[1] - start[1])
        start_angle = math.atan2(start[1] - center[1], start[0] - center[0])
        end_angle = math.atan2(end[1] - center[1], end[0] - center[0])
        if ccw:
            while end_angle < start_angle:
                end_angle += 2 * math.pi
        else:
            while end_angle > start_angle:
                end_angle -= 2 * math.pi
        return r * abs(end_angle - start_angle)
    return 0.0


def compute_total_length(segments: List[Dict[str, Any]]) -> float:
    """Вычислить общую длину контура."""
    return sum(segment_length(seg) for seg in segments)


def point_at_length(segments: List[Dict[str, Any]], target_length: float) -> Tuple[float, float]:
    """Найти точку на контуре на заданном расстоянии от начала."""
    current_length = 0.0

    for seg in segments:
        if seg['type'] == 'line':
            x1, y1 = seg['p1']
            x2, y2 = seg['p2']
            seg_len = math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)

            if current_length + seg_len >= target_length:
                t = (target_length - current_length) / seg_len if seg_len > 0 else 0
                return (x1 + t * (x2 - x1), y1 + t * (y2 - y1))

            current_length += seg_len

        elif seg['type'] == 'arc':
            r = seg['r']
            start = seg['start']
            end = seg['end']
            center = seg['center']
            ccw = seg['ccw']

            start_angle = math.atan2(start[1] - center[1], start[0] - center[0])
            end_angle = math.atan2(end[1] - center[1], end[0] - center[0])
            if ccw:
                while end_angle < start_angle:
                    end_angle += 2 * math.pi
            else:
                while end_angle > start_angle:
                    end_angle -= 2 * math.pi

            arc_len = r * abs(end_angle - start_angle)

            if current_length + arc_len >= target_length:
                t = (target_length - current_length) / arc_len if arc_len > 0 else 0
                angle = start_angle + t * (end_angle - start_angle) if ccw else start_angle - t * abs(end_angle - start_angle)
                return (center[0] + r * math.cos(angle), center[1] + r * math.sin(angle))

            current_length += arc_len

    # Если не нашли — возвращаем последнюю точку
    last_seg = segments[-1]
    if last_seg['type'] == 'line':
        return last_seg['p2']
    else:
        return last_seg['end']


def insert_tabs(segments: List[Dict[str, Any]], n_tabs: int,
                tab_width: float) -> List[Dict[str, Any]]:
    """
    Вставить держательные перемычки (tabs) в контур.

    Стратегия: перемычки ставятся в середины сторон контура, а не равномерно
    по длине периметра. Это гарантирует, что при любом N tab не попадёт на угол
    (для прямоугольника N=1..4 раньше давали один или несколько tab-ов прямо
    в углах — фреза не смогла бы корректно удержать мост).

    - Если N <= количества сторон S — выбираем N сторон, распределённых по
      индексам максимально равномерно, tab в середине каждой.
    - Если N > S — распределяем tabs по сторонам пропорционально их длинам
      (largest-remainder), на каждой стороне tabs ставятся в точках
      (k + 0.5) / K от длины стороны.

    Args:
        segments: сегменты контура (ожидается замкнутый полигон из линий)
        n_tabs: количество tabs
        tab_width: ширина каждого tab (мм)

    Returns:
        Список сегментов; сегменты, попавшие внутрь tab-участка, помечены 'is_tab': True.
    """
    if n_tabs <= 0 or tab_width <= 0 or not segments:
        return list(segments)

    # Контур должен быть замкнут. На незамкнутом tabs давали бы мусор молча
    # (перемычки могли бы оказаться на разрыве контура). Возвращаем [] — caller
    # увидит проблему и сообщит пользователю.
    if not is_closed_contour(segments):
        return []

    # Собираем логические стороны контура с их кумулятивными длинами.
    # Каждый входной сегмент считается отдельной стороной (для outline-пути
    # это соответствует одному ребру offset-полигона).
    sides: List[Dict[str, Any]] = []
    cum = 0.0
    for seg in segments:
        if seg['type'] == 'line':
            x1, y1 = seg['p1']
            x2, y2 = seg['p2']
            L = math.hypot(x2 - x1, y2 - y1)
        elif seg['type'] == 'arc':
            r = seg['r']
            start = seg['start']
            end = seg['end']
            center = seg['center']
            ccw = seg['ccw']
            sa = math.atan2(start[1] - center[1], start[0] - center[0])
            ea = math.atan2(end[1] - center[1], end[0] - center[0])
            if ccw:
                while ea < sa:
                    ea += 2 * math.pi
            else:
                while ea > sa:
                    ea -= 2 * math.pi
            L = r * abs(ea - sa)
        else:
            continue
        if L > 1e-9:
            sides.append({'start': cum, 'length': L})
            cum += L
    total_length = cum
    if total_length <= 0 or not sides:
        return list(segments)

    # Если tabs физически не вмещаются — ужимаем ширину
    if tab_width * n_tabs >= total_length:
        tab_width = total_length / (n_tabs + 1)

    S = len(sides)
    tab_centers: List[float] = []

    if n_tabs <= S:
        # Выбираем n_tabs сторон, распределённых по индексам максимально равномерно.
        # int(round(i * S / n_tabs)) даёт естественный шаг S/n_tabs;
        # при коллизиях сдвигаем индекс на следующую свободную сторону.
        chosen: set = set()
        for i in range(n_tabs):
            idx = int(round(i * S / n_tabs)) % S
            while idx in chosen:
                idx = (idx + 1) % S
            chosen.add(idx)
        tab_centers = sorted(
            sides[i]['start'] + sides[i]['length'] / 2.0 for i in chosen
        )
    else:
        # Больше tabs чем сторон — распределяем пропорционально длинам сторон
        # по методу наибольших остатков (largest-remainder / Hamilton).
        exact = [n_tabs * s['length'] / total_length for s in sides]
        counts = [int(e) for e in exact]
        remaining = n_tabs - sum(counts)
        ranking = sorted(range(S), key=lambda i: -(exact[i] - counts[i]))
        for i in range(remaining):
            counts[ranking[i]] += 1
        for si, s in enumerate(sides):
            K = counts[si]
            if K == 0:
                continue
            for k in range(K):
                frac = (k + 0.5) / K
                tab_centers.append(s['start'] + frac * s['length'])
        tab_centers.sort()

    # Строим список tab-интервалов [start_len, end_len] в координатах общей длины,
    # раскрывая wrap-around в два отдельных диапазона.
    tab_ranges: List[Tuple[float, float]] = []
    for center in tab_centers:
        s = center - tab_width / 2.0
        e = center + tab_width / 2.0
        if s < 0:
            # Половина в хвосте контура, половина в начале
            tab_ranges.append((s + total_length, total_length))
            tab_ranges.append((0.0, e))
        elif e > total_length:
            tab_ranges.append((s, total_length))
            tab_ranges.append((0.0, e - total_length))
        else:
            tab_ranges.append((s, e))

    def _is_in_tab(length_pos: float) -> bool:
        for ts, te in tab_ranges:
            if ts - 1e-9 <= length_pos <= te + 1e-9:
                return True
        return False

    result: List[Dict[str, Any]] = []
    current_length = 0.0

    for seg in segments:
        if seg['type'] == 'line':
            x1, y1 = seg['p1']
            x2, y2 = seg['p2']
            seg_len = math.hypot(x2 - x1, y2 - y1)
            if seg_len <= 1e-9:
                continue

            seg_start = current_length
            seg_end = current_length + seg_len

            # Собираем точки разбиения: границы сегмента + границы tab-ов внутри сегмента
            split_positions = {seg_start, seg_end}
            for ts, te in tab_ranges:
                if seg_start < ts < seg_end:
                    split_positions.add(ts)
                if seg_start < te < seg_end:
                    split_positions.add(te)
            sorted_splits = sorted(split_positions)

            # Каждый подсегмент помечаем is_tab по положению середины
            for i in range(len(sorted_splits) - 1):
                p1_len = sorted_splits[i]
                p2_len = sorted_splits[i + 1]
                if p2_len - p1_len < 1e-9:
                    continue

                t1 = (p1_len - seg_start) / seg_len
                t2 = (p2_len - seg_start) / seg_len
                p1 = (x1 + t1 * (x2 - x1), y1 + t1 * (y2 - y1))
                p2 = (x1 + t2 * (x2 - x1), y1 + t2 * (y2 - y1))

                new_seg = {'type': 'line', 'p1': p1, 'p2': p2}
                mid_len = (p1_len + p2_len) / 2.0
                if _is_in_tab(mid_len):
                    new_seg['is_tab'] = True
                result.append(new_seg)

            current_length += seg_len

        elif seg['type'] == 'arc':
            # Для дуг — упрощённо добавляем как есть (в MVP tabs на дугах редки)
            result.append(seg)
            r = seg['r']
            start = seg['start']
            end = seg['end']
            center = seg['center']
            ccw = seg['ccw']

            start_angle = math.atan2(start[1] - center[1], start[0] - center[0])
            end_angle = math.atan2(end[1] - center[1], end[0] - center[0])
            if ccw:
                while end_angle < start_angle:
                    end_angle += 2 * math.pi
            else:
                while end_angle > start_angle:
                    end_angle -= 2 * math.pi

            current_length += r * abs(end_angle - start_angle)

    return result
