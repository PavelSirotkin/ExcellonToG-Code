"""
Всплывающие подсказки (tooltip) при клике на элементы.
"""
import logging
import math
import tkinter as tk
from core.transforms import to_virtual_x, to_virtual_y
import core.config as cfg

logger = logging.getLogger(__name__)


def _tooltip_hide():
    """Скрыть всплывающую подсказку."""
    if cfg._tooltip_window:
        try:
            cfg._tooltip_window.destroy()
        except Exception as e:
            logger.exception("Failed to destroy tooltip window: %s", e)
        cfg._tooltip_window = None


def _tooltip_show(canvas_x, canvas_y, text):
    """Показать всплывающую подсказку рядом с указанной точкой канваса."""
    _tooltip_hide()
    canvas = cfg.get_widget("canvas")
    if canvas is None:
        return
    rx = canvas.winfo_rootx() + canvas_x + 14
    ry = canvas.winfo_rooty() + canvas_y - 10
    tw = tk.Toplevel(cfg.get_widget("root"))
    tw.wm_overrideredirect(True)
    tw.wm_geometry(f"+{rx}+{ry}")
    tw.attributes("-topmost", True)
    lbl = tk.Label(tw, text=text,
                   background=cfg.get_color("tooltip_bg"),
                   foreground=cfg.get_color("tooltip_fg"),
                   relief="solid",
                   borderwidth=1, font=("Courier", 9), justify="left", padx=4, pady=2)
    lbl.pack()
    cfg._tooltip_window = tw


def on_canvas_click(event):
    """ПКМ на канвасе: если подсказка открыта — закрыть; иначе найти элемент и показать."""
    if cfg.viz_mode:
        return
    # Если подсказка уже видна — закрыть и выйти
    if cfg._tooltip_window is not None:
        _tooltip_hide()
        return
    # Перевести координаты клика в мм
    click_vx = to_virtual_x(event.x)
    click_vy = to_virtual_y(event.y)

    # Порог попадания в пикселях → переводим в мм
    HIT_PX = 8
    hit_mm = HIT_PX / cfg.scale_factor

    best_dist = hit_mm
    best_text = None

    # Проверяем отверстия
    if cfg.current_tools:
        for tool, data in cfg.current_tools.items():
            if not data['visible']:
                continue
            diam = data['diameter']
            for (x_mm, y_mm) in data['holes']:
                d = math.sqrt((x_mm - click_vx) ** 2 + (y_mm - click_vy) ** 2)
                if d < best_dist:
                    best_dist = d
                    best_text = (f"T{tool}  D={diam:.2f}mm  (отв.)\n"
                                 f"X={x_mm:.3f}  Y={y_mm:.3f} мм")

    # Проверяем слоты: ищем ближайшую точку на отрезке
    if cfg.slot_tools:
        for tool, data in cfg.slot_tools.items():
            if not data['visible']:
                continue
            diam = data['diameter']
            for idx, (start, end) in enumerate(data['slots']):
                sx, sy = start
                ex, ey = end
                # Ближайшая точка на отрезке
                dx, dy = ex - sx, ey - sy
                seg_len2 = dx * dx + dy * dy
                if seg_len2 > 0:
                    t = max(0.0, min(1.0, ((click_vx - sx) * dx + (click_vy - sy) * dy) / seg_len2))
                else:
                    t = 0.0
                near_x = sx + t * dx
                near_y = sy + t * dy
                d = math.sqrt((near_x - click_vx) ** 2 + (near_y - click_vy) ** 2)
                if d < best_dist:
                    best_dist = d
                    length = math.sqrt(dx * dx + dy * dy)
                    best_text = (f"T{tool}  D={diam:.2f}mm  (слот #{idx + 1})\n"
                                 f"  Start: X={sx:.3f}  Y={sy:.3f}\n"
                                 f"  End:   X={ex:.3f}  Y={ey:.3f}\n"
                                 f"  L={length:.3f} мм")

    if best_text:
        _tooltip_show(event.x, event.y, best_text)
    else:
        _tooltip_hide()
