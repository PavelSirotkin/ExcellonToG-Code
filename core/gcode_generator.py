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


_MULTIPASS_MAX_ITER = 10000  # верхняя граница — на любой физически разумный слот хватает с запасом


# ==========================================================
# Низкоуровневые хелперы вывода G-code
#
# Унифицированный формат: X/Y в .3f, Z в .2f, подача в .0f.
# Все callers генератора (drilling, milling slots, outline) обязаны проходить
# через эти функции — это гарантирует одинаковый вид G-code и упрощает,
# например, будущую смену постпроцессора (G0/G1 → специфика GRBL/Mach3 и т.п.).
# ==========================================================

def emit_rapid_xy(buf, x: float, y: float, rapid_rate: float) -> None:
    """Холостое перемещение в плоскости XY (G00)."""
    buf.write(f"G00 X{x:.3f} Y{y:.3f} F{rapid_rate:.0f}\n")


def emit_mill_xy(buf, x: float, y: float, mill_rate: float) -> None:
    """Рабочее перемещение в плоскости XY (G01) — резка."""
    buf.write(f"G01 X{x:.3f} Y{y:.3f} F{mill_rate:.0f}\n")


def emit_plunge_z(buf, z: float, plunge_rate: float) -> None:
    """Рабочее погружение по Z (G01) — врезание/опускание под нагрузкой."""
    buf.write(f"G01 Z{z:.2f} F{plunge_rate:.0f}\n")


def emit_retract_z(buf, z: float, rapid_rate: float) -> None:
    """Холостой подъём по Z (G00) — выход из материала на безопасную высоту."""
    buf.write(f"G00 Z{z:.2f} F{rapid_rate:.0f}\n")


def _calc_multipass_offsets(slot_width, tool_diameter, stepover_pct):
    """Список смещений от оси слота для multi-pass. Симметрично от 0.
    Шаг = tool_diameter * (1 - stepover_pct/100). Если stepover_pct==0 → 50%.
    Условие включения прохода: |offset| + tool_diameter/2 <= slot_width/2.

    Невалидные входы (tool_diameter <= 0, slot_width <= 0, NaN/inf, фреза шире
    слота) → возвращается []. Для гарантии завершения число итераций
    ограничено _MULTIPASS_MAX_ITER.
    """
    # Валидация: все размеры — конечные положительные числа
    if not (math.isfinite(slot_width) and math.isfinite(tool_diameter)):
        return []
    if tool_diameter <= 0 or slot_width <= 0:
        return []
    # Фреза шире слота — multi-pass невозможен
    if tool_diameter > slot_width + 1e-9:
        return []

    pct = stepover_pct if stepover_pct and stepover_pct > 0 else 50
    step = tool_diameter * (1.0 - pct / 100.0)
    if step <= 0:
        step = tool_diameter * 0.5
    # После guard выше step гарантированно > 0, но защитимся и здесь
    if step <= 0:
        return [0.0]
    half_w = slot_width / 2.0
    half_d = tool_diameter / 2.0
    offsets = []
    for k in range(_MULTIPASS_MAX_ITER):
        candidates = [0.0] if k == 0 else [k * step, -k * step]
        added = False
        for offset in candidates:
            if abs(offset) + half_d <= half_w + 1e-9:
                offsets.append(offset)
                added = True
        if k > 0 and not added:
            break
    # Если цикл выбрал _MULTIPASS_MAX_ITER без break — параметры явно вырожденные
    # (например, slot_width огромный при микроскопическом step). Возвращаем то,
    # что успели накопить — пользователь увидит длинную последовательность
    # проходов и поймёт, что параметры стоит проверить.

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
    if not offsets:
        # Нет валидных проходов (фреза шире слота, нулевые/отрицательные размеры
        # и т.п.). Безопасно пропускаем слот с комментарием — оператор увидит
        # пометку в G-code и поймёт, что параметры инструмента стоит проверить.
        buf.write("; Slot skipped: no valid multi-pass offsets "
                  "(tool wider than slot or invalid dimensions)\n")
        return

    dx = ex - sx
    dy = ey - sy
    length = math.sqrt(dx * dx + dy * dy)
    if length < 1e-9:
        # Нулевой слот — одна точка, просто погружение
        emit_rapid_xy(buf, sx, sy, rapid_rate)
        emit_plunge_z(buf, drill_z, eff_plunge)
        emit_retract_z(buf, safe_z, eff_retract)
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
    emit_rapid_xy(buf, p0sx, p0sy, rapid_rate)
    emit_plunge_z(buf, drill_z, eff_plunge)
    emit_mill_xy(buf, p0ex, p0ey, eff_mill)

    # Текущий конец: конец прохода 0 (прямой) = p0ex, p0ey
    cur_x, cur_y = p0ex, p0ey

    for i in range(1, len(passes)):
        psx, psy, pex, pey = passes[i]
        buf.write(f"; pass {i + 1}\n")
        if i % 2 == 1:
            # Нечётный проход — идём в обратную сторону: end→start
            # Переезд от cur к pex,pey (поперёк + небольшой сдвиг вдоль)
            emit_mill_xy(buf, pex, pey, eff_mill)
            emit_mill_xy(buf, psx, psy, eff_mill)
            cur_x, cur_y = psx, psy
        else:
            # Чётный проход — прямое направление: start→end
            emit_mill_xy(buf, psx, psy, eff_mill)
            emit_mill_xy(buf, pex, pey, eff_mill)
            cur_x, cur_y = pex, pey

    # Подъём после последнего прохода
    emit_retract_z(buf, safe_z, eff_retract)


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
    emit_retract_z(f, safe_z, rapid_rate)


