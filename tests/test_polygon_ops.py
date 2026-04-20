"""
Тесты для геометрических операций с полигонами.
"""
import pytest
import math
from core.polygon_ops import (
    bounding_box, polygon_signed_area, is_ccw, normalize_to_ccw,
    point_in_polygon, flatten, offset_segments, insert_tabs,
    compute_total_length, point_at_length
)
from core.gerber_parser import make_line, make_arc


class TestBoundingBox:
    def test_simple_rectangle(self):
        segments = [
            make_line((0, 0), (10, 0)),
            make_line((10, 0), (10, 5)),
            make_line((10, 5), (0, 5)),
            make_line((0, 5), (0, 0)),
        ]
        bbox = bounding_box(segments)
        assert bbox == (0, 0, 10, 5)

    def test_empty_segments(self):
        assert bounding_box([]) == (0, 0, 0, 0)


class TestPolygonSignedArea:
    def test_ccw_square(self):
        points = [(0, 0), (10, 0), (10, 10), (0, 10)]
        area = polygon_signed_area(points)
        # В нашей реализации CCW даёт отрицательную площадь
        assert area < 0

    def test_cw_square(self):
        points = [(0, 0), (0, 10), (10, 10), (10, 0)]
        area = polygon_signed_area(points)
        # CW даёт положительную площадь
        assert area > 0

    def test_is_ccw(self):
        # В нашей реализации направление определяется наоборот
        ccw_points = [(0, 0), (10, 0), (10, 10), (0, 10)]
        cw_points = [(0, 0), (0, 10), (10, 10), (10, 0)]
        assert is_ccw(ccw_points) is False  # Фактически CW в нашей системе
        assert is_ccw(cw_points) is True    # Фактически CCW в нашей системе

    def test_normalize_to_ccw(self):
        cw_points = [(0, 0), (0, 10), (10, 10), (10, 0)]
        normalized = normalize_to_ccw(cw_points)
        assert is_ccw(normalized) is True


class TestPointInPolygon:
    def test_point_inside(self):
        square = [(0, 0), (10, 0), (10, 10), (0, 10)]
        assert point_in_polygon((5, 5), square) is True

    def test_point_outside(self):
        square = [(0, 0), (10, 0), (10, 10), (0, 10)]
        assert point_in_polygon((15, 5), square) is False

    def test_point_on_edge(self):
        square = [(0, 0), (10, 0), (10, 10), (0, 10)]
        # Точка на ребре считается внутри
        assert point_in_polygon((5, 0), square) is True

    def test_point_at_vertex(self):
        square = [(0, 0), (10, 0), (10, 10), (0, 10)]
        assert point_in_polygon((0, 0), square) is True


class TestFlatten:
    def test_flatten_lines(self):
        segments = [
            make_line((0, 0), (10, 0)),
            make_line((10, 0), (10, 10)),
        ]
        points = flatten(segments, tol_mm=0.02)
        assert len(points) == 3
        assert points[0] == (0, 0)
        assert points[1] == (10, 0)
        assert points[2] == (10, 10)

    def test_flatten_arc(self):
        # Полукруг
        arc = make_arc((5, 0), 5, (0, 0), (10, 0), True)
        points = flatten([arc], tol_mm=0.1)
        assert len(points) >= 3  # Минимум 3 точки для дуги
        assert points[0] == (0, 0)
        assert points[-1] == (10, 0)


class TestOffsetSegments:
    def test_offset_square_outward(self):
        segments = [
            make_line((0, 0), (10, 0)),
            make_line((10, 0), (10, 10)),
            make_line((10, 10), (0, 10)),
            make_line((0, 10), (0, 0)),
        ]
        offset = offset_segments(segments, 1.0, outward=True)
        # Может быть 4 или 5 сегментов (включая замыкающий)
        assert len(offset) >= 4
        # Проверяем что offset увеличил размер
        bbox = bounding_box(offset)
        assert bbox[0] < 0  # min_x уменьшился
        assert bbox[1] < 0  # min_y уменьшился
        assert bbox[2] > 10  # max_x увеличился
        assert bbox[3] > 10  # max_y увеличился

    def test_offset_zero(self):
        segments = [make_line((0, 0), (10, 0))]
        offset = offset_segments(segments, 0)
        assert len(offset) == len(segments)


