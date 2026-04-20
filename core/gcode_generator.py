"""
Генерация G-code (сверление, фрезеровка слотов, объединённый).
Чистая бизнес-логика — без зависимостей от tkinter.
"""
import os
import io
import math
from core.validators import validate_gcode_params as _validate_params

# Re-export для обратной совместимости (используется в тестах)
def validate_gcode_params(safe_z, drill_z, feed_rate, rapid_rate, park_z, mill_feed=None):
    return _validate_params({'safe_z': safe_z, 'drill_z': drill_z, 'feed_rate': feed_rate,
                             'rapid_rate': rapid_rate, 'park_z': park_z, 'mill_feed': mill_feed})


def _calc_multipass_offsets(slot_width, tool_diameter, stepover_pct):
    """Список смещений от оси слота для multi-pass. Симметрично от 0.
    Шаг = tool_diameter * (1 - stepover_pct/100). Если stepover_pct==0 → 50%.
    Условие включения прохода: |offset| + tool_diameter/2 <= slot_width/2.
    """
    pct = stepover_pct if stepover_pct and stepover_pct > 0 else 50
    step = tool_diameter * (1.0 - pct / 100.0)
    if step <= 0:
        step = tool_diameter * 0.5
    half_w = slot_width / 2.0
    half_d = tool_diameter / 2.0
    offsets = []
    k = 0
    while True:
        candidates = [0.0] if k == 0 else [k * step, -k * step]
        added = False
        for offset in candidates:
            if abs(offset) + half_d <= half_w + 1e-9:
                offsets.append(offset)
                added = True
        if k > 0 and not added:
            break
        k += 1

    # Добавить граничные проходы (касание стенок), если не покрыты stepover-проходами
    max_wall_offset = half_w - half_d  # = (slot_width - tool_diameter) / 2
    if max_wall_offset > 1e-9:
        covered = any(abs(abs(o) - max_wall_offset) < 1e-9 for o in offsets)
        if not covered:
            offsets.append(max_wall_offset)
            offsets.append(-max_wall_offset)

    return offsets


def _write_slot_passes(buf, sx, sy, ex, ey, offsets,
                       drill_z, safe_z, eff_plunge, eff_retract, eff_mill, rapid_rate):
    """Написать G-code для нескольких параллельных проходов по слоту зигзагом.
    Один подъём перед первым проходом, один подъём после последнего.
    Между проходами — только горизонтальное перемещение на уровне drill_z.
    Направление чередуется: pass1 start→end, pass2 end'→start', pass3 start''→end'' ...
    """
    dx = ex - sx
    dy = ey - sy
    length = math.sqrt(dx * dx + dy * dy)
    if length < 1e-9:
        # Нулевой слот — одна точка, просто погружение
        buf.write(f"G00 X{sx:.3f} Y{sy:.3f} F{rapid_rate:.0f}\n")
        buf.write(f"G01 Z{drill_z:.2f} F{eff_plunge:.0f}\n")
        buf.write(f"G00 Z{safe_z:.2f} F{eff_retract:.0f}\n")
        return
    # Нормаль (перпендикуляр к оси, повёрнут на 90°)
    nx = -dy / length
    ny = dx / length

    # Вычислить координаты всех проходов (start, end) с учётом смещения
    passes = []
    for offset in offsets:
        passes.append((
            sx + nx * offset, sy + ny * offset,
            ex + nx * offset, ey + ny * offset,
        ))

    # Зигзаг: быстрый подъезд к началу первого прохода, погружение
    # Инструмент идёт: start0→end0, затем на уровне drill_z переезд к началу pass1,
    # pass1 идёт в обратную сторону: end1→start1, и т.д.
    # Конец прохода i и начало прохода i+1 — соединяем одним G01 на drill_z.

    # passes[i] = (psx, psy, pex, pey) — прямое направление
    # При нечётном i проход идёт в обратную сторону (end→start)

    p0sx, p0sy, p0ex, p0ey = passes[0]
    buf.write(f"G00 X{p0sx:.3f} Y{p0sy:.3f} F{rapid_rate:.0f}\n")
    buf.write(f"G01 Z{drill_z:.2f} F{eff_plunge:.0f}\n")
    buf.write(f"G01 X{p0ex:.3f} Y{p0ey:.3f} F{eff_mill:.0f}\n")

    # Текущий конец: конец прохода 0 (прямой) = p0ex, p0ey
    cur_x, cur_y = p0ex, p0ey

    for i in range(1, len(passes)):
        psx, psy, pex, pey = passes[i]
        buf.write(f"; pass {i + 1}\n")
        if i % 2 == 1:
            # Нечётный проход — идём в обратную сторону: end→start
            # Переезд от cur к pex,pey (поперёк + небольшой сдвиг вдоль)
            buf.write(f"G01 X{pex:.3f} Y{pey:.3f} F{eff_mill:.0f}\n")
            buf.write(f"G01 X{psx:.3f} Y{psy:.3f} F{eff_mill:.0f}\n")
            cur_x, cur_y = psx, psy
        else:
            # Чётный проход — прямое направление: start→end
            buf.write(f"G01 X{psx:.3f} Y{psy:.3f} F{eff_mill:.0f}\n")
            buf.write(f"G01 X{pex:.3f} Y{pey:.3f} F{eff_mill:.0f}\n")
            cur_x, cur_y = pex, pey

    # Подъём после последнего прохода
    buf.write(f"G00 Z{safe_z:.2f} F{eff_retract:.0f}\n")