def write_tool_parking(f, park_z, rapid_rate):
    """Парковка после каждого инструмента для смены."""
    f.write("\n; Parking\n")
    f.write("; Spindle OFF\n")
    f.write("M05\n")
    emit_retract_z(f, park_z, rapid_rate)
    # Парковка XY — особый случай: без подачи, координаты целыми числами.
    # Это исторический формат, который проверяется тестами и читаемее в логе.
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


def _pick_outline_tool_num(*tool_dicts, default: int = 100) -> int:
    """Подобрать свободный номер инструмента для секции обрезки контура.

    Берёт max(tool_num) + 1 среди ключей всех переданных словарей инструментов
    (current_tools, slot_tools и т.п.). Если ни в одном словаре нет ключей,
    парсящихся как целые — возвращает default. Если максимум меньше default —
    возвращает default (чтобы контур всегда оставался в "верхнем" диапазоне).
    """
    used = []
    for d in tool_dicts:
        if not d:
            continue
        for key in d.keys():
            try:
                used.append(int(key))
            except (TypeError, ValueError):
                continue
    if not used:
        return default
    return max(max(used) + 1, default)


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
    from core.i18n import t
    errors = []
    if not current_tools:
        errors.append(t("app.err.no_holes_data"))
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
        errors.append(t("app.err.no_visible_holes"))
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
            emit_rapid_xy(buf, x_mm, y_mm, rapid_rate)
            emit_plunge_z(buf, drill_z, eff_plunge)
            emit_retract_z(buf, safe_z, eff_retract)
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
    from core.i18n import t
    errors = []
    if not slot_tools:
        errors.append(t("app.err.no_slots_data"))
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
        errors.append(t("app.err.no_visible_slots"))
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
                emit_rapid_xy(buf, sx, sy, rapid_rate)
                emit_plunge_z(buf, drill_z, eff_plunge)
                emit_mill_xy(buf, ex, ey, eff_mill)
                emit_retract_z(buf, safe_z, eff_retract)
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
    from core.i18n import t
    errors = []
    if not current_tools and not slot_tools:
        errors.append(t("app.err.no_data_loaded"))
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
        errors.append(t("app.err.no_visible_tools"))
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
                emit_rapid_xy(buf, x_mm, y_mm, rapid_rate)
                emit_plunge_z(buf, drill_z, eff_plunge)
                emit_retract_z(buf, safe_z, eff_retract)
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
                    emit_rapid_xy(buf, sx, sy, rapid_rate)
                    emit_plunge_z(buf, drill_z, eff_plunge)
                    emit_mill_xy(buf, ex, ey, eff_mill)
                    emit_retract_z(buf, safe_z, eff_retract)
            write_tool_parking(buf, park_z, rapid_rate)

    # Обрезка по контуру
    if board_outline and outline_params:
        buf.write("\n; ===== BOARD OUTLINE MILLING =====\n\n")
        from core.outline_gcode import build_outline_section
        outline_tool_num = _pick_outline_tool_num(current_tools, slot_tools)
        build_outline_section(buf, board_outline, board_outline_filename,
                              params, outline_params, tool_num=outline_tool_num)

    buf.write("M30\n")
    buf.write("; End program\n")
    return buf.getvalue(), []


def _build_outline_only_gcode(board_outline, board_outline_filename,
                              params, outline_params,
                              current_tools=None, slot_tools=None):
    """Построение G-code только для обрезки по контуру платы.

    Args:
        board_outline: список сегментов контура (линии / дуги)
        board_outline_filename: имя исходного Gerber-файла (для комментария)
        params: глобальные параметры G-code (safe_z, drill_z, rapid_rate, park_z...)
        outline_params: параметры обрезки (tool_diameter, depth_per_pass, n_tabs,
                        tab_width, tab_height, direction)
        current_tools: dict отверстий — используется только для подбора номера
                       инструмента контура без конфликта с уже загруженными.
        slot_tools: dict слотов — то же назначение.
    Returns:
        (gcode_text, errors)
    """
    from core.i18n import t
    errors = []
    if not board_outline:
        errors.append(t("app.err.outline_not_loaded"))
        return None, errors
    if not outline_params:
        errors.append(t("app.err.outline_params_missing"))
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
    outline_tool_num = _pick_outline_tool_num(current_tools, slot_tools)
    build_outline_section(buf, board_outline, board_outline_filename,
                          params, outline_params, tool_num=outline_tool_num)

    buf.write("M30\n")
    buf.write("; End program\n")
    return buf.getvalue(), []
