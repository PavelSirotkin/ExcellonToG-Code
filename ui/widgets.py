"""
Вспомогательные функции для работы с UI виджетами.
"""
import os
from tkinter import filedialog
from ui import themed_messagebox as messagebox
from core.parser import detect_coordinate_format, is_excellon_file, parse_excellon_file, parse_slot_file
from core.gerber_parser import parse_gerber_outline, is_gerber_file
from core.validators import validate_file_exists, validate_file_readable
from core.i18n import t
import core.config as cfg

_last_dir: str = ""


def _check_format_conflict(detected_format):
    """Проверить конфликт форматов с уже загруженным файлом.
    Возвращает формат, который следует использовать."""
    if detected_format and cfg.coordinate_format and detected_format != cfg.coordinate_format:
        msg = t("app.err.format_conflict.msg", 
                detected=detected_format, 
                current=cfg.coordinate_format)
        messagebox.showwarning(t("app.err.format_conflict.title"), msg)
        return cfg.coordinate_format
    return detected_format or cfg.coordinate_format


def _reload_all():
    """Перепарсить оба файла с текущим форматом, обновить вид."""
    try:
        if cfg.current_filename:
            cfg.current_tools = parse_excellon_file(cfg.current_filename)
        if cfg.slot_filename:
            cfg.slot_tools = parse_slot_file(cfg.slot_filename)
    except Exception as e:
        messagebox.showerror(t("app.dlg.error"), t("app.err.parsing", error=str(e)))
        return

    from ui.navigation import auto_fit_scale
    auto_fit_scale()
    from ui.renderer import redraw_grid
    redraw_grid()
    from ui.legend import update_legend
    update_legend()


def choose_file():
    """Диалог выбора Excellon файла с отверстиями."""
    global _last_dir
    filename = filedialog.askopenfilename(
        initialdir=_last_dir or None,
        filetypes=[(t("app.filetype.excellon"), "*.txt;*.drl"), (t("app.filetype.all"), "*.*")]
    )
    if not filename:
        return
    if not validate_file_exists(filename) or not validate_file_readable(filename):
        messagebox.showerror(t("app.dlg.error"), t("app.err.file_unavailable"))
        return
    if not is_excellon_file(filename):
        messagebox.showerror(t("app.dlg.error"), t("app.err.invalid_format"))
        return

    detected = detect_coordinate_format(filename)

    # Если слоты уже загружены — проверяем конфликт форматов
    if cfg.slot_filename:
        fmt = _check_format_conflict(detected)
    else:
        fmt = detected or cfg.coordinate_format
        cfg.coordinate_format = fmt
        cfg.get_widget("format_combobox").set(fmt)

    cfg.current_filename = filename
    cfg.get_widget("holes_file_label").config(text=t("app.lbl.holes_file", filename=os.path.basename(filename)))
    _reload_all()
    if not cfg.current_tools:
        messagebox.showwarning(t("app.dlg.warning"), t("app.err.no_tools"))
        cfg.current_filename = None
        return
    _last_dir = os.path.dirname(filename)
    cfg.get_widget("status_label").config(text=t("app.status.loaded", filename=os.path.basename(filename)))


def choose_slot_file():
    """Диалог выбора SlotHoles файла."""
    global _last_dir
    filename = filedialog.askopenfilename(
        initialdir=_last_dir or None,
        filetypes=[(t("app.filetype.slot"), "*.txt;*.drl"), (t("app.filetype.all"), "*.*")]
    )
    if not filename:
        return
    if not validate_file_exists(filename) or not validate_file_readable(filename):
        messagebox.showerror(t("app.dlg.error"), t("app.err.file_unavailable"))
        return
    if not is_excellon_file(filename):
        messagebox.showerror(t("app.dlg.error"), t("app.err.invalid_format"))
        return

    detected = detect_coordinate_format(filename)

    # Если holes уже загружены — проверяем конфликт форматов
    if cfg.current_filename:
        fmt = _check_format_conflict(detected)
    else:
        fmt = detected or cfg.coordinate_format
        cfg.coordinate_format = fmt
        cfg.get_widget("format_combobox").set(fmt)

    cfg.slot_filename = filename
    cfg.get_widget("slot_file_label").config(text=t("app.lbl.slots_file", filename=os.path.basename(filename)))
    _reload_all()
    if not cfg.slot_tools:
        messagebox.showwarning(t("app.dlg.warning"), t("app.err.no_slots"))
        cfg.slot_filename = None
        return
    _last_dir = os.path.dirname(filename)
    cfg.get_widget("status_label").config(text=t("app.status.slots_loaded", filename=os.path.basename(filename)))


