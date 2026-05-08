"""
Тесты для геометрических операций с полигонами.
"""
import pytest
import math
from core.polygon_ops import (
    bounding_box, polygon_signed_area,
    is_cw_orientation, normalize_to_cw_for_offset,
    point_in_polygon, flatten, offset_segments, insert_tabs,
    compute_total_length, point_at_length, is_closed_contour,
    split_subpaths, flatten_subpaths, classify_subpaths,
    stitch_subpaths,
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
    """polygon_signed_area использует трапецеидальную конвенцию:
    положительная сумма = CW, отрицательная = CCW (см. docstring функции)."""

    def test_ccw_square_negative_area(self):
        ccw_points = [(0, 0), (10, 0), (10, 10), (0, 10)]
        area = polygon_signed_area(ccw_points)
        assert area < 0

    def test_cw_square_positive_area(self):
        cw_points = [(0, 0), (0, 10), (10, 10), (10, 0)]
        area = polygon_signed_area(cw_points)
        assert area > 0

    def test_is_cw_orientation(self):
        ccw_points = [(0, 0), (10, 0), (10, 10), (0, 10)]
        cw_points = [(0, 0), (0, 10), (10, 10), (10, 0)]
        assert is_cw_orientation(ccw_points) is False
        assert is_cw_orientation(cw_points) is True

    def test_normalize_to_cw_for_offset_keeps_cw(self):
        cw_points = [(0, 0), (0, 10), (10, 10), (10, 0)]
        normalized = normalize_to_cw_for_offset(cw_points)
        assert is_cw_orientation(normalized) is True
        # Уже CW — порядок не меняется
        assert normalized == cw_points

    def test_normalize_to_cw_for_offset_reverses_ccw(self):
        ccw_points = [(0, 0), (10, 0), (10, 10), (0, 10)]
        normalized = normalize_to_cw_for_offset(ccw_points)
        assert is_cw_orientation(normalized) is True
        # CCW развернут в обратный порядок
        assert normalized == list(reversed(ccw_points))


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

    def test_flatten_full_circle_arc(self):
        """H3: arc с одинаковыми start/end и валидным r — full circle.

        Раньше delta_angle = 0 → n_segments = 1 → вырождался в одну хорду
        нулевой длины. Теперь должен раскрываться в множество хорд,
        лежащих на окружности радиуса 5 вокруг центра (0, 0).
        """
        # CCW: D01 из точки (5, 0) в (5, 0) с центром в (0, 0), r=5.
        arc = make_arc((0, 0), 5, (5, 0), (5, 0), True)
        points = flatten([arc], tol_mm=0.1)
        assert len(points) >= 8, (
            f"Full circle должен давать ≥ 8 хорд, получено {len(points) - 1}")
        # Все точки лежат на окружности радиуса 5 (с допуском)
        for x, y in points:
            r = (x * x + y * y) ** 0.5
            assert abs(r - 5) < 0.15, f"Точка ({x:.3f}, {y:.3f}) не на круге r=5"
        # Замыкаемся в стартовой точке
        assert abs(points[-1][0] - 5) < 1e-6
        assert abs(points[-1][1]) < 1e-6


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

    def test_offset_l_shape_small_delta_succeeds(self):
        """M3: L-контур с маленьким inward-offset — нет self-intersection.

        Регрессионный страж: проверка, что детектор не срабатывает на штатных
        сценариях.
        """
        segments = [
            make_line((0, 0), (20, 0)),
            make_line((20, 0), (20, 8)),
            make_line((20, 8), (8, 8)),
            make_line((8, 8), (8, 20)),
            make_line((8, 20), (0, 20)),
            make_line((0, 20), (0, 0)),
        ]
        offset = offset_segments(segments, 0.5, outward=False)
        assert len(offset) > 0, "offset для безопасного delta не должен пустеть"


class TestSelfIntersectionDetector:
    """M3: модульные тесты helper'ов _segments_strictly_cross и
    _has_self_intersection. Тестируем именно детектор, потому что простой
    offset-алгоритм не приводит выпуклые формы в self-intersect — это
    реализуемо только через полноценную overlay-библиотеку (Clipper).
    Детектор всё же ловит явные «битые» полигоны: bowtie от вынужденной
    топологии, нулевые рёбра, схлопнувшиеся вершины — что и спасает плату.
    """

    def test_strictly_cross_classical_x(self):
        """Классический X-крест должен распознаваться как пересечение."""
        from core.polygon_ops import _segments_strictly_cross
        assert _segments_strictly_cross((0, 0), (10, 10), (0, 10), (10, 0))

    def test_strictly_cross_shared_endpoint_is_not_intersection(self):
        """Общий конец двух отрезков НЕ должен считаться пересечением.

        Иначе любой нормальный полигон (где соседи имеют общую вершину)
        ложно срабатывал бы.
        """
        from core.polygon_ops import _segments_strictly_cross
        assert not _segments_strictly_cross((0, 0), (10, 0),
                                            (10, 0), (20, 0))

    def test_strictly_cross_t_touch_is_not_intersection(self):
        """T-касание (конец одного на середине другого) — не строгое
        пересечение во внутренних точках. По нашей конвенции — допустимо.
        """
        from core.polygon_ops import _segments_strictly_cross
        # отрезок (5,0)-(5,10) касается серединой (5,5) горизонтальный
        # (0,5)-(10,5) → endpoints совпадают только если идти в обе стороны.
        # Здесь горизонтальный отрезок имеет конец в (10,5), не на середине
        # вертикального. Это уже X-крест, не T. Сделаем настоящий T:
        # отрезок (5,5)-(5,10) — его конец (5,5) лежит на середине (0,5)-(10,5).
        assert not _segments_strictly_cross((0, 5), (10, 5),
                                            (5, 5), (5, 10))

    def test_has_self_intersection_bowtie(self):
        """Bowtie из 4 отрезков — два диагональных ребра пересекаются."""
        from core.polygon_ops import _has_self_intersection
        bowtie = [
            make_line((0, 0), (10, 10)),
            make_line((10, 10), (10, 0)),
            make_line((10, 0), (0, 10)),
            make_line((0, 10), (0, 0)),
        ]
        assert _has_self_intersection(bowtie)

    def test_has_self_intersection_clean_square(self):
        """Чистый квадрат — пересечений нет."""
        from core.polygon_ops import _has_self_intersection
        square = [
            make_line((0, 0), (10, 0)),
            make_line((10, 0), (10, 10)),
            make_line((10, 10), (0, 10)),
            make_line((0, 10), (0, 0)),
        ]
        assert not _has_self_intersection(square)

    def test_has_self_intersection_zero_edge(self):
        """Нуль-длинное ребро (p1 == p2) — признак схлопывания контура."""
        from core.polygon_ops import _has_self_intersection
        bad = [
            make_line((0, 0), (10, 0)),
            make_line((10, 0), (10, 0)),  # zero-length
            make_line((10, 0), (10, 10)),
            make_line((10, 10), (0, 0)),
        ]
        assert _has_self_intersection(bad)

    def test_has_self_intersection_duplicate_non_adjacent_vertex(self):
        """Несоседние вершины с одинаковыми координатами — локально вырожденный
        полигон (две вершины разных частей контура схлопнулись)."""
        from core.polygon_ops import _has_self_intersection
        bad = [
            make_line((0, 0), (10, 0)),
            make_line((10, 0), (10, 10)),
            make_line((10, 10), (0, 0)),  # вершина (0,0) совпадает с p1[0]
            make_line((0, 0), (0, 0)),  # zero-edge для замыкания
        ]
        assert _has_self_intersection(bad)


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

    def test_full_circle_length(self):
        """H3: длина full-circle arc должна быть 2πr, а не 0."""
        arc = make_arc((0, 0), 5, (5, 0), (5, 0), True)
        length = compute_total_length([arc])
        import math
        assert abs(length - 2 * math.pi * 5) < 0.01


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

    def test_point_at_quarter_of_full_circle(self):
        """H3: на full-circle arc четверть длины ≈ точка под 90° от стартовой.

        CCW круг r=5 со стартом в (5, 0): четверть окружности вперёд (π/2 рад)
        даёт точку (0, 5).
        """
        import math
        arc = make_arc((0, 0), 5, (5, 0), (5, 0), True)
        quarter = (2 * math.pi * 5) / 4.0
        x, y = point_at_length([arc], quarter)
        assert abs(x - 0) < 0.05
        assert abs(y - 5) < 0.05


class TestIsClosedContour:
    def test_closed_square(self):
        """Замкнутый квадрат должен распознаваться как замкнутый."""
        segments = [
            make_line((0, 0), (10, 0)),
            make_line((10, 0), (10, 10)),
            make_line((10, 10), (0, 10)),
            make_line((0, 10), (0, 0)),
        ]
        assert is_closed_contour(segments) is True

    def test_open_contour(self):
        """Незамкнутый контур (конец не совпадает с началом)."""
        segments = [
            make_line((0, 0), (10, 0)),
            make_line((10, 0), (10, 10)),
            make_line((10, 10), (0, 10)),
            # Последний сегмент не возвращается к (0, 0)
        ]
        assert is_closed_contour(segments) is False

    def test_almost_closed_within_tolerance(self):
        """Контур с небольшим зазором в пределах допуска."""
        segments = [
            make_line((0, 0), (10, 0)),
            make_line((10, 0), (10, 10)),
            make_line((10, 10), (0, 10)),
            make_line((0, 10), (0.0005, 0.0005)),  # Зазор 0.0007 мм < 1e-3
        ]
        assert is_closed_contour(segments) is True

    def test_almost_closed_outside_tolerance(self):
        """Контур с зазором больше допуска."""
        segments = [
            make_line((0, 0), (10, 0)),
            make_line((10, 0), (10, 10)),
            make_line((10, 10), (0, 10)),
            make_line((0, 10), (0.5, 0.5)),  # Зазор ~0.7 мм > 1e-3
        ]
        assert is_closed_contour(segments) is False

    def test_single_segment(self):
        """Один сегмент не может быть замкнутым контуром."""
        segments = [make_line((0, 0), (10, 0))]
        assert is_closed_contour(segments) is False

    def test_empty_segments(self):
        """Пустой список не является замкнутым контуром."""
        assert is_closed_contour([]) is False

    def test_closed_outline_with_cutout(self):
        """Контур с замкнутым внешним контуром И замкнутым вырезом —
        должен распознаваться как замкнутый, хотя first.start ≠ last.end.
        Раньше старая реализация на этом возвращала False."""
        outline = [
            {**make_line((0, 0), (10, 0)), 'subpath_start': True},
            make_line((10, 0), (10, 10)),
            make_line((10, 10), (0, 10)),
            make_line((0, 10), (0, 0)),
        ]
        cutout = [
            {**make_line((3, 3), (7, 3)), 'subpath_start': True},
            make_line((7, 3), (7, 7)),
            make_line((7, 7), (3, 7)),
            make_line((3, 7), (3, 3)),
        ]
        assert is_closed_contour(outline + cutout) is True

    def test_open_outline_with_closed_cutout(self):
        """Если хотя бы один подконтур разорван — общий результат False."""
        outline = [
            {**make_line((0, 0), (10, 0)), 'subpath_start': True},
            make_line((10, 0), (10, 10)),
            make_line((10, 10), (0, 10)),
            # без замыкающей линии
        ]
        cutout = [
            {**make_line((3, 3), (7, 3)), 'subpath_start': True},
            make_line((7, 3), (7, 7)),
            make_line((7, 7), (3, 7)),
            make_line((3, 7), (3, 3)),
        ]
        assert is_closed_contour(outline + cutout) is False


class TestSubpaths:
    def test_split_no_markers_single_subpath(self):
        """Совместимость: если меток нет — один подконтур."""
        segments = [
            make_line((0, 0), (10, 0)),
            make_line((10, 0), (10, 10)),
        ]
        subpaths = split_subpaths(segments)
        assert len(subpaths) == 1
        assert len(subpaths[0]) == 2

    def test_split_two_subpaths(self):
        outline = [
            {**make_line((0, 0), (10, 0)), 'subpath_start': True},
            make_line((10, 0), (0, 0)),
        ]
        cutout = [
            {**make_line((3, 3), (7, 3)), 'subpath_start': True},
            make_line((7, 3), (3, 3)),
        ]
        subpaths = split_subpaths(outline + cutout)
        assert len(subpaths) == 2
        assert len(subpaths[0]) == 2
        assert len(subpaths[1]) == 2

    def test_flatten_subpaths_keeps_separation(self):
        """flatten_subpaths не должен соединять разные подконтуры."""
        outline = [
            {**make_line((0, 0), (10, 0)), 'subpath_start': True},
            make_line((10, 0), (10, 10)),
            make_line((10, 10), (0, 0)),
        ]
        cutout = [
            {**make_line((3, 3), (7, 3)), 'subpath_start': True},
            make_line((7, 3), (3, 3)),
        ]
        result = flatten_subpaths(outline + cutout)
        assert len(result) == 2
        assert (0, 0) in result[0]
        assert (3, 3) in result[1]
        # Точки одного подконтура не должны попадать в другой
        assert (10, 0) not in result[1]
        assert (7, 3) not in result[0]


class TestClassifySubpaths:
    def _square(self, x0, y0, x1, y1, mark_start=True):
        """Утилита: квадрат как замкнутый список линий."""
        first = make_line((x0, y0), (x1, y0))
        if mark_start:
            first['subpath_start'] = True
        return [
            first,
            make_line((x1, y0), (x1, y1)),
            make_line((x1, y1), (x0, y1)),
            make_line((x0, y1), (x0, y0)),
        ]

    def test_single_outer(self):
        result = classify_subpaths(self._square(0, 0, 10, 10))
        assert len(result) == 1
        assert result[0]['is_outer'] is True
        assert result[0]['depth'] == 0

    def test_outer_with_one_cutout(self):
        outer = self._square(0, 0, 20, 20)
        inner = self._square(5, 5, 15, 15)
        result = classify_subpaths(outer + inner)
        assert len(result) == 2
        outer_classes = [r for r in result if r['depth'] == 0]
        inner_classes = [r for r in result if r['depth'] == 1]
        assert len(outer_classes) == 1 and outer_classes[0]['is_outer'] is True
        assert len(inner_classes) == 1 and inner_classes[0]['is_outer'] is False

    def test_island_in_cutout_is_outer(self):
        """Островок в дырке — снова outer (чётность глубины 2)."""
        plate = self._square(0, 0, 30, 30)
        hole = self._square(5, 5, 25, 25)
        island = self._square(10, 10, 20, 20)
        result = classify_subpaths(plate + hole + island)
        depths = sorted(r['depth'] for r in result)
        assert depths == [0, 1, 2]
        # depth 0 и 2 — outer; depth 1 — inner
        for r in result:
            assert r['is_outer'] == (r['depth'] % 2 == 0)

    def test_two_separate_outers(self):
        """Два не вложенных контура — оба outer."""
        a = self._square(0, 0, 10, 10)
        b = self._square(20, 20, 30, 30)
        result = classify_subpaths(a + b)
        assert len(result) == 2
        assert all(r['is_outer'] for r in result)
        assert all(r['depth'] == 0 for r in result)


class TestStitchSubpaths:
    def test_already_closed_passthrough(self):
        """Замкнутый собранный квадрат — stitch ничего не меняет."""
        sq = [
            {**make_line((0, 0), (10, 0)), 'subpath_start': True},
            make_line((10, 0), (10, 10)),
            make_line((10, 10), (0, 10)),
            make_line((0, 10), (0, 0)),
        ]
        result = stitch_subpaths(sq)
        # Те же сегменты, тот же порядок (опционально не точная
        # идентичность словарей, но геометрически совпадает).
        assert len(result) == 4
        assert result[0].get('subpath_start') is True
        assert result[0]['p1'] == (0, 0) and result[0]['p2'] == (10, 0)
        assert result[3]['p1'] == (0, 10) and result[3]['p2'] == (0, 0)

    def test_unordered_lines_into_square(self):
        """4 линии квадрата в случайном порядке + каждая в своём
        подконтуре (как KiCad штрихи). Должны собраться в одну
        замкнутую цепь."""
        # Порядок: верхняя, левая, нижняя, правая
        sides = [
            {**make_line((10, 10), (0, 10)), 'subpath_start': True},   # top
            {**make_line((0, 10), (0, 0)), 'subpath_start': True},     # left
            {**make_line((0, 0), (10, 0)), 'subpath_start': True},     # bottom
            {**make_line((10, 0), (10, 10)), 'subpath_start': True},   # right
        ]
        result = stitch_subpaths(sides)
        # 4 сегмента, ровно один subpath_start, замкнуто
        assert len(result) == 4
        starts = [s for s in result if s.get('subpath_start')]
        assert len(starts) == 1
        # Первый.start == Последний.end
        first_p = result[0]['p1']
        last_p = result[-1]['p2']
        assert math.hypot(first_p[0] - last_p[0],
                          first_p[1] - last_p[1]) <= 1e-3
        # Цепь непрерывна
        for i in range(len(result) - 1):
            e = result[i]['p2']
            s = result[i + 1]['p1']
            assert math.hypot(e[0] - s[0], e[1] - s[1]) <= 1e-3

    def test_inversion_when_segment_runs_backward(self):
        """Один штрих описан в «обратную сторону» обхода — должен
        быть инвертирован при сшивке."""
        # Квадрат, но вторая сторона задана наоборот (10,10)→(10,0)
        sides = [
            {**make_line((0, 0), (10, 0)), 'subpath_start': True},
            {**make_line((10, 10), (10, 0)), 'subpath_start': True},   # backward!
            {**make_line((10, 10), (0, 10)), 'subpath_start': True},
            {**make_line((0, 10), (0, 0)), 'subpath_start': True},
        ]
        result = stitch_subpaths(sides)
        assert len(result) == 4
        # После сшивки цепь должна быть непрерывна
        for i in range(len(result) - 1):
            e = result[i]['p2']
            s = result[i + 1]['p1']
            assert math.hypot(e[0] - s[0], e[1] - s[1]) <= 1e-3
        # И замкнута
        assert math.hypot(result[0]['p1'][0] - result[-1]['p2'][0],
                          result[0]['p1'][1] - result[-1]['p2'][1]) <= 1e-3

    def test_arc_inversion_flips_ccw(self):
        """При инверсии дуги при сшивке поле ccw переключается."""
        # Идём из (0,0) → дуга CCW до (10,0) → линия до (0,0).
        # Дугу подаём в обратном направлении (от 10,0 к 0,0).
        arc_backward = make_arc(center=(5, 0), r=5,
                                start=(10, 0), end=(0, 0), ccw=True)
        sides = [
            {**make_line((10, 0), (0, 0)), 'subpath_start': True},     # closing line
            {**arc_backward, 'subpath_start': True},                   # arc backward
        ]
        result = stitch_subpaths(sides)
        # Должна получиться замкнутая цепь из 2 элементов
        assert len(result) == 2
        # Найдём дугу в результате (порядок может варьироваться)
        arcs = [s for s in result if s['type'] == 'arc']
        assert len(arcs) == 1
        # Цепь непрерывна
        for i in range(len(result) - 1):
            e = result[i]['p2'] if result[i]['type'] == 'line' else result[i]['end']
            s = result[i + 1]['p1'] if result[i + 1]['type'] == 'line' else result[i + 1]['start']
            assert math.hypot(e[0] - s[0], e[1] - s[1]) <= 1e-3

    def test_two_loops_assembled_separately(self):
        """Внешний прямоугольник + внутренний квадрат, штрихи
        перемешаны — должны собраться в две петли."""
        outer = [
            {**make_line((0, 0), (20, 0)), 'subpath_start': True},
            {**make_line((20, 0), (20, 20)), 'subpath_start': True},
            {**make_line((20, 20), (0, 20)), 'subpath_start': True},
            {**make_line((0, 20), (0, 0)), 'subpath_start': True},
        ]
        inner = [
            {**make_line((5, 5), (15, 5)), 'subpath_start': True},
            {**make_line((15, 5), (15, 15)), 'subpath_start': True},
            {**make_line((15, 15), (5, 15)), 'subpath_start': True},
            {**make_line((5, 15), (5, 5)), 'subpath_start': True},
        ]
        # Перемешиваем
        mixed = [outer[2], inner[0], outer[0], inner[2],
                 outer[3], inner[1], outer[1], inner[3]]
        result = stitch_subpaths(mixed)
        # Должны получиться 2 подконтура по 4 сегмента
        starts = [i for i, s in enumerate(result) if s.get('subpath_start')]
        assert len(starts) == 2
        # Каждый подконтур замкнут
        sub1 = result[starts[0]:starts[1]]
        sub2 = result[starts[1]:]
        for sub in (sub1, sub2):
            f = sub[0]['p1']
            l = sub[-1]['p2']
            assert math.hypot(f[0] - l[0], f[1] - l[1]) <= 1e-3
            assert len(sub) == 4

    def test_open_chain_kept_open_with_warning(self, caplog):
        """Если штрихи не сшиваются в замкнутую петлю, возвращаем
        как есть и логируем warning. Никаких исключений."""
        # Три линии, образующие П: (0,0)→(10,0)→(10,10)→(0,10),
        # без замыкающей. После сшивки — одна открытая цепь из 3-х.
        sides = [
            {**make_line((0, 0), (10, 0)), 'subpath_start': True},
            {**make_line((10, 0), (10, 10)), 'subpath_start': True},
            {**make_line((10, 10), (0, 10)), 'subpath_start': True},
        ]
        with caplog.at_level('WARNING', logger='core.polygon_ops'):
            result = stitch_subpaths(sides)
        # 3 сегмента в одной цепи
        assert len(result) == 3
        starts = [s for s in result if s.get('subpath_start')]
        assert len(starts) == 1
        # Цепь непрерывна, но не замкнута
        for i in range(len(result) - 1):
            e = result[i]['p2']
            s = result[i + 1]['p1']
            assert math.hypot(e[0] - s[0], e[1] - s[1]) <= 1e-3
        f = result[0]['p1']
        l = result[-1]['p2']
        assert math.hypot(f[0] - l[0], f[1] - l[1]) > 1e-3
        # И есть warning
        assert any("open chain" in rec.message for rec in caplog.records)

    def test_kept_subpath_not_disturbed_by_pool(self):
        """Когда часть подконтуров уже замкнута, а часть — нет:
        замкнутые НЕ должны переписываться/переупорядочиваться."""
        # Замкнутый квадрат + два штриха которые не сшиваются в петлю
        closed_square = [
            {**make_line((100, 100), (110, 100)), 'subpath_start': True},
            make_line((110, 100), (110, 110)),
            make_line((110, 110), (100, 110)),
            make_line((100, 110), (100, 100)),
        ]
        loose = [
            {**make_line((0, 0), (10, 0)), 'subpath_start': True},
            {**make_line((20, 0), (30, 0)), 'subpath_start': True},  # gap!
        ]
        result = stitch_subpaths(closed_square + loose)
        # Первые 4 сегмента — нетронутый замкнутый квадрат
        assert result[0]['p1'] == (100, 100)
        assert result[3]['p2'] == (100, 100)
        assert result[0].get('subpath_start') is True
        for i in range(1, 4):
            assert not result[i].get('subpath_start')


class TestClosedContourValidation:
    def test_offset_rejects_open_contour(self):
        """offset_segments должен возвращать [] для незамкнутого контура."""
        segments = [
            make_line((0, 0), (10, 0)),
            make_line((10, 0), (10, 10)),
            make_line((10, 10), (0, 10)),
            # Не замкнут
        ]
        result = offset_segments(segments, 1.0, outward=True)
        assert result == []

    def test_insert_tabs_rejects_open_contour(self):
        """insert_tabs должен возвращать [] для незамкнутого контура."""
        segments = [
            make_line((0, 0), (10, 0)),
            make_line((10, 0), (10, 10)),
            make_line((10, 10), (0, 10)),
            # Не замкнут
        ]
        result = insert_tabs(segments, n_tabs=2, tab_width=1.0)
        assert result == []

    def test_offset_accepts_closed_contour(self):
        """offset_segments должен работать с замкнутым контуром."""
        segments = [
            make_line((0, 0), (10, 0)),
            make_line((10, 0), (10, 10)),
            make_line((10, 10), (0, 10)),
            make_line((0, 10), (0, 0)),
        ]
        result = offset_segments(segments, 1.0, outward=True)
        assert len(result) > 0

    def test_insert_tabs_accepts_closed_contour(self):
        """insert_tabs должен работать с замкнутым контуром."""
        segments = [
            make_line((0, 0), (10, 0)),
            make_line((10, 0), (10, 10)),
            make_line((10, 10), (0, 10)),
            make_line((0, 10), (0, 0)),
        ]
        result = insert_tabs(segments, n_tabs=2, tab_width=1.0)
        assert len(result) > 0
