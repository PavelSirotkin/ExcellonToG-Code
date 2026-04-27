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


class TestTwoOptIterationLimit:
    def test_respects_max_iterations_points(self):
        """two_opt должен останавливаться после max_iterations."""
        # Создаём большой набор точек
        points = [(i, i % 10) for i in range(100)]
        # С лимитом 1 итерация должна завершиться быстро
        result = two_opt(points, max_iterations=1)
        assert len(result) == len(points)
        assert set(result) == set(points)

    def test_respects_max_iterations_slots(self):
        """two_opt_slots должен останавливаться после max_iterations."""
        # Создаём большой набор слотов
        slots = [((i, i % 10), (i + 1, (i + 1) % 10)) for i in range(100)]
        # С лимитом 1 итерация должна завершиться быстро
        result = two_opt_slots(slots, max_iterations=1)
        assert len(result) == len(slots)
        assert set(result) == set(slots)

    def test_default_limit_used_when_none(self):
        """При max_iterations=None должен использоваться дефолтный лимит."""
        points = [(i, i) for i in range(50)]
        # Не должно зависнуть
        result = two_opt(points, max_iterations=None)
        assert len(result) == len(points)

    def test_zero_iterations_returns_input(self):
        """При max_iterations=0 должен вернуть исходный маршрут."""
        points = [(0, 0), (10, 10), (1, 1), (9, 9), (2, 2)]
        result = two_opt(points, max_iterations=0)
        assert result == points


class TestTwoOptTimeBudget:
    def test_time_budget_stops_early(self):
        """time_budget_ms должен прерывать оптимизацию даже при большом max_iterations."""
        import time
        # Большой набор точек, чтобы 2-opt занимал заметное время
        points = [(i * 0.1, (i * 7) % 100) for i in range(500)]
        start = time.monotonic()
        # 50 мс — много меньше времени, нужного на полную сходимость
        result = two_opt(points, max_iterations=10000, time_budget_ms=50)
        elapsed_ms = (time.monotonic() - start) * 1000
        # Бюджет 50 мс + накладные на проверку deadline между i-итерациями.
        # Допуск 500 мс (с большим запасом для медленных CI).
        assert elapsed_ms < 500, f"Превышен бюджет: {elapsed_ms:.1f} ms"
        # Маршрут должен сохранить состав точек
        assert len(result) == len(points)
        assert set(result) == set(points)

    def test_time_budget_none_no_limit(self):
        """time_budget_ms=None означает «без лимита по времени» (только по итерациям)."""
        points = [(0, 0), (10, 10), (1, 1), (9, 9), (2, 2)]
        # Без лимита — должен сходиться за разумное время
        result = two_opt(points, time_budget_ms=None)
        assert set(result) == set(points)

    def test_time_budget_slots(self):
        """time_budget_ms работает и для two_opt_slots."""
        import time
        slots = [((i, 0), (i + 1, 1)) for i in range(500)]
        start = time.monotonic()
        result = two_opt_slots(slots, max_iterations=10000, time_budget_ms=50)
        elapsed_ms = (time.monotonic() - start) * 1000
        assert elapsed_ms < 500, f"Превышен бюджет: {elapsed_ms:.1f} ms"
        assert len(result) == len(slots)
