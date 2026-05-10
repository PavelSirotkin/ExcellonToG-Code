"""
Визуализатор G-code: 2.5D рендер, плеер, управление режимом.
"""
import math
import tkinter as tk
from ui import themed_messagebox as messagebox
from core.gcode_parser import parse_gcode_for_viz
from core.i18n import t
import core.config as cfg

# Кабинетная проекция: угол 30°, коэффициент глубины 0.45
_CAB_AX = math.cos(math.radians(30)) * 0.45
_CAB_AY = math.sin(math.radians(30)) * 0.45

# Цвета для инструментов в режиме визуализации
VIZ_TOOL_COLORS = [
    '#E74C3C', '#2ECC71', '#3498DB', '#F39C12',
    '#9B59B6', '#1ABC9C', '#E67E22', '#34495E',
]


def _viz_tool_color(tool_key, tool_color_map):
    """Выбор цвета для инструмента."""
    if tool_key not in tool_color_map:
        idx = len(tool_color_map) % len(VIZ_TOOL_COLORS)
        tool_color_map[tool_key] = VIZ_TOOL_COLORS[idx]
    return tool_color_map[tool_key]


def _draw_slot_like(canvas, segments, vp_fn, sf, *,
                    border_color, fill_color, oval_fallback):
    """Отрисовать набор «слотоподобных» сегментов как двойную линию: внешний
    бордер + внутренняя заливка.

    Каждый элемент `segments` — кортеж `(sx, sy, ex, ey, diameter, color)`,
    где `color` — per-tool цвет, посчитанный заранее.

    border_color:
      - None — для каждого сегмента берётся собственный per-tool `color`
        (используется для слотов и outline-прорезей).
      - строка цвета — фиксированный для всех сегментов (используется для
        tab-перемычек, у которых семантический цвет — «остаток материала»).

    fill_color: цвет «начинки» внутренней линии (фиксированный).

    oval_fallback: True — слишком короткий сегмент (`length_px < 1`) рисуется
    как oval (точечная прорезь); False — пропускается. Для tabs точечный
    мост визуально бесполезен, поэтому fallback отключается.
    """
    for sx, sy, ex, ey, diam, col in segments:
        d_px = max(2, diam * sf * 0.5)
        ps = vp_fn(sx, sy, 0.0)
        pe = vp_fn(ex, ey, 0.0)
        length_px = math.hypot(pe[0] - ps[0], pe[1] - ps[1])
        bd = border_color if border_color is not None else col
        if length_px < 1:
            if not oval_fallback:
                continue
            canvas.create_oval(ps[0] - d_px, ps[1] - d_px,
                               ps[0] + d_px, ps[1] + d_px,
                               fill=fill_color, outline=bd, width=1)
            continue
        lw = max(4, int(2 * d_px))
        canvas.create_line(ps[0], ps[1], pe[0], pe[1],
                           fill=bd, width=lw + 2, capstyle=tk.ROUND)
        canvas.create_line(ps[0], ps[1], pe[0], pe[1],
                           fill=fill_color, width=lw, capstyle=tk.ROUND)


