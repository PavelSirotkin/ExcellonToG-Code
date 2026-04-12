"""
Отрисовка на canvas: сетка, линейки, отверстия, слоты, пути.
"""
import math
import tkinter as tk
import core.config as cfg
from core.transforms import to_real_x, to_real_y


def get_grid_step_mm():
    """Динамический шаг сетки в зависимости от масштаба."""
    if cfg.scale_factor >= 10:
        return 1
    elif cfg.scale_factor >= 5:
        return 5
    elif cfg.scale_factor >= 2:
        return 10
    return 20


def determine_ruler_step(visible_range_mm):
    """Адаптивный шаг делений линейки."""
    min_pixel_step = 50
    min_mm_step = min_pixel_step / cfg.scale_factor
    step = 1
    while step < min_mm_step:
        if step * 5 >= min_mm_step:
            step *= 5
        elif step * 2 >= min_mm_step:
            step *= 2
        else:
            step *= 10
    return max(1, int(step))


def clip_line(x1, y1, x2, y2, xmin, ymin, xmax, ymax):
    """Алгоритм Коэна-Сазерленда для клиппирования линий."""
    INSIDE, LEFT, RIGHT, BOTTOM, TOP = 0, 1, 2, 4, 8

    def compute_code(x, y):
        code = INSIDE
        if x < xmin: code |= LEFT
        elif x > xmax: code |= RIGHT
        if y < ymin: code |= TOP
        elif y > ymax: code |= BOTTOM
        return code

    code1 = compute_code(x1, y1)
    code2 = compute_code(x2, y2)
    while True:
        if not (code1 | code2):
            return (x1, y1, x2, y2)
        elif code1 & code2:
            return (None, None, None, None)
        else:
            code_out = code1 if code1 else code2
            if code_out & TOP:
                x = x1 + (x2 - x1) * (ymin - y1) / (y2 - y1) if y2 != y1 else x1
                y = ymin
            elif code_out & BOTTOM:
                x = x1 + (x2 - x1) * (ymax - y1) / (y2 - y1) if y2 != y1 else x1
                y = ymax
            elif code_out & RIGHT:
                y = y1 + (y2 - y1) * (xmax - x1) / (x2 - x1) if x2 != x1 else y1
                x = xmax
            elif code_out & LEFT:
                y = y1 + (y2 - y1) * (xmin - x1) / (x2 - x1) if x2 != x1 else y1
                x = xmin
            if code_out == code1:
                x1, y1 = x, y
                code1 = compute_code(x1, y1)
            else:
                x2, y2 = x, y
                code2 = compute_code(x2, y2)


def is_in_workarea(rx, ry):
    """Проверка точки в рабочей области."""
    return (cfg.WORKAREA_OFFSET_X <= rx <= cfg.WORKAREA_OFFSET_X + cfg.WORKAREA_WIDTH and
            cfg.WORKAREA_OFFSET_Y <= ry <= cfg.WORKAREA_OFFSET_Y + cfg.WORKAREA_HEIGHT)


def draw_rulers(canvas):
    """Отрисовка линеек по X и Y."""
    wa_x1 = cfg.WORKAREA_OFFSET_X
    wa_y1 = cfg.WORKAREA_OFFSET_Y
    wa_x2 = cfg.WORKAREA_OFFSET_X + cfg.WORKAREA_WIDTH
    wa_y2 = cfg.WORKAREA_OFFSET_Y + cfg.WORKAREA_HEIGHT

    ruler_y = wa_y2 + 5
    visible_start_x = cfg.offset_x - (cfg.WORKAREA_WIDTH / (2 * cfg.scale_factor))
    visible_end_x = cfg.offset_x + (cfg.WORKAREA_WIDTH / (2 * cfg.scale_factor))
    step_x = determine_ruler_step(visible_end_x - visible_start_x)
    first_tick_x = step_x * math.floor(visible_start_x / step_x)
    last_tick_x = step_x * math.ceil(visible_end_x / step_x)
    for x_mm in range(first_tick_x, last_tick_x + 1, step_x):
        if x_mm < cfg.X_MIN or x_mm > cfg.X_MAX:
            continue
        real_x = to_real_x(x_mm)
        if wa_x1 <= real_x <= wa_x2:
            canvas.create_line(real_x, ruler_y, real_x, ruler_y + 10, fill="black")
            canvas.create_text(real_x, ruler_y + 15,
                               text=f"{x_mm:.0f}", anchor="n", font=("Arial", 8))

    visible_start_y = cfg.offset_y - (cfg.WORKAREA_HEIGHT / (2 * cfg.scale_factor))
    visible_end_y = cfg.offset_y + (cfg.WORKAREA_HEIGHT / (2 * cfg.scale_factor))
    step_y = determine_ruler_step(visible_end_y - visible_start_y)
    first_tick_y = step_y * math.floor(visible_start_y / step_y)
    last_tick_y = step_y * math.ceil(visible_end_y / step_y)
    for y_mm in range(first_tick_y, last_tick_y + 1, step_y):
        if y_mm < cfg.Y_MIN or y_mm > cfg.Y_MAX:
            continue
        real_y = to_real_y(y_mm)
        if wa_y1 <= real_y <= wa_y2:
            canvas.create_line(wa_x1 - 20, real_y, wa_x1 - 10, real_y, fill="black")
            canvas.create_text(wa_x1 - 25, real_y,
                               text=f"{y_mm:.0f}", anchor="e", font=("Arial", 8))


