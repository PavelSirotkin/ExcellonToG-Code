"""
Генерация G-code для финишной обрезки платы по контуру.
"""
import math
import os
from typing import List, Dict, Tuple, Optional
from core.polygon_ops import offset_segments, insert_tabs, flatten
from core.gcode_generator import write_tool_start, write_tool_parking


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

    # Offset контура наружу на радиус фрезы
    offset_delta = tool_diameter / 2.0
    offset_segments_list = offset_segments(segments, offset_delta, outward=True)

    if not offset_segments_list:
        buf.write("; Error: Could not create offset contour\n")
        return

    # Разворачиваем дуги в линии для упрощения
    flat_points = flatten(offset_segments_list, tol_mm=0.02)

    if len(flat_points) < 3:
        buf.write("; Error: Contour too small\n")
        return

    # Инвертируем направление если нужно CW
    if direction == 'CW':
        flat_points = list(reversed(flat_points))

    # Вычисляем количество Z-проходов
    total_depth = abs(drill_z)
    n_passes = max(1, int(math.ceil(total_depth / depth_per_pass)))

    # Заголовок инструмента (со шпинделем, если задан)
    write_tool_start(buf, tool_num, tool_diameter, len(flat_points) - 1,
                     "outline", safe_z, rapid_rate, spindle_speed=spindle_speed)

    # Генерируем проходы по Z
    for pass_idx in range(n_passes):
        current_z = max(drill_z, -depth_per_pass * (pass_idx + 1))
        is_last_pass = (pass_idx == n_passes - 1)

        buf.write(f"\n; Pass {pass_idx + 1}/{n_passes}, Z={current_z:.2f}\n")

        if is_last_pass and n_tabs > 0:
            # Последний проход с tabs
            _generate_tabbed_pass(buf, flat_points, current_z, safe_z,
                                  rapid_rate, mill_feed, plunge_feed,
                                  tab_height, n_tabs, tab_width)
        else:
            # Обычный проход
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
    buf.write(f"G00 X{first[0]:.3f} Y{first[1]:.3f} F{rapid_rate:.0f}\n")
    # Погружение по Z — с подачей врезания
    buf.write(f"G01 Z{target_z:.2f} F{plunge_feed:.0f}\n")

    # Проход по всем точкам — с подачей резания
    for p in points[1:]:
        buf.write(f"G01 X{p[0]:.3f} Y{p[1]:.3f} F{mill_feed:.0f}\n")

    # Замыкаем контур, только если последняя точка ещё не совпадает с первой
    # (flatten для замкнутого контура уже возвращает [A, ..., A]).
    last = points[-1]
    if math.hypot(last[0] - first[0], last[1] - first[1]) > 1e-6:
        buf.write(f"G01 X{first[0]:.3f} Y{first[1]:.3f} F{mill_feed:.0f}\n")

    # Подъём на быстром ходе
    buf.write(f"G00 Z{safe_z:.2f} F{rapid_rate:.0f}\n")


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

    # Подъезд к первой точке на быстром ходе
    first = tabbed_segments[0]['p1']
    buf.write(f"G00 X{first[0]:.3f} Y{first[1]:.3f} F{rapid_rate:.0f}\n")
    # Погружение по Z — с подачей врезания
    buf.write(f"G01 Z{target_z:.2f} F{plunge_feed:.0f}\n")

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
            buf.write(f"G01 Z{target_z + tab_height:.2f} F{plunge_feed:.0f}\n")
            current_is_tab = True
        elif not is_tab and current_is_tab:
            # Выход из tab: опускаемся обратно на рабочую глубину
            buf.write(f"G01 Z{target_z:.2f} F{plunge_feed:.0f}\n")
            buf.write("; TAB END\n")
            current_is_tab = False

        # Линейное перемещение всегда с рабочей подачей (фреза в материале)
        buf.write(f"G01 X{p2[0]:.3f} Y{p2[1]:.3f} F{mill_feed:.0f}\n")

    # Если контур закончился внутри tab — вернуться на рабочую глубину
    if current_is_tab:
        buf.write(f"G01 Z{target_z:.2f} F{plunge_feed:.0f}\n")
        buf.write("; TAB END\n")

    # Подъём на быстром ходе
    buf.write(f"G00 Z{safe_z:.2f} F{rapid_rate:.0f}\n")
