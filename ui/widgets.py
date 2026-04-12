"""
Вспомогательные функции для работы с UI виджетами.
"""
import os
from tkinter import messagebox, filedialog
from core.parser import detect_coordinate_format, is_excellon_file, parse_excellon_file, parse_slot_file
from core.validators import validate_file_exists, validate_file_readable
import core.config as cfg

_last_dir: str = ""


def _check_format_conflict(detected_format):
    """Проверить конфликт форматов с уже загруженным файлом.
    Возвращает формат, который следует использовать."""
    if detected_format and cfg.coordinate_format and detected_format != cfg.coordinate_format:
        messagebox.showwarning(
            "Несовпадение форматов",
            f"Формат координат нового файла ({detected_format}) отличается "
            f"от текущего ({cfg.coordinate_format}).\n\n"
            f"Будет использован формат {cfg.coordinate_format}."
        )
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
        messagebox.showerror("Ошибка", f"Ошибка парсинга: {str(e)}")
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
        filetypes=[("Excellon files", "*.txt;*.drl"), ("All files", "*.*")]
    )
    if not filename:
        return
    if not validate_file_exists(filename) or not validate_file_readable(filename):
        messagebox.showerror("Ошибка", "Файл недоступен.")
        return
    if not is_excellon_file(filename):
        messagebox.showerror("Ошибка", "Неверный формат файла.")
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
    cfg.get_widget("holes_file_label").config(text=f"Отверстия: {os.path.basename(filename)}")
    _reload_all()
    if not cfg.current_tools:
        messagebox.showwarning("Предупреждение",
                               "Файл не содержит данных об инструментах.")
        cfg.current_filename = None
        return
    _last_dir = os.path.dirname(filename)
    cfg.get_widget("status_label").config(text=f"Загружен: {os.path.basename(filename)}")


def choose_slot_file():
    """Диалог выбора SlotHoles файла."""
    global _last_dir
    filename = filedialog.askopenfilename(
        initialdir=_last_dir or None,
        filetypes=[("Excellon Slot files", "*.txt;*.drl"), ("All files", "*.*")]
    )
    if not filename:
        return
    if not validate_file_exists(filename) or not validate_file_readable(filename):
        messagebox.showerror("Ошибка", "Файл недоступен.")
        return
    if not is_excellon_file(filename):
        messagebox.showerror("Ошибка", "Неверный формат файла.")
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
    cfg.get_widget("slot_file_label").config(text=f"Слоты: {os.path.basename(filename)}")
    _reload_all()
    if not cfg.slot_tools:
        messagebox.showwarning("Предупреждение",
                               "Файл не содержит данных о слотах.")
        cfg.slot_filename = None
        return
    _last_dir = os.path.dirname(filename)
    cfg.get_widget("status_label").config(text=f"Слоты загружены: {os.path.basename(filename)}")


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
        cfg.get_widget("coord_label").config(text=f"X: {vx:.2f} мм  Y: {vy:.2f} мм")
    else:
        cfg.get_widget("coord_label").config(text="X: --- Y: ---")


def on_canvas_resize(event):
    """Обработка изменения размера canvas."""
    from ui.renderer import redraw_grid
    cfg.CANVAS_WIDTH = event.width
    cfg.CANVAS_HEIGHT = event.height
    cfg.WORKAREA_WIDTH = max(100, cfg.CANVAS_WIDTH - 80)
    cfg.WORKAREA_HEIGHT = max(100, cfg.CANVAS_HEIGHT - 80)
    redraw_grid()
