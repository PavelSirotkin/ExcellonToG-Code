"""
Генерация G-code для финишной обрезки платы по контуру.
"""
import math
import os
from typing import List, Dict, Tuple, Optional
from core.polygon_ops import (
    offset_segments, insert_tabs, flatten, classify_subpaths,
)
from core.gcode_generator import (
    write_tool_start, write_tool_parking,
    emit_rapid_xy, emit_mill_xy, emit_plunge_z, emit_retract_z,
)


def build_outline_section(buf, segments: List[Dict], filename: str,
                          params: Dict, outline_params: Dict,
                          tool_num: int = 100) -> None:
    """
    Построить секцию G-code для обрезки по контуру.

    Args:
        buf: StringIO буфер для записи G-code
        segments: сегменты контура платы
        filename: имя исходного файла контура
        params: глобальные параметры {safe_z, drill_z, rapid_rate, mill_feed, feed_rate, ...}
        outline_params: параметры обрезки {
            tool_diameter, depth_per_pass, n_tabs, tab_width, tab_height, direction,
            mill_feed (опционально, если задано — имеет приоритет),
            plunge_feed (опционально),
            spindle_speed (опционально)
        }
        tool_num: номер инструмента для G-code
    """
    if not segments:
        return

    safe_z = params.get('safe_z', 5.0)
    drill_z = params.get('drill_z', -2.5)
    rapid_rate = params.get('rapid_rate', 500)

    tool_diameter = outline_params.get('tool_diameter', 2.0)
    depth_per_pass = outline_params.get('depth_per_pass', 0.5)
    # Защита от depth_per_pass <= 0: основной путь через UI ловится
    # validate_outline_params, но при прямом вызове генератора (тесты,
    # программный пайплайн) попадание нуля в деление давало ZeroDivisionError.
    # Минимум 0.01 мм — заведомо тонкий проход, даёт осмысленный G-code
    # вместо краша. Нормализуем здесь, чтобы и G-code-комментарий
    # «Depth per pass: …», и расчёт n_passes использовали одно значение.
    depth_per_pass = max(float(depth_per_pass), 0.01)
    n_tabs = int(outline_params.get('n_tabs', 4))
    tab_width = outline_params.get('tab_width', 3.0)
    tab_height = outline_params.get('tab_height', 1.0)
    direction = outline_params.get('direction', 'CCW')

    # Рабочие подачи: если задано в outline_params — используем,
    # иначе падаем на глобальные params (mill_feed для XY, feed_rate для Z-погружения).
    mill_feed = outline_params.get('mill_feed',
                                   params.get('mill_feed', 50))
    plunge_feed = outline_params.get('plunge_feed',
                                     params.get('feed_rate', 100))
    spindle_speed = outline_params.get('spindle_speed', None)

    # Заголовок секции
    buf.write("\n; ===== BOARD OUTLINE MILLING =====\n")
    if filename:
        buf.write(f"; Source: {os.path.basename(filename)}\n")
    buf.write(f"; Tool diameter: {tool_diameter:.2f}mm\n")
    buf.write(f"; Depth per pass: {depth_per_pass:.2f}mm\n")
    buf.write(f"; Tabs: {n_tabs} x {tab_width:.1f}mm\n")
    buf.write(f"; Direction: {direction}\n")
    buf.write(f"; Mill feed: {mill_feed:.0f} mm/min\n")
    buf.write(f"; Plunge feed: {plunge_feed:.0f} mm/min\n\n")

    # Готовим путь по каждому подконтуру отдельно. Для платы с вырезами
    # один общий offset «склеивает» внешний контур и вырезы в один
    # полигон — фреза переходит между ними по диагонали на рабочей
    # глубине, разрушая плату. Решение: каждый подконтур фрезеруется
    # независимо, между ними фреза поднимается на safe Z.
    offset_delta = tool_diameter / 2.0
    classified = classify_subpaths(segments)

    paths: List[Dict] = []
    for cls in classified:
        # Внешний контур → offset наружу (фреза идёт по краю, материал
        # справа); вырез → offset ВНУТРЬ (фреза идёт по краю выреза,
        # материал снаружи от пути) — иначе мы расширим вырез на
        # диаметр фрезы.
        offset_segs = offset_segments(
            cls['segments'], offset_delta, outward=cls['is_outer'])
        if not offset_segs:
            # offset_segments возвращает [] либо для незамкнутого подконтура,
            # либо для self-intersection (delta больше радиуса вписанной
            # окружности у вогнутого угла — см. polygon_ops._has_self_intersection).
            # Самая частая практическая причина — слишком большой диаметр фрезы
            # для острого внутреннего угла. Пишем подсказку прямо в G-code,
            # чтобы оператор увидел причину пропуска без чтения логов.
            buf.write(
                "; Skipped subpath: offset failed "
                "(probable cause: tool radius too large for a sharp concave "
                "corner — try smaller tool_diameter)\n")
            continue
        flat_points = flatten(offset_segs, tol_mm=0.02)
        if len(flat_points) < 3:
            buf.write("; Skipped subpath: too small\n")
            continue
        if direction == 'CW':
            flat_points = list(reversed(flat_points))
        paths.append({
            'flat_points': flat_points,
            'is_outer': cls['is_outer'],
            'depth': cls['depth'],
        })

    if not paths:
        buf.write("; Error: Could not create offset contour\n")
        return

    # Порядок: сначала внутренние подконтуры, последним — внешний контур
    # (плата отделяется от заготовки в самом конце). Пока плата держится
    # массивом заготовки, вырезы режутся максимально жёстко закреплённой
    # деталью; tabs на внешнем контуре нужны только на финальной операции.
    # Сортируем по убыванию глубины: depth 3 (вырез в островке) → depth 2
    # (островок) → depth 1 (вырез в плате) → depth 0 (внешний контур).
    # Сортировка стабильна — относительный порядок подконтуров одного
    # уровня сохраняется.
    paths.sort(key=lambda p: -p['depth'])

    # Вычисляем количество Z-проходов (depth_per_pass уже нормализован выше).
    total_depth = abs(drill_z)
    n_passes = max(1, int(math.ceil(total_depth / depth_per_pass)))

    # Заголовок инструмента (со шпинделем, если задан).
    # total_segments — общее число резных рёбер по всем подконтурам и
    # всем Z-проходам, для отчёта в стартовой шапке.
    total_segments = sum((len(p['flat_points']) - 1) for p in paths) * n_passes
    write_tool_start(buf, tool_num, tool_diameter, total_segments,
                     "outline", safe_z, rapid_rate, spindle_speed=spindle_speed)

    # Цикл по подконтурам. Каждый завершается полным retract на safe_z,
    # так что переезд между ними всегда безопасен.
    for path_idx, path in enumerate(paths):
        flat_points = path['flat_points']
        is_outer = path['is_outer']
        kind = "outer contour" if is_outer else f"inner cutout (depth={path['depth']})"
        buf.write(f"\n; --- Subpath {path_idx + 1}/{len(paths)}: {kind} ---\n")

        for pass_idx in range(n_passes):
            current_z = max(drill_z, -depth_per_pass * (pass_idx + 1))

            # Tabs формируются ТОЛЬКО на внешнем контуре — на вырезе
            # перемычки бессмысленны (плата вокруг выреза остаётся целой).
            tab_start_z = drill_z + tab_height
            should_use_tabs = (
                is_outer and n_tabs > 0 and current_z <= tab_start_z)

            buf.write(f"\n; Pass {pass_idx + 1}/{n_passes}, Z={current_z:.2f}\n")

            if should_use_tabs:
                _generate_tabbed_pass(buf, flat_points, current_z, safe_z,
                                      rapid_rate, mill_feed, plunge_feed,
                                      tab_height, n_tabs, tab_width)
            else:
                _generate_simple_pass(buf, flat_points, current_z, safe_z,
                                      rapid_rate, mill_feed, plunge_feed)

    # Парковка
    write_tool_parking(buf, params.get('park_z', 30), rapid_rate)