def redraw_viz(play_idx=None):
    """Перерисовка канваса в режиме 2.5D визуализации."""
    canvas = cfg.get_widget("canvas")
    if canvas is None:
        return

    canvas.delete("all")

    wa_x1 = cfg.WORKAREA_OFFSET_X
    wa_y1 = cfg.WORKAREA_OFFSET_Y
    wa_x2 = cfg.WORKAREA_OFFSET_X + cfg.WORKAREA_WIDTH
    wa_y2 = cfg.WORKAREA_OFFSET_Y + cfg.WORKAREA_HEIGHT

    # Единый фон на весь канвас
    canvas.create_rectangle(0, 0, cfg.CANVAS_WIDTH + cfg.BACKGROUND_PAD,
                             cfg.CANVAS_HEIGHT + cfg.BACKGROUND_PAD,
                             fill="#1A1A2E", outline="")

    segs = cfg.viz_gcode_lines
    if not segs:
        canvas.create_text(cfg.CANVAS_WIDTH // 2, cfg.CANVAS_HEIGHT // 2,
                           text=t("viz.no_data"), fill="gray",
                           font=("Arial", 14))
        return

    tool_color_map = {}
    n = len(segs)
    end_idx = play_idx if play_idx is not None else n

    sf = cfg.viz_sf
    ox = cfg.viz_ox
    oy = cfg.viz_oy

    def vp(x_mm, y_mm, z_mm=0.0):
        cx_c = cfg.WORKAREA_OFFSET_X + cfg.WORKAREA_WIDTH / 2
        cy_c = cfg.WORKAREA_OFFSET_Y + cfg.WORKAREA_HEIGHT / 2
        px = cx_c + (x_mm - ox) * sf
        py = cy_c - (y_mm - oy) * sf
        px += z_mm * _CAB_AX * sf * 0.15
        py -= z_mm * _CAB_AY * sf * 0.15
        return px, py

    # Bbox платы из всех сегментов
    xs = [s['x0'] for s in segs] + [s['x1'] for s in segs]
    ys = [s['y0'] for s in segs] + [s['y1'] for s in segs]
    bx0, bx1 = min(xs) - 3, max(xs) + 3
    by0, by1 = min(ys) - 3, max(ys) + 3

    # --- Плата ---
    board_z_top, board_z_bot = 0.0, -0.5
    corners_top = [vp(bx0, by0, board_z_top), vp(bx1, by0, board_z_top),
                   vp(bx1, by1, board_z_top), vp(bx0, by1, board_z_top)]
    corners_bot = [vp(bx0, by0, board_z_bot), vp(bx1, by0, board_z_bot),
                   vp(bx1, by1, board_z_bot), vp(bx0, by1, board_z_bot)]

    flat_top  = [c for pt in corners_top for c in pt]
    flat_sf_p = [c for pt in [corners_top[0], corners_top[1],
                               corners_bot[1], corners_bot[0]] for c in pt]
    flat_sr_p = [c for pt in [corners_top[1], corners_top[2],
                               corners_bot[2], corners_bot[1]] for c in pt]

    if len(flat_sf_p) >= 8:
        canvas.create_polygon(flat_sf_p, fill="#1B4332", outline="#2D6A4F", width=1)
    if len(flat_sr_p) >= 8:
        canvas.create_polygon(flat_sr_p, fill="#1B4332", outline="#2D6A4F", width=1)
    if len(flat_top) >= 8:
        canvas.create_polygon(flat_top, fill="#2D6A4F", outline="#40916C", width=1)

    # --- Траектории ---
    completed_slots = []
    completed_outlines = []  # Сегменты outline для отображения как прорезей
    completed_tabs = []      # Сегменты над перемычками (мост остаётся)
    pending_slot_start = None
    pending_outline_start = None  # Начало outline-сегмента

    for i, seg in enumerate(segs):
        if i >= end_idx:
            break
        seg_type = seg['type']
        col = _viz_tool_color(seg['tool'], tool_color_map)
        p0 = vp(seg['x0'], seg['y0'], seg['z0'])
        p1 = vp(seg['x1'], seg['y1'], seg['z1'])

        if seg_type == 'rapid':
            canvas.create_line(p0[0], p0[1], p1[0], p1[1],
                                fill="#555577", width=1, dash=(4, 4))
            pending_slot_start = None
            pending_outline_start = None
        elif seg_type == 'drill_down':
            canvas.create_line(p0[0], p0[1], p1[0], p1[1], fill=col, width=2)
            d_px = max(2, seg['diameter'] * sf * 0.5)
            pending_slot_start = (seg['x1'], seg['y1'], seg['diameter'], col, p1, d_px)
            pending_outline_start = (seg['x1'], seg['y1'], seg['diameter'], col)
        elif seg_type == 'drill_up':
            canvas.create_line(p0[0], p0[1], p1[0], p1[1], fill="#888899", width=1)
            if pending_slot_start:
                _sx, _sy, _diam, _scol, _sp1, _sd_px = pending_slot_start
                canvas.create_oval(_sp1[0]-_sd_px, _sp1[1]-_sd_px,
                                    _sp1[0]+_sd_px, _sp1[1]+_sd_px,
                                    fill="#0D0D0D", outline=_scol, width=1)
                pending_slot_start = None
            pending_outline_start = None
        elif seg_type == 'slot_h':
            if pending_slot_start:
                sx, sy, diam, scol, _p, _d = pending_slot_start
                completed_slots.append((sx, sy, seg['x1'], seg['y1'], diam, scol))
                pending_slot_start = None
            else:
                lw = max(2, int(seg['diameter'] * sf * 0.4))
                canvas.create_line(p0[0], p0[1], p1[0], p1[1],
                                    fill=col, width=lw, capstyle=tk.ROUND)
            pending_outline_start = None
        elif seg_type == 'outline':
            # Outline milling - собираем сегменты для отображения как прорезей
            completed_outlines.append((seg['x0'], seg['y0'], seg['x1'], seg['y1'], seg['diameter'], col))
            pending_outline_start = (seg['x1'], seg['y1'], seg['diameter'], col)
        elif seg_type == 'outline_tab':
            # Tab-участок — мост (материал внизу не прорезан), отрисовываем отдельно
            completed_tabs.append((seg['x0'], seg['y0'], seg['x1'], seg['y1'], seg['diameter'], col))
            pending_outline_start = (seg['x1'], seg['y1'], seg['diameter'], col)

    # Овальные прорези (слоты): per-tool бордер, чёрная заливка прорези.
    _draw_slot_like(canvas, completed_slots, vp, sf,
                    border_color=None, fill_color="#0D0D0D",
                    oval_fallback=True)

    # Прорези outline (финишная обрезка) — рисуются так же, как слоты.
    _draw_slot_like(canvas, completed_outlines, vp, sf,
                    border_color=None, fill_color="#0D0D0D",
                    oval_fallback=True)

    # Перемычки (tabs) поверх outline — мост из неразрезанного материала.
    # Ярко-оранжевая заливка с тёмно-коричневой обводкой поверх чёрных прорезей,
    # чтобы было видно, где плата ещё держится после обрезки. Точечные tabs
    # (length_px < 1) визуально бесполезны и пропускаются — отсюда oval_fallback=False.
    _draw_slot_like(canvas, completed_tabs, vp, sf,
                    border_color="#8B4513", fill_color="#F39C12",
                    oval_fallback=False)

    # --- Головка инструмента ---
    if end_idx > 0 and end_idx <= n:
        last = segs[end_idx - 1]
        hx, hy = vp(last['x1'], last['y1'], last['z1'])
        col = _viz_tool_color(last['tool'], tool_color_map)
        canvas.create_oval(hx-8, hy-8, hx+8, hy+8, fill="", outline="white", width=2)
        canvas.create_oval(hx-4, hy-4, hx+4, hy+4, fill=col, outline=col)
        canvas.create_text(hx+12, hy-10,
                            text=f"X{last['x1']:.2f} Y{last['y1']:.2f} Z{last['z1']:.2f}",
                            fill="white", font=("Arial", 8), anchor="w")

    if tool_color_map:
        lx, ly = cfg.CANVAS_WIDTH - 10, 10
        for tool_key, col in tool_color_map.items():
            canvas.create_rectangle(lx-60, ly, lx-48, ly+10, fill=col, outline="")
            canvas.create_text(lx-44, ly+5, text=f"T{tool_key}",
                                fill="white", font=("Arial", 8), anchor="w")
            ly += 14


