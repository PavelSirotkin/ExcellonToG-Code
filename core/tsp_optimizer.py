"""
Алгоритмы оптимизации маршрута (TSP — Travelling Salesman Problem).
Используют nearest neighbour + 2-opt для упорядочивания отверстий и слотов.
"""
import math


def _dist(a, b):
    """Евклидово расстояние между двумя точками."""
    return math.sqrt((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2)


def two_opt(points):
    """2-opt улучшение маршрута: итеративно переворачивает подотрезки,
    пока это сокращает суммарный путь."""
    if len(points) < 4:
        return points

    def total_distance(route):
        return sum(_dist(route[i], route[i + 1]) for i in range(len(route) - 1))

    improved = True
    route = list(points)
    n = len(route)
    while improved:
        improved = False
        for i in range(1, n - 2):
            for j in range(i + 1, n):
                if j - i == 1:
                    continue
                d_before = _dist(route[i - 1], route[i]) + _dist(route[j - 1], route[j])
                d_after = _dist(route[i - 1], route[j - 1]) + _dist(route[i], route[j])
                if d_after < d_before - 1e-10:
                    route[i:j] = route[i:j][::-1]
                    improved = True
    return route


def two_opt_slots(slots):
    """2-opt для слотов: точкой входа считается start, точкой выхода — end."""
    if len(slots) < 4:
        return slots

    improved = True
    route = list(slots)
    n = len(route)
    while improved:
        improved = False
        for i in range(1, n - 2):
            for j in range(i + 1, n):
                if j - i == 1:
                    continue
                # Переход между слотами: выход i-1 → вход i и выход j-1 → вход j
                d_before = (_dist(route[i - 1][1], route[i][0]) +
                            _dist(route[j - 1][1], route[j][0]))
                d_after = (_dist(route[i - 1][1], route[j - 1][0]) +
                           _dist(route[i][1], route[j][0]))
                if d_after < d_before - 1e-10:
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