def redraw_grid(event=None):
    """Полная перерисовка: фон, сетка, отверстия, слоты, пути, линейки."""
    canvas = cfg.get_widget("canvas")
    if canvas is None:
        return

    if cfg.viz_mode:
        from ui.gcode_viz import redraw_viz
        redraw_viz(cfg.viz_play_index)
        return

    canvas.delete("all")

    wa_x1 = cfg.WORKAREA_OFFSET_X
    wa_y1 = cfg.WORKAREA_OFFSET_Y
    wa_x2 = cfg.WORKAREA_OFFSET_X + cfg.WORKAREA_WIDTH
    wa_y2 = cfg.WORKAREA_OFFSET_Y + cfg.WORKAREA_HEIGHT

    canvas.create_rectangle(0, 0, cfg.CANVAS_WIDTH + cfg.BACKGROUND_PAD,
                            cfg.CANVAS_HEIGHT + cfg.BACKGROUND_PAD,
                            fill="#F0F0F0", outline="")
    canvas.create_rectangle(wa_x1, wa_y1, wa_x2, wa_y2, fill="white", outline="")

    grid_step_mm = get_grid_step_mm()
    visible_start_x = cfg.offset_x - (cfg.WORKAREA_WIDTH / (2 * cfg.scale_factor))
    visible_end_x = cfg.offset_x + (cfg.WORKAREA_WIDTH / (2 * cfg.scale_factor))
    first_line_x = grid_step_mm * math.floor(visible_start_x / grid_step_mm)
    last_line_x = grid_step_mm * math.ceil(visible_end_x / grid_step_mm)
    for x_mm in range(first_line_x, last_line_x + 1, grid_step_mm):
        real_x = to_real_x(x_mm)
        if wa_x1 <= real_x <= wa_x2:
            canvas.create_line(real_x, wa_y1, real_x, wa_y2, fill="lightgray")

    visible_start_y = cfg.offset_y - (cfg.WORKAREA_HEIGHT / (2 * cfg.scale_factor))
    visible_end_y = cfg.offset_y + (cfg.WORKAREA_HEIGHT / (2 * cfg.scale_factor))
    first_line_y = grid_step_mm * math.floor(visible_start_y / grid_step_mm)
    last_line_y = grid_step_mm * math.ceil(visible_end_y / grid_step_mm)
    for y_mm in range(first_line_y, last_line_y + 1, grid_step_mm):
        real_y = to_real_y(y_mm)
        if wa_y1 <= real_y <= wa_y2:
            canvas.create_line(wa_x1, real_y, wa_x2, real_y, fill="lightgray")

    colors = cfg.HOLE_COLORS
    slot_colors = cfg.SLOT_COLORS

    if cfg.current_tools:
        for i, (tool, data) in enumerate(cfg.current_tools.items()):
            if not data['visible']:
                continue
            color = colors[i % len(colors)]
            is_hovered = (cfg.hovered_tool == (tool, 'holes'))
            for x_mm, y_mm in data['holes']:
                real_x = to_real_x(x_mm)
                real_y = to_real_y(y_mm)
                if is_in_workarea(real_x, real_y):
                    if is_hovered:
                        canvas.create_oval(real_x - 6, real_y - 6,
                                           real_x + 6, real_y + 6,
                                           fill="", outline="white", width=3)
                        canvas.create_oval(real_x - 5, real_y - 5,
                                           real_x + 5, real_y + 5,
                                           fill=color, outline=color)
                    else:
                        canvas.create_oval(real_x - 2, real_y - 2,
                                           real_x + 2, real_y + 2,
                                           fill=color, outline=color)

        if cfg.show_paths_var and cfg.show_paths_var.get():
            for i, (tool, data) in enumerate(cfg.current_tools.items()):
                if not data['visible'] or len(data['holes']) < 2:
                    continue
                color = colors[i % len(colors)]
                holes = data['holes']
                for j in range(len(holes) - 1):
                    r_x1 = to_real_x(holes[j][0])
                    r_y1 = to_real_y(holes[j][1])
                    r_x2 = to_real_x(holes[j + 1][0])
                    r_y2 = to_real_y(holes[j + 1][1])
                    clipped = clip_line(r_x1, r_y1, r_x2, r_y2,
                                        wa_x1, wa_y1, wa_x2, wa_y2)
                    if clipped[0] is not None:
                        canvas.create_line(clipped[0], clipped[1],
                                           clipped[2], clipped[3],
                                           fill=color, width=1)

    if cfg.slot_tools:
        for i, (tool, data) in enumerate(cfg.slot_tools.items()):
            if not data['visible']:
                continue
            color = slot_colors[i % len(slot_colors)]
            diameter = data['diameter']
            r_px = max(2, (diameter / 2) * cfg.scale_factor)
            is_hovered = (cfg.hovered_tool == (tool, 'slots'))

            for start, end in data['slots']:
                real_sx = to_real_x(start[0])
                real_sy = to_real_y(start[1])
                real_ex = to_real_x(end[0])
                real_ey = to_real_y(end[1])

                line_w = max(1, int(diameter * cfg.scale_factor))
                if is_hovered:
                    clipped_h = clip_line(real_sx, real_sy, real_ex, real_ey,
                                          wa_x1, wa_y1, wa_x2, wa_y2)
                    if clipped_h[0] is not None:
                        canvas.create_line(clipped_h[0], clipped_h[1],
                                           clipped_h[2], clipped_h[3],
                                           fill="white", width=line_w + 4,
                                           capstyle=tk.ROUND)
                clipped = clip_line(real_sx, real_sy, real_ex, real_ey,
                                    wa_x1, wa_y1, wa_x2, wa_y2)
                if clipped[0] is not None:
                    canvas.create_line(clipped[0], clipped[1],
                                       clipped[2], clipped[3],
                                       fill=color, width=line_w,
                                       capstyle=tk.ROUND)

                if is_in_workarea(real_sx, real_sy):
                    canvas.create_oval(real_sx - r_px, real_sy - r_px,
                                       real_sx + r_px, real_sy + r_px,
                                       outline=color, width=1)
                    canvas.create_oval(real_sx - 2, real_sy - 2,
                                       real_sx + 2, real_sy + 2,
                                       fill=color, outline=color)
                if is_in_workarea(real_ex, real_ey):
                    canvas.create_oval(real_ex - r_px, real_ey - r_px,
                                       real_ex + r_px, real_ey + r_px,
                                       outline=color, width=1)
                    canvas.create_oval(real_ex - 2, real_ey - 2,
                                       real_ex + 2, real_ey + 2,
                                       fill=color, outline=color)

            if cfg.show_paths_var and cfg.show_paths_var.get() and len(data['slots']) > 1:
                for j in range(len(data['slots']) - 1):
                    _, prev_end = data['slots'][j]
                    next_start, _ = data['slots'][j + 1]
                    r_pe_x = to_real_x(prev_end[0])
                    r_pe_y = to_real_y(prev_end[1])
                    r_ns_x = to_real_x(next_start[0])
                    r_ns_y = to_real_y(next_start[1])
                    clipped = clip_line(r_pe_x, r_pe_y, r_ns_x, r_ns_y,
                                        wa_x1, wa_y1, wa_x2, wa_y2)
                    if clipped[0] is not None:
                        canvas.create_line(clipped[0], clipped[1],
                                           clipped[2], clipped[3],
                                           fill=color, width=1, dash=(4, 4))

    canvas.create_rectangle(wa_x1, wa_y1, wa_x2, wa_y2, outline="black", width=2)
    draw_rulers(canvas)