# ---- Плеер ----

def viz_player_step():
    """Один шаг анимации."""
    if not cfg.viz_playing:
        return
    cfg.viz_play_index += 1
    n = len(cfg.viz_gcode_lines)
    if cfg.viz_play_index > n:
        cfg.viz_play_index = n
        cfg.viz_playing = False
        cfg.get_widget("viz_btn_play").config(text=t("viz.btn.play"))
        _viz_slider_set(n)
        redraw_viz(n)
        return

    redraw_viz(cfg.viz_play_index)
    _viz_slider_set(cfg.viz_play_index)
    cfg.get_widget("viz_pos_label").config(
        text=t("viz.lbl.position", current=cfg.viz_play_index, total=n))

    delay = max(10, int(300 / cfg.get_widget("viz_speed_var").get()))
    cfg.viz_after_id = cfg.get_widget("canvas").after(delay, viz_player_step)


def viz_play_pause():
    """Play/Pause переключение."""
    if cfg.viz_playing:
        cfg.viz_playing = False
        if cfg.viz_after_id:
            cfg.get_widget("canvas").after_cancel(cfg.viz_after_id)
        cfg.get_widget("viz_btn_play").config(text=t("viz.btn.play"))
    else:
        if cfg.viz_play_index >= len(cfg.viz_gcode_lines):
            viz_stop()
        cfg.viz_playing = True
        cfg.get_widget("viz_btn_play").config(text=t("viz.btn.pause"))
        viz_player_step()