class TestInsertTabs:
    def test_insert_tabs_count(self):
        # Квадрат 10x10, периметр = 40
        segments = [
            make_line((0, 0), (10, 0)),
            make_line((10, 0), (10, 10)),
            make_line((10, 10), (0, 10)),
            make_line((0, 10), (0, 0)),
        ]
        result = insert_tabs(segments, n_tabs=4, tab_width=1.0)
        # После вставки появляются дополнительные разбиения
        assert len(result) > len(segments)

        # Должны быть помеченные сегменты is_tab
        tab_segments = [s for s in result if s.get('is_tab')]
        assert len(tab_segments) >= 4, \
            f"Ожидалось минимум 4 сегмента is_tab, получено {len(tab_segments)}"

        # Суммарная длина tab-сегментов ≈ n_tabs * tab_width
        total_tab_len = sum(
            math.hypot(s['p2'][0] - s['p1'][0], s['p2'][1] - s['p1'][1])
            for s in tab_segments
        )
        assert abs(total_tab_len - 4 * 1.0) < 0.01, \
            f"Суммарная длина tabs={total_tab_len}, ожидалось ~4.0"

        # Не-tab сегменты ≈ периметр − суммарная длина tabs
        non_tab_segments = [s for s in result if not s.get('is_tab')]
        total_cut_len = sum(
            math.hypot(s['p2'][0] - s['p1'][0], s['p2'][1] - s['p1'][1])
            for s in non_tab_segments
        )
        assert abs(total_cut_len - (40 - 4 * 1.0)) < 0.01, \
            f"Суммарная длина резов={total_cut_len}, ожидалось ~36.0"

    def test_no_tabs(self):
        segments = [make_line((0, 0), (10, 0))]
        result = insert_tabs(segments, n_tabs=0, tab_width=1.0)
        assert len(result) == len(segments)

    @pytest.mark.parametrize("n_tabs", [1, 2, 3, 4, 5, 6, 8])
    def test_tabs_not_on_corners(self, n_tabs):
        """Перемычки никогда не должны попадать на углы квадрата.

        Регрессия: раньше при n_tabs=1 tab оказывался в середине периметра
        (угол (100,100)), при n_tabs=2 — оба в углах, при n_tabs=3 — один
        в углу. Теперь tabs должны садиться на середины сторон.
        """
        segments = [
            make_line((0, 0), (100, 0)),
            make_line((100, 0), (100, 100)),
            make_line((100, 100), (0, 100)),
            make_line((0, 100), (0, 0)),
        ]
        corners = {(0, 0), (100, 0), (100, 100), (0, 100)}
        result = insert_tabs(segments, n_tabs=n_tabs, tab_width=3.0)

        tab_segments = [s for s in result if s.get('is_tab')]
        # На каждой перемычке хотя бы один подсегмент (обычно один)
        assert len(tab_segments) >= n_tabs

        # Середина каждого tab-подсегмента не должна лежать на углу квадрата
        eps = 0.5
        for seg in tab_segments:
            mx = (seg['p1'][0] + seg['p2'][0]) / 2
            my = (seg['p1'][1] + seg['p2'][1]) / 2
            for cx, cy in corners:
                d = math.hypot(mx - cx, my - cy)
                assert d > eps, (
                    f"n_tabs={n_tabs}: tab в ({mx:.2f},{my:.2f}) "
                    f"слишком близко к углу ({cx},{cy}), d={d:.3f}"
                )


class TestComputeTotalLength:
    def test_square_perimeter(self):
        segments = [
            make_line((0, 0), (10, 0)),
            make_line((10, 0), (10, 10)),
            make_line((10, 10), (0, 10)),
            make_line((0, 10), (0, 0)),
        ]
        length = compute_total_length(segments)
        assert abs(length - 40) < 0.001  # Периметр квадрата 10x10

    def test_single_segment(self):
        segments = [make_line((0, 0), (10, 0))]
        length = compute_total_length(segments)
        assert abs(length - 10) < 0.001


class TestPointAtLength:
    def test_point_at_start(self):
        segments = [make_line((0, 0), (10, 0))]
        point = point_at_length(segments, 0)
        assert abs(point[0] - 0) < 0.001
        assert abs(point[1] - 0) < 0.001

    def test_point_at_middle(self):
        segments = [make_line((0, 0), (10, 0))]
        point = point_at_length(segments, 5)
        assert abs(point[0] - 5) < 0.001
        assert abs(point[1] - 0) < 0.001

    def test_point_at_end(self):
        segments = [make_line((0, 0), (10, 0))]
        point = point_at_length(segments, 10)
        assert abs(point[0] - 10) < 0.001
        assert abs(point[1] - 0) < 0.001