def write_tool_start(f, tool, diameter, count, unit, safe_z, rapid_rate, spindle_speed=None):
    """Заголовок нового инструмента.
    Если spindle_speed задан — генерирует M03 S{n}.
    """
    f.write(f"; Tool T{tool} D={diameter:.2f}mm ({count} {unit})\n")
    f.write(f"; Change to T{tool} D={diameter:.2f}mm\n")
    f.write("; Pause for tool change\n")
    f.write("M00\n")
    f.write("; Spindle ON\n")
    if spindle_speed is not None and spindle_speed > 0:
        f.write(f"M03 S{int(spindle_speed)}\n")
    else:
        f.write("M03\n")
    f.write(f"G00 Z{safe_z:.2f} F{rapid_rate:.0f}\n")


def write_tool_parking(f, park_z, rapid_rate):
    """Парковка после каждого инструмента для смены."""
    f.write("\n; Parking\n")
    f.write("; Spindle OFF\n")
    f.write("M05\n")
    f.write(f"G00 Z{park_z:.2f} F{rapid_rate:.0f}\n")
    f.write("G00 X0 Y0\n")


def _get_spindle_speed(tool_params):
    """Получить скорость шпинделя из параметров инструмента."""
    if tool_params and "spindle_speed" in tool_params:
        return tool_params["spindle_speed"]
    return None


def _get_feed_rate(tool_params, global_key="feed_rate"):
    """Получить подачу из параметров инструмента или fallback."""
    if tool_params and global_key in tool_params:
        return tool_params[global_key]
    return None


def _build_drilling_gcode(current_tools, current_filename, params, tool_params_dict=None):
    """Построение G-code для сверления.

    Args:
        current_tools: dict инструментов
        current_filename: имя файла
        params: глобальные параметры {safe_z, drill_z, feed_rate, rapid_rate, park_z}
        tool_params_dict: {tool_number: {spindle_speed, feed_rate, ...}} — параметры из базы
    Returns:
        (gcode_text, errors)
    """
    errors = []
    if not current_tools:
        errors.append("Нет загруженных данных об отверстиях.")
        return None, errors

    safe_z = params.get('safe_z', 5.0)
    drill_z = params.get('drill_z', -2.5)
    feed_rate = params.get('feed_rate', 100)
    rapid_rate = params.get('rapid_rate', 500)
    park_z = params.get('park_z', 30)

    validation_errors = _validate_params({'safe_z': safe_z, 'drill_z': drill_z,
                                          'feed_rate': feed_rate, 'rapid_rate': rapid_rate,
                                          'park_z': park_z})
    if validation_errors:
        return None, validation_errors

    visible_tools = [(t, d) for t, d in current_tools.items()
                     if d['visible'] and d['holes']]
    if not visible_tools:
        errors.append("Нет видимых отверстий для генерации.")
        return None, errors

    buf = io.StringIO()
    buf.write("; G-Code — Drilling only\n")
    if current_filename:
        buf.write(f"; Source: {os.path.basename(current_filename)}\n")
    buf.write("G21 ; Metric\n")
    buf.write("G90 ; Absolute coordinates\n\n")

    for tool, data in visible_tools:
        t_params = tool_params_dict.get(tool) if tool_params_dict else None
        spindle = _get_spindle_speed(t_params)
        # Погружение Z — из базы (plunge_feed) или глобальная feed_rate
        eff_plunge = _get_feed_rate(t_params, 'feed_rate') or feed_rate
        # Подъём Z — из базы (retract_feed) или глобальная rapid_rate
        eff_retract = _get_feed_rate(t_params, 'rapid_rate') or rapid_rate

        write_tool_start(buf, tool, data['diameter'], len(data['holes']),
                         "holes", safe_z, rapid_rate, spindle)
        for x_mm, y_mm in data['holes']:
            buf.write(f"G00 X{x_mm:.3f} Y{y_mm:.3f} F{rapid_rate:.0f}\n")
            buf.write(f"G01 Z{drill_z:.2f} F{eff_plunge:.0f}\n")
            buf.write(f"G00 Z{safe_z:.2f} F{eff_retract:.0f}\n")
        write_tool_parking(buf, park_z, rapid_rate)

    buf.write("M30\n")
    buf.write("; End program\n")
    return buf.getvalue(), []