def on_format_change(event):
    """Переформатирование при смене формата координат.
    Перепарсивает ОБА загруженных файла с новым форматом."""
    cfg.coordinate_format = cfg.get_widget("format_combobox").get()
    _reload_all()


def on_show_paths_change():
    """Редрав при переключении чекбокса путей."""
    from ui.renderer import redraw_grid
    redraw_grid()


def on_mouse_move(event):
    """Обновление координат в статус-баре при движении мыши."""
    from core.transforms import to_virtual_x, to_virtual_y
    if (cfg.WORKAREA_OFFSET_X <= event.x <= cfg.WORKAREA_OFFSET_X + cfg.WORKAREA_WIDTH and
            cfg.WORKAREA_OFFSET_Y <= event.y <= cfg.WORKAREA_OFFSET_Y + cfg.WORKAREA_HEIGHT):
        vx = to_virtual_x(event.x)
        vy = to_virtual_y(event.y)
        cfg.get_widget("coord_label").config(text=t("app.status.coord", x=vx, y=vy))
    else:
        cfg.get_widget("coord_label").config(text=t("app.status.coord_empty"))


def on_canvas_resize(event):
    """Обработка изменения размера canvas."""
    from ui.renderer import redraw_grid
    cfg.CANVAS_WIDTH = event.width
    cfg.CANVAS_HEIGHT = event.height
    cfg.WORKAREA_WIDTH = max(100, cfg.CANVAS_WIDTH - 80)
    cfg.WORKAREA_HEIGHT = max(100, cfg.CANVAS_HEIGHT - 80)
    redraw_grid()


def choose_outline_file():
    """Диалог выбора Gerber файла контура платы."""
    global _last_dir
    filename = filedialog.askopenfilename(
        initialdir=_last_dir or None,
        filetypes=[(t("app.filetype.gerber"), "*.gbr;*.gko;*.gm1;*.txt"), (t("app.filetype.all"), "*.*")]
    )
    if not filename:
        return
    if not validate_file_exists(filename) or not validate_file_readable(filename):
        messagebox.showerror(t("app.dlg.error"), t("app.err.file_unavailable"))
        return
    if not is_gerber_file(filename):
        messagebox.showerror(t("app.dlg.error"), t("app.err.invalid_gerber"))
        return

    try:
        segments, unit, bbox = parse_gerber_outline(filename)
        if not segments:
            messagebox.showwarning(t("app.dlg.warning"), t("app.err.no_outline_data"))
            return

        cfg.board_outline = segments
        cfg.board_outline_filename = filename
        cfg.board_outline_unit = unit
        cfg.get_widget("outline_file_label").config(text=t("app.lbl.outline_file", filename=os.path.basename(filename)))
        _last_dir = os.path.dirname(filename)
        cfg.get_widget("status_label").config(text=t("app.status.outline_loaded", filename=os.path.basename(filename)))

        # Автозум и перерисовка (важно даже если сверловки/слоты не загружены)
        from ui.navigation import auto_fit_scale
        auto_fit_scale()
        from ui.renderer import redraw_grid
        redraw_grid()
        from ui.legend import update_legend
        update_legend()

    except Exception as e:
        messagebox.showerror(t("app.dlg.error"), t("app.err.parsing_gerber", error=str(e)))


def clear_outline():
    """Очистить загруженный контур платы."""
    cfg.board_outline = None
    cfg.board_outline_filename = None
    cfg.board_outline_unit = "mm"
    cfg.outline_violations = []
    cfg.get_widget("outline_file_label").config(text=t("app.lbl.outline_not_loaded"))
    cfg.get_widget("status_label").config(text=t("app.status.outline_cleared"))

    # Перецентровка на оставшихся данных (или сброс если их нет)
    from ui.navigation import auto_fit_scale
    auto_fit_scale()
    from ui.renderer import redraw_grid
    redraw_grid()
    from ui.legend import update_legend
    update_legend()