def _generate_simple_pass(buf, points: List[Tuple[float, float]],
                          target_z: float, safe_z: float,
                          rapid_rate: float, mill_feed: float,
                          plunge_feed: float) -> None:
    """Сгенерировать простой проход без tabs.

    G00 — быстрые перемещения с rapid_rate.
    G01 Z — погружение с plunge_feed.
    G01 X/Y — рабочее резание с mill_feed.
    """
    if not points:
        return

    # Подъезд к первой точке на быстром ходе
    first = points[0]
    emit_rapid_xy(buf, first[0], first[1], rapid_rate)
    # Погружение по Z — с подачей врезания
    emit_plunge_z(buf, target_z, plunge_feed)

    # Проход по всем точкам — с подачей резания
    for p in points[1:]:
        emit_mill_xy(buf, p[0], p[1], mill_feed)

    # Замыкаем контур, только если последняя точка ещё не совпадает с первой
    # (flatten для замкнутого контура уже возвращает [A, ..., A]).
    last = points[-1]
    if math.hypot(last[0] - first[0], last[1] - first[1]) > 1e-6:
        emit_mill_xy(buf, first[0], first[1], mill_feed)

    # Подъём на быстром ходе
    emit_retract_z(buf, safe_z, rapid_rate)


def _rotate_to_safe_plunge(tabbed_segments: List[Dict]) -> List[Dict]:
    """Повернуть замкнутый список сегментов так, чтобы первое погружение
    произошло в середине самого длинного non-tab сегмента.

    Найденный сегмент разбивается пополам в точке midpoint M, и список
    переставляется: [M..p2_seg, ...следующие сегменты..., ...предыдущие
    сегменты..., p1_seg..M]. Контур остаётся замкнутым, но стартует и
    заканчивается в M — на максимальном удалении от ближайшей tab-границы.
    Если все сегменты помечены как tab или non-tab сегментов нет,
    возвращается исходный список без изменений.
    """
    if not tabbed_segments:
        return tabbed_segments

    non_tab_idx = [i for i, s in enumerate(tabbed_segments)
                   if not s.get('is_tab', False) and s.get('type') == 'line']
    if not non_tab_idx:
        return tabbed_segments

    def _seg_len(s: Dict) -> float:
        p1, p2 = s['p1'], s['p2']
        return math.hypot(p2[0] - p1[0], p2[1] - p1[1])

    best = max(non_tab_idx, key=lambda i: _seg_len(tabbed_segments[i]))
    seg = tabbed_segments[best]
    p1, p2 = seg['p1'], seg['p2']
    mid = ((p1[0] + p2[0]) / 2.0, (p1[1] + p2[1]) / 2.0)
    second_half = {'type': 'line', 'p1': mid, 'p2': p2}
    first_half = {'type': 'line', 'p1': p1, 'p2': mid}

    return ([second_half]
            + tabbed_segments[best + 1:]
            + tabbed_segments[:best]
            + [first_half])


