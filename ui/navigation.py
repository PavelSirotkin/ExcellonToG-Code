"""
Управление навигацией: zoom, pan, drag, auto-fit.
"""
from core.config import MIN_SCALE
from core.transforms import clamp_offset
import core.config as cfg


def auto_fit_scale(all_points=None):
    """Автомасштаб — вписать все точки в рабочую область."""
    if all_points is None:
        all_points = []
        if cfg.current_tools:
            for tool_data in cfg.current_tools.values():
                if tool_data['visible']:
                    all_points.extend(tool_data['holes'])
        if cfg.slot_tools:
            for tool_data in cfg.slot_tools.values():
                if tool_data['visible']:
                    for start, end in tool_data['slots']:
                        all_points.append(start)
                        all_points.append(end)
        # Добавляем точки контура платы
        if cfg.board_outline:
            from core.polygon_ops import flatten
            outline_points = flatten(cfg.board_outline, tol_mm=0.5)
            all_points.extend(outline_points)

    if not all_points:
        cfg.scale_factor = MIN_SCALE
        cfg.offset_x = 0
        cfg.offset_y = 0
        return

    min_x = min(h[0] for h in all_points)
    max_x = max(h[0] for h in all_points)
    min_y = min(h[1] for h in all_points)
    max_y = max(h[1] for h in all_points)
    width = max_x - min_x
    height = max_y - min_y
    if width <= 0:
        width = 1
    if height <= 0:
        height = 1
    scale_x = cfg.WORKAREA_WIDTH / width * 0.9
    scale_y = cfg.WORKAREA_HEIGHT / height * 0.9
    cfg.scale_factor = min(scale_x, scale_y)
    cfg.scale_factor = max(MIN_SCALE, cfg.scale_factor)
    cfg.offset_x = (min_x + max_x) / 2
    cfg.offset_y = (min_y + max_y) / 2
    cfg.offset_x, cfg.offset_y = clamp_offset(cfg.offset_x, cfg.offset_y, cfg.scale_factor)


def on_mousewheel(event, redraw_callback):
    """Зум колесом мыши (с учётом точки под курсором)."""
    from ui.tooltip import _tooltip_hide
    _tooltip_hide()

    center_x = cfg.WORKAREA_OFFSET_X + cfg.WORKAREA_WIDTH / 2
    center_y = cfg.WORKAREA_OFFSET_Y + cfg.WORKAREA_HEIGHT / 2
    mx = cfg.offset_x + (event.x - center_x) / cfg.scale_factor
    my = cfg.offset_y + (center_y - event.y) / cfg.scale_factor
    new_scale = cfg.scale_factor * 1.1 if event.delta > 0 else cfg.scale_factor * 0.9
    new_scale = max(MIN_SCALE, min(new_scale, 1200.0))
    new_offset_x = mx - (event.x - center_x) / new_scale
    new_offset_y = my - (center_y - event.y) / new_scale
    new_offset_x, new_offset_y = clamp_offset(new_offset_x, new_offset_y, new_scale)
    cfg.scale_factor = new_scale
    cfg.offset_x = new_offset_x
    cfg.offset_y = new_offset_y
    redraw_callback()


def on_double_click(event, redraw_callback):
    """Двойной клик ЛКМ — сброс масштаба к автозуму."""
    if cfg.current_tools or cfg.slot_tools or cfg.board_outline:
        auto_fit_scale()
        redraw_callback()


def start_drag(event):
    """Начало перетаскивания."""
    from ui.tooltip import _tooltip_hide
    _tooltip_hide()
    cfg.drag_start_real_x = event.x
    cfg.drag_start_real_y = event.y
    cfg.initial_offset_x = cfg.offset_x
    cfg.initial_offset_y = cfg.offset_y


def during_drag(event, redraw_callback):
    """Перемещение при перетаскивании."""
    dx_real = event.x - cfg.drag_start_real_x
    dy_real = event.y - cfg.drag_start_real_y
    new_offset_x = cfg.initial_offset_x - dx_real / cfg.scale_factor
    new_offset_y = cfg.initial_offset_y + dy_real / cfg.scale_factor
    new_offset_x, new_offset_y = clamp_offset(new_offset_x, new_offset_y, cfg.scale_factor)
    cfg.offset_x = new_offset_x
    cfg.offset_y = new_offset_y
    redraw_callback()