def _build_milling_gcode(slot_tools, slot_filename, params, tool_params_dict=None):
    """Построение G-code для фрезеровки слотов.

    Args:
        slot_tools: dict слотов
        slot_filename: имя файла
        params: глобальные параметры
        tool_params_dict: {tool_number: {spindle_speed, cutting_feed, plunge_feed, ...}}
    Returns:
        (gcode_text, errors)
    """
    errors = []
    if not slot_tools:
        errors.append("Нет загруженных данных о слотах.")
        return None, errors

    safe_z = params.get('safe_z', 5.0)
    drill_z = params.get('drill_z', -2.5)
    feed_rate = params.get('feed_rate', 100)
    mill_feed = params.get('mill_feed', 50)
    rapid_rate = params.get('rapid_rate', 500)
    park_z = params.get('park_z', 30)

    validation_errors = _validate_params({'safe_z': safe_z, 'drill_z': drill_z,
                                          'feed_rate': feed_rate, 'rapid_rate': rapid_rate,
                                          'park_z': park_z, 'mill_feed': mill_feed})
    if validation_errors:
        return None, validation_errors

    visible_tools = [(t, d) for t, d in slot_tools.items()
                     if d['visible'] and d['slots']]
    if not visible_tools:
        errors.append("Нет видимых слотов для генерации.")
        return None, errors

    buf = io.StringIO()
    buf.write("; G-Code — Slot milling only\n")
    if slot_filename:
        buf.write(f"; Source: {os.path.basename(slot_filename)}\n")
    buf.write(f"; Milling feed: {mill_feed:.0f} mm/min\n")
    buf.write("G21 ; Metric\n")
    buf.write("G90 ; Absolute coordinates\n\n")

    for tool, data in visible_tools:
        t_params = tool_params_dict.get(tool) if tool_params_dict else None
        spindle = _get_spindle_speed(t_params)
        # Погружение Z — из базы (plunge_feed) или глобальная feed_rate
        eff_plunge = _get_feed_rate(t_params, 'feed_rate') or feed_rate
        # Подъём Z — из базы (retract_feed) или глобальная rapid_rate
        eff_retract = _get_feed_rate(t_params, 'rapid_rate') or rapid_rate
        # Рез XY — из базы (cutting_feed) или глобальная mill_feed
        eff_mill = _get_feed_rate(t_params, 'mill_feed') or mill_feed

        tool_display_d = t_params["diameter"] if (t_params and t_params.get("multi_pass")) else data['diameter']
        write_tool_start(buf, tool, tool_display_d, len(data['slots']),
                         "slots", safe_z, rapid_rate, spindle)
        for slot_idx, (start, end) in enumerate(data['slots']):
            sx, sy = start
            ex, ey = end
            buf.write(f"; Slot {slot_idx + 1}\n")
            if t_params and t_params.get("multi_pass"):
                offsets = _calc_multipass_offsets(
                    t_params["slot_width"], t_params["diameter"], t_params.get("stepover", 0))
                _write_slot_passes(buf, sx, sy, ex, ey, offsets,
                                   drill_z, safe_z, eff_plunge, eff_retract, eff_mill, rapid_rate)
            else:
                buf.write(f"G00 X{sx:.3f} Y{sy:.3f} F{rapid_rate:.0f}\n")
                buf.write(f"G01 Z{drill_z:.2f} F{eff_plunge:.0f}\n")
                buf.write(f"G01 X{ex:.3f} Y{ey:.3f} F{eff_mill:.0f}\n")
                buf.write(f"G00 Z{safe_z:.2f} F{eff_retract:.0f}\n")
        write_tool_parking(buf, park_z, rapid_rate)

    buf.write("M30\n")
    buf.write("; End program\n")
    return buf.getvalue(), []