def _generate_tabbed_pass(buf, points: List[Tuple[float, float]],
                          target_z: float, safe_z: float,
                          rapid_rate: float, mill_feed: float,
                          plunge_feed: float,
                          tab_height: float, n_tabs: int,
                          tab_width: float) -> None:
    """Сгенерировать проход с держательными перемычками (tabs).

    G00 — быстрые перемещения (подъезд, переезд через tab).
    G01 Z — погружение с plunge_feed.
    G01 X/Y — рабочее резание с mill_feed.
    """
    if not points or len(points) < 3:
        return

    # Преобразуем точки в сегменты.
    # flatten() обычно возвращает уже замкнутый список (points[-1] == points[0]),
    # поэтому дописываем явное замыкание только если контур не замкнут.
    segments = []
    for i in range(len(points) - 1):
        segments.append({
            'type': 'line',
            'p1': points[i],
            'p2': points[i + 1]
        })
    dx = points[-1][0] - points[0][0]
    dy = points[-1][1] - points[0][1]
    if math.hypot(dx, dy) > 1e-6:
        segments.append({
            'type': 'line',
            'p1': points[-1],
            'p2': points[0]
        })

    # Вставляем tabs
    tabbed_segments = insert_tabs(segments, n_tabs, tab_width)

    # Сдвигаем стартовую точку подальше от любой перемычки. Иначе первое
    # погружение происходит в points[0] — а оно может оказаться внутри
    # tab-диапазона (особенно при wrap-around, когда центр перемычки
    # лежит у самого начала/конца контура) или просто рядом с краем
    # перемычки. Фреза диаметра, сравнимого с tab_width, при погружении
    # на полную глубину срезает мост. Решение: стартовать в середине
    # самого длинного non-tab сегмента — это даёт максимальный зазор
    # до ближайшей перемычки.
    tabbed_segments = _rotate_to_safe_plunge(tabbed_segments)
    if not tabbed_segments:
        return

    # Подъезд к первой точке на быстром ходе
    first = tabbed_segments[0]['p1']
    emit_rapid_xy(buf, first[0], first[1], rapid_rate)
    # Погружение по Z — с подачей врезания
    emit_plunge_z(buf, target_z, plunge_feed)

    # Проход с tabs.
    # Внутри tab фреза остаётся в материале на уровне target_z + tab_height:
    # сверху — шов ширины tab_width, снизу — нетронутый мост высотой tab_height.
    # Поэтому перемещение над tab — G01 с рабочей подачей, а не G00.
    # Комментарии ; TAB BEGIN / ; TAB END — чтобы визуализатор мог различать
    # нормальный рез и участок над перемычкой.
    current_is_tab = False
    for seg in tabbed_segments:
        p2 = seg['p2']
        is_tab = seg.get('is_tab', False)

        if is_tab and not current_is_tab:
            # Вход в tab: поднимаемся до уровня перемычки с подачей врезания
            buf.write("; TAB BEGIN\n")
            emit_plunge_z(buf, target_z + tab_height, plunge_feed)
            current_is_tab = True
        elif not is_tab and current_is_tab:
            # Выход из tab: опускаемся обратно на рабочую глубину
            emit_plunge_z(buf, target_z, plunge_feed)
            buf.write("; TAB END\n")
            current_is_tab = False

        # Линейное перемещение всегда с рабочей подачей (фреза в материале)
        emit_mill_xy(buf, p2[0], p2[1], mill_feed)

    # Если контур закончился внутри tab — вернуться на рабочую глубину
    if current_is_tab:
        emit_plunge_z(buf, target_z, plunge_feed)
        buf.write("; TAB END\n")

    # Подъём на быстром ходе
    emit_retract_z(buf, safe_z, rapid_rate)