def viz_stop():
    """Останов и сброс."""
    cfg.viz_playing = False
    if cfg.viz_after_id:
        cfg.get_widget("canvas").after_cancel(cfg.viz_after_id)
    cfg.viz_play_index = 0
    cfg.get_widget("viz_btn_play").config(text=t("viz.btn.play"))
    _viz_slider_set(0)
    redraw_viz(0)


def _viz_slider_set(val):
    """Установить позицию слайдера из кода."""
    cfg.get_widget("viz_slider").set(val)


def enter_viz_mode():
    """Вход в режим 2.5D визуализации."""
    cfg.viz_mode = True
    cfg.viz_play_index = 0
    cfg.viz_playing = False
    cfg.get_widget("viz_btn_play").config(text=t("viz.btn.play"))

    # Автомасштаб — вписать плату в 85% рабочей области
    segs = cfg.viz_gcode_lines
    if segs:
        xs = [s['x0'] for s in segs] + [s['x1'] for s in segs]
        ys = [s['y0'] for s in segs] + [s['y1'] for s in segs]
        bx0, bx1 = min(xs) - 3, max(xs) + 3
        by0, by1 = min(ys) - 3, max(ys) + 3
        bw = max(bx1 - bx0, 1)
        bh = max(by1 - by0, 1)
        cfg.viz_sf = min(cfg.WORKAREA_WIDTH * 0.85 / bw, cfg.WORKAREA_HEIGHT * 0.85 / bh)
        cfg.viz_ox = (bx0 + bx1) / 2
        cfg.viz_oy = (by0 + by1) / 2

    n = len(cfg.viz_gcode_lines)
    cfg.get_widget("viz_slider").config(to=max(1, n))
    _viz_slider_set(0)

    cfg.get_widget("viz_player_frame").pack(side="bottom", fill="x", before=cfg.get_widget("canvas"))
    cfg.get_widget("btn_visualize").config(text=t("viz.btn.back"))

    # Переключаем мышь на визуализатор
    canvas = cfg.get_widget("canvas")
    canvas.bind("<ButtonPress-1>", on_viz_drag_start)
    canvas.bind("<B1-Motion>", on_viz_drag)
    canvas.bind("<MouseWheel>", on_viz_mousewheel)
    # Linux: <Button-4>/<Button-5> вместо <MouseWheel>; .delta отсутствует —
    # проставляем вручную и переиспользуем сам event (у него уже есть x/y).
    canvas.bind("<Button-4>", _on_viz_wheel_up)
    canvas.bind("<Button-5>", _on_viz_wheel_down)

    redraw_viz(n)
    cfg.get_widget("status_label").config(text=t("viz.status.mode", n=n))