def _build_combined_gcode(current_tools, current_filename, slot_tools, slot_filename,
                          params, tool_params_dict=None,
                          board_outline=None, board_outline_filename=None,
                          outline_params=None):
    """Построение объединённого G-code.

    Args:
        current_tools: dict отверстий
        slot_tools: dict слотов
        params: глобальные параметры
        tool_params_dict: {"drills": {tool_num: params}, "endmills": {tool_num: params}}
        board_outline: сегменты контура платы
        board_outline_filename: имя файла контура
        outline_params: параметры обрезки по контуру
    Returns:
        (gcode_text, errors)
    """
    errors = []
    if not current_tools and not slot_tools:
        errors.append("Нет загруженных данных. Загрузите хотя бы один файл.")
        return None, errors

    safe_z = params.get('safe_z', 5.0)
    drill_z = params.get('drill_z', -2.5)
    feed_rate = params.get('feed_rate', 100)
    mill_feed = params.get('mill_feed', 50)
    rapid_rate = params.get('rapid_rate', 500)
    park_z = params.get('park_z', 30)

    validation_errors = _validate_params({'safe_z': safe_z, 'drill_z': drill_z,
                                          'feed_rate': feed_rate, 'rapid_rate': rapid_rate,
                                          'park_z': park_z, 'mill_feed': mill_feed})
    if validation_errors:
        return None, validation_errors

    has_visible_drilling = any(d['visible'] and d['holes']
                                for d in (current_tools or {}).values())
    has_visible_milling = any(d['visible'] and d['slots']
                               for d in (slot_tools or {}).values())
    if not has_visible_drilling and not has_visible_milling:
        errors.append("Нет видимых инструментов с данными для генерации.")
        return None, errors

    buf = io.StringIO()
    buf.write("; G-Code — Combined: Drilling + Slot milling\n")
    if current_filename:
        buf.write(f"; Holes source: {os.path.basename(current_filename)}\n")
    if slot_filename:
        buf.write(f"; Slots source: {os.path.basename(slot_filename)}\n")
    buf.write(f"; Milling feed: {mill_feed:.0f} mm/min\n")
    buf.write("G21 ; Metric\n")
    buf.write("G90 ; Absolute coordinates\n\n")

    # Сверление
    if current_tools and has_visible_drilling:
        buf.write("; ===== DRILLING SECTION =====\n\n")
        drills_dict = tool_params_dict.get("drills", {}) if tool_params_dict else {}
        for tool, data in current_tools.items():
            if not data['visible'] or not data['holes']:
                continue
            t_params = drills_dict.get(tool)
            spindle = _get_spindle_speed(t_params)
            eff_plunge = _get_feed_rate(t_params, 'feed_rate') or feed_rate
            eff_retract = _get_feed_rate(t_params, 'rapid_rate') or rapid_rate

            write_tool_start(buf, tool, data['diameter'], len(data['holes']),
                             "holes", safe_z, rapid_rate, spindle)
            for x_mm, y_mm in data['holes']:
                buf.write(f"G00 X{x_mm:.3f} Y{y_mm:.3f} F{rapid_rate:.0f}\n")
                buf.write(f"G01 Z{drill_z:.2f} F{eff_plunge:.0f}\n")
                buf.write(f"G00 Z{safe_z:.2f} F{eff_retract:.0f}\n")
            write_tool_parking(buf, park_z, rapid_rate)

    # Фрезеровка слотов
    if slot_tools and has_visible_milling:
        buf.write("\n; ===== SLOT MILLING SECTION =====\n\n")
        endmills_dict = tool_params_dict.get("endmills", {}) if tool_params_dict else {}
        for tool, data in slot_tools.items():
            if not data['visible'] or not data['slots']:
                continue
            t_params = endmills_dict.get(tool)
            spindle = _get_spindle_speed(t_params)
            eff_plunge = _get_feed_rate(t_params, 'feed_rate') or feed_rate
            eff_retract = _get_feed_rate(t_params, 'rapid_rate') or rapid_rate
            eff_mill = _get_feed_rate(t_params, 'mill_feed') or mill_feed

            tool_display_d = t_params["diameter"] if (t_params and t_params.get("multi_pass")) else data['diameter']
            write_tool_start(buf, tool, tool_display_d, len(data['slots']),
                             "slots", safe_z, rapid_rate, spindle)
            for slot_idx, (start, end) in enumerate(data['slots']):
                sx, sy = start
                ex, ey = end
                buf.write(f"; Slot {slot_idx + 1}\n")
                if t_params and t_params.get("multi_pass"):
                    offsets = _calc_multipass_offsets(
                        t_params["slot_width"], t_params["diameter"], t_params.get("stepover", 0))
                    _write_slot_passes(buf, sx, sy, ex, ey, offsets,
                                       drill_z, safe_z, eff_plunge, eff_retract, eff_mill, rapid_rate)
                else:
                    buf.write(f"G00 X{sx:.3f} Y{sy:.3f} F{rapid_rate:.0f}\n")
                    buf.write(f"G01 Z{drill_z:.2f} F{eff_plunge:.0f}\n")
                    buf.write(f"G01 X{ex:.3f} Y{ey:.3f} F{eff_mill:.0f}\n")
                    buf.write(f"G00 Z{safe_z:.2f} F{eff_retract:.0f}\n")
            write_tool_parking(buf, park_z, rapid_rate)

    # Обрезка по контуру
    if board_outline and outline_params:
        buf.write("\n; ===== BOARD OUTLINE MILLING =====\n\n")
        from core.outline_gcode import build_outline_section
        build_outline_section(buf, board_outline, board_outline_filename,
                              params, outline_params, tool_num=100)

    buf.write("M30\n")
    buf.write("; End program\n")
    return buf.getvalue(), []


