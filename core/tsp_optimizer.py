"""
Алгоритмы оптимизации маршрута (TSP — Travelling Salesman Problem).
Используют nearest neighbour + 2-opt для упорядочивания отверстий и слотов.
"""
import math
import time


# Максимальное число итераций 2-opt. На больших платах (1000+ отверстий)
# алгоритм квадратичен по времени. Лимит гарантирует завершение за разумное время.
_TWO_OPT_MAX_ITERATIONS = 1000


def _dist(a, b):
    """Евклидово расстояние между двумя точками."""
    return math.sqrt((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2)


def two_opt(points, max_iterations=None, time_budget_ms=None):
    """2-opt улучшение маршрута: итеративно переворачивает подотрезки,
    пока это сокращает суммарный путь.

    Args:
        points: список точек (x, y)
        max_iterations: максимальное число итераций внешнего цикла
                        (по умолчанию _TWO_OPT_MAX_ITERATIONS).
        time_budget_ms: жёсткий лимит времени в миллисекундах. Проверяется
                        между итерациями внешнего цикла И внутри него
                        (после каждого i во внешнем цикле). По умолчанию None
                        — лимита по времени нет (только по итерациям).

    Returns:
        Оптимизированный маршрут (или текущее лучшее, если сработал лимит).
    """
    if len(points) < 4:
        return points

    if max_iterations is None:
        max_iterations = _TWO_OPT_MAX_ITERATIONS

    deadline = (time.monotonic() + time_budget_ms / 1000.0) if time_budget_ms else None

    improved = True
    route = list(points)
    n = len(route)
    iteration = 0
    while improved and iteration < max_iterations:
        improved = False
        iteration += 1
        for i in range(1, n - 2):
            # Проверка таймаута между внешними проходами по i — позволяет
            # быстро выйти из тяжёлой итерации на больших n.
            if deadline is not None and time.monotonic() > deadline:
                return route
            for j in range(i + 1, n):
                if j - i == 1:
                    continue
                d_before = _dist(route[i - 1], route[i]) + _dist(route[j - 1], route[j])
                d_after = _dist(route[i - 1], route[j - 1]) + _dist(route[i], route[j])
                if d_after < d_before - 1e-9:
                    route[i:j] = route[i:j][::-1]
                    improved = True
    return route


def two_opt_slots(slots, max_iterations=None, time_budget_ms=None):
    """2-opt для слотов: точкой входа считается start, точкой выхода — end.

    Args:
        slots: список слотов ((start_x, start_y), (end_x, end_y))
        max_iterations: максимальное число итераций внешнего цикла
                        (по умолчанию _TWO_OPT_MAX_ITERATIONS).
        time_budget_ms: жёсткий лимит времени в миллисекундах (см. two_opt).

    Returns:
        Оптимизированный маршрут слотов.
    """
    if len(slots) < 4:
        return slots

    if max_iterations is None:
        max_iterations = _TWO_OPT_MAX_ITERATIONS

    deadline = (time.monotonic() + time_budget_ms / 1000.0) if time_budget_ms else None

    improved = True
    route = list(slots)
    n = len(route)
    iteration = 0
    while improved and iteration < max_iterations:
        improved = False
        iteration += 1
        for i in range(1, n - 2):
            if deadline is not None and time.monotonic() > deadline:
                return route
            for j in range(i + 1, n):
                if j - i == 1:
                    continue
                # Переход между слотами: выход i-1 → вход i и выход j-1 → вход j
                d_before = (_dist(route[i - 1][1], route[i][0]) +
                            _dist(route[j - 1][1], route[j][0]))
                d_after = (_dist(route[i - 1][1], route[j - 1][0]) +
                           _dist(route[i][1], route[j][0]))
                if d_after < d_before - 1e-9:
                    route[i:j] = route[i:j][::-1]
                    improved = True
    return route


def nearest_neighbor_tsp(points):
    """Жадный nearest-neighbor + 2-opt для отверстий."""
    if not points:
        return []
    visited = [False] * len(points)
    path = [0]
    visited[0] = True
    for _ in range(1, len(points)):
        last_point = path[-1]
        nearest_point = None
        nearest_distance = float('inf')
        for j in range(len(points)):
            if not visited[j]:
                distance = _dist(points[last_point], points[j])
                if distance < nearest_distance:
                    nearest_distance = distance
                    nearest_point = j
        if nearest_point is not None:
            path.append(nearest_point)
            visited[nearest_point] = True
    ordered = [points[i] for i in path]
    return two_opt(ordered)


def nearest_neighbor_tsp_slots(slots):
    """Nearest-neighbor + 2-opt для слотов."""
    if not slots:
        return []
    if len(slots) == 1:
        return slots
    visited = [False] * len(slots)
    path = [0]
    visited[0] = True
    for _ in range(1, len(slots)):
        last_slot = slots[path[-1]]
        last_pos = last_slot[1]
        nearest_idx = None
        nearest_distance = float('inf')
        for j in range(len(slots)):
            if not visited[j]:
                sx, sy = slots[j][0]
                distance = ((last_pos[0] - sx) ** 2 + (last_pos[1] - sy) ** 2) ** 0.5
                if distance < nearest_distance:
                    nearest_distance = distance
                    nearest_idx = j
        if nearest_idx is not None:
            path.append(nearest_idx)
            visited[nearest_idx] = True
    ordered = [slots[i] for i in path]
    return two_opt_slots(ordered)
