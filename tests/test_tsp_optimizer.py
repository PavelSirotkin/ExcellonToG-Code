"""
Тесты для модуля tsp_optimizer.
"""
import pytest
import math
from core.tsp_optimizer import (
    nearest_neighbor_tsp,
    nearest_neighbor_tsp_slots,
    two_opt,
    two_opt_slots,
)


class TestNearestNeighborTSP:
    def test_empty_input(self):
        assert nearest_neighbor_tsp([]) == []

    def test_single_point(self):
        points = [(0, 0)]
        result = nearest_neighbor_tsp(points)
        assert len(result) == 1
        assert result[0] == (0, 0)

    def test_two_points(self):
        points = [(0, 0), (10, 10)]
        result = nearest_neighbor_tsp(points)
        assert len(result) == 2
        assert set(result) == set(points)

    def test_multiple_points_returns_same_count(self):
        points = [(i, i) for i in range(10)]
        result = nearest_neighbor_tsp(points)
        assert len(result) == len(points)
        assert set(result) == set(points)

    def test_result_is_permutation(self):
        points = [(1, 2), (3, 4), (5, 6), (7, 8)]
        result = nearest_neighbor_tsp(points)
        assert len(result) == len(points)
        for p in result:
            assert p in points


class TestTwoOpt:
    def test_empty_input(self):
        assert two_opt([]) == []

    def test_fewer_than_4_points(self):
        points = [(0, 0), (1, 1), (2, 2)]
        result = two_opt(points)
        assert result == points

    def test_improves_route(self):
        # Создаём заведомо плохой маршрут: зигзаг
        points = [(0, 0), (10, 10), (1, 1), (9, 9), (2, 2)]
        result = two_opt(points)
        # После 2-opt маршрут должен быть не хуже (по длине)
        def total_dist(pts):
            return sum(math.hypot(pts[i][0] - pts[i-1][0], pts[i][1] - pts[i-1][1])
                       for i in range(1, len(pts)))
        assert total_dist(result) <= total_dist(points) + 1e-9


class TestNearestNeighborSlots:
    def test_empty_input(self):
        assert nearest_neighbor_tsp_slots([]) == []

    def test_single_slot(self):
        slots = [((0, 0), (5, 5))]
        result = nearest_neighbor_tsp_slots(slots)
        assert len(result) == 1

    def test_multiple_slots(self):
        slots = [
            ((0, 0), (2, 2)),
            ((10, 10), (12, 12)),
            ((5, 5), (7, 7)),
        ]
        result = nearest_neighbor_tsp_slots(slots)
        assert len(result) == 3
        assert set(result) == set(slots)


class TestTwoOptSlots:
    def test_empty_input(self):
        assert two_opt_slots([]) == []

    def test_fewer_than_4_slots(self):
        slots = [((0, 0), (1, 1)), ((2, 2), (3, 3)), ((4, 4), (5, 5))]
        result = two_opt_slots(slots)
        assert result == slots

    def test_preserves_slot_structure(self):
        slots = [
            ((0, 0), (1, 1)),
            ((10, 10), (11, 11)),
            ((5, 5), (6, 6)),
            ((15, 15), (16, 16)),
        ]
        result = two_opt_slots(slots)
        assert len(result) == 4
        # Каждый слот должен остаться тем же (start, end)
        for s in result:
            assert s in slots