def _build_outline_only_gcode(board_outline, board_outline_filename,
                              params, outline_params):
    """Построение G-code только для обрезки по контуру платы.

    Args:
        board_outline: список сегментов контура (линии / дуги)
        board_outline_filename: имя исходного Gerber-файла (для комментария)
        params: глобальные параметры G-code (safe_z, drill_z, rapid_rate, park_z...)
        outline_params: параметры обрезки (tool_diameter, depth_per_pass, n_tabs,
                        tab_width, tab_height, direction)
    Returns:
        (gcode_text, errors)
    """
    errors = []
    if not board_outline:
        errors.append("Контур платы не загружен.")
        return None, errors
    if not outline_params:
        errors.append("Не заданы параметры обрезки по контуру.")
        return None, errors

    safe_z = params.get('safe_z', 5.0)
    drill_z = params.get('drill_z', -2.5)
    feed_rate = params.get('feed_rate', 100)
    rapid_rate = params.get('rapid_rate', 500)
    park_z = params.get('park_z', 30)

    validation_errors = _validate_params({'safe_z': safe_z, 'drill_z': drill_z,
                                          'feed_rate': feed_rate,
                                          'rapid_rate': rapid_rate,
                                          'park_z': park_z})
    if validation_errors:
        return None, validation_errors

    buf = io.StringIO()
    buf.write("; G-Code — Board outline milling only\n")
    if board_outline_filename:
        buf.write(f"; Outline source: {os.path.basename(board_outline_filename)}\n")
    buf.write("G21 ; Metric\n")
    buf.write("G90 ; Absolute coordinates\n")

    from core.outline_gcode import build_outline_section
    build_outline_section(buf, board_outline, board_outline_filename,
                          params, outline_params, tool_num=100)

    buf.write("M30\n")
    buf.write("; End program\n")
    return buf.getvalue(), []