def _on_viz_wheel_up(event):
    """Linux: <Button-4> = прокрутка вверх в режиме визуализации."""
    event.delta = 120
    on_viz_mousewheel(event)


def _on_viz_wheel_down(event):
    """Linux: <Button-5> = прокрутка вниз в режиме визуализации."""
    event.delta = -120
    on_viz_mousewheel(event)


def on_viz_mousewheel(event):
    """Зум в режиме визуализации — колесо мыши."""
    cx_c = cfg.WORKAREA_OFFSET_X + cfg.WORKAREA_WIDTH / 2
    cy_c = cfg.WORKAREA_OFFSET_Y + cfg.WORKAREA_HEIGHT / 2
    mx = cfg.viz_ox + (event.x - cx_c) / cfg.viz_sf
    my = cfg.viz_oy - (event.y - cy_c) / cfg.viz_sf
    factor = 1.1 if event.delta > 0 else 0.9
    cfg.viz_sf = max(0.5, min(cfg.viz_sf * factor, 2000.0))
    cfg.viz_ox = mx - (event.x - cx_c) / cfg.viz_sf
    cfg.viz_oy = my + (event.y - cy_c) / cfg.viz_sf
    redraw_viz(cfg.viz_play_index)


def on_viz_drag_start(event):
    """Начало перетаскивания в viz."""
    cfg.drag_start_real_x = event.x
    cfg.drag_start_real_y = event.y
    cfg.initial_offset_x = cfg.viz_ox
    cfg.initial_offset_y = cfg.viz_oy


def on_viz_drag(event):
    """Перетаскивание в viz."""
    cfg.viz_ox = cfg.initial_offset_x - (event.x - cfg.drag_start_real_x) / cfg.viz_sf
    cfg.viz_oy = cfg.initial_offset_y + (event.y - cfg.drag_start_real_y) / cfg.viz_sf
    redraw_viz(cfg.viz_play_index)


def exit_viz_mode():
    """Выйти из режима визуализации."""
    cfg.viz_mode = False
    cfg.viz_playing = False
    if cfg.viz_after_id:
        cfg.get_widget("canvas").after_cancel(cfg.viz_after_id)
    cfg.get_widget("viz_player_frame").pack_forget()
    cfg.get_widget("btn_visualize").config(text=t("app.btn.visualize"))

    # Возвращаем оригинальные биндинги мыши (сохранённые при инициализации)
    canvas = cfg.get_widget("canvas")
    original_bindings = cfg.widgets.get("original_bindings")
    if original_bindings:
        canvas.bind("<ButtonPress-1>", original_bindings["button_press_1"])
        canvas.bind("<B1-Motion>", original_bindings["b1_motion"])
        canvas.bind("<Double-Button-1>", original_bindings["double_button_1"])
        canvas.bind("<Button-3>", original_bindings["button_3"])
        canvas.bind("<MouseWheel>", original_bindings["mousewheel"])
        canvas.bind("<Button-4>", original_bindings["button_4"])
        canvas.bind("<Button-5>", original_bindings["button_5"])
        canvas.bind("<Motion>", original_bindings["motion"])

    from ui.renderer import redraw_grid
    redraw_grid()
    cfg.get_widget("status_label").config(text=t("viz.status.view"))


def toggle_viz_mode():
    """Переключатель viz on/off."""
    if cfg.viz_mode:
        exit_viz_mode()
    else:
        if not cfg.viz_gcode_lines:
            messagebox.showwarning(t("viz.warning.title"), t("viz.warning.msg"))
            return
        enter_viz_mode()


def _store_gcode_for_viz(gcode_text):
    """Сохраняет G-code и активирует кнопку визуализации."""
    cfg.viz_gcode_lines = parse_gcode_for_viz(gcode_text)
    cfg.get_widget("btn_visualize").config(state="normal")
    cfg.get_widget("status_label").config(
        text=t("viz.status.ready", n=len(cfg.viz_gcode_lines)))
