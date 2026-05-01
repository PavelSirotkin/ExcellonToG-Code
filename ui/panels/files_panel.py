"""
Панель работы с файлами (Excellon, слоты, контур).
"""
import tkinter as tk
from tkinter import ttk
from core.i18n import t
import core.config as cfg
from ui.enhanced_tooltip import EnhancedTooltip


def create_files_panel(parent, localize_widget, handlers):
    """Создать панель работы с файлами.
    
    Args:
        parent: Родительский виджет
        localize_widget: Функция локализации виджетов
        handlers: Словарь с обработчиками событий
    
    Returns:
        LabelFrame с панелью файлов
    """
    files_frame = tk.LabelFrame(parent, padx=5, pady=5)
    files_frame.pack(fill="x", padx=5, pady=2)
    localize_widget(files_frame, "app.frame.files")
    cfg.register_themed_widget(files_frame, bg="panel_bg", fg="panel_fg")

    # Кнопка открытия Excellon
    btn_excellon = tk.Button(files_frame, command=handlers['choose_file'])
    btn_excellon.pack(fill="x", pady=2)
    localize_widget(btn_excellon, "app.btn.open_excellon")
    cfg.register_themed_widget(btn_excellon, bg="btn_bg", fg="btn_fg")
    EnhancedTooltip(btn_excellon, lambda: t("tt.btn_open_excellon"))

    holes_file_label = tk.Label(files_frame, font=("Arial", 8))
    holes_file_label.pack(anchor="w")
    localize_widget(holes_file_label, "app.lbl.holes_not_loaded")
    cfg.set_widget("holes_file_label", holes_file_label)
    cfg.register_themed_widget(holes_file_label, bg="panel_bg", fg="text_muted")

    # Кнопка открытия слотов
    btn_slots = tk.Button(files_frame, command=handlers['choose_slot_file'])
    btn_slots.pack(fill="x", pady=2)
    localize_widget(btn_slots, "app.btn.open_slots")
    cfg.register_themed_widget(btn_slots, bg="btn_bg", fg="btn_fg")
    EnhancedTooltip(btn_slots, lambda: t("tt.btn_open_slots"))

    slot_file_label = tk.Label(files_frame, font=("Arial", 8))
    slot_file_label.pack(anchor="w")
    localize_widget(slot_file_label, "app.lbl.slots_not_loaded")
    cfg.set_widget("slot_file_label", slot_file_label)
    cfg.register_themed_widget(slot_file_label, bg="panel_bg", fg="text_muted")

    # Кнопка открытия контура (Gerber)
    btn_gerber = tk.Button(files_frame, command=handlers['choose_outline_file'])
    btn_gerber.pack(fill="x", pady=2)
    localize_widget(btn_gerber, "app.btn.open_outline")
    cfg.register_themed_widget(btn_gerber, bg="btn_bg", fg="btn_fg")
    EnhancedTooltip(btn_gerber, lambda: t("tt.btn_open_gerber"))
    
    outline_file_label = tk.Label(files_frame, font=("Arial", 8))
    outline_file_label.pack(anchor="w")
    localize_widget(outline_file_label, "app.lbl.outline_not_loaded")
    cfg.set_widget("outline_file_label", outline_file_label)
    cfg.register_themed_widget(outline_file_label, bg="panel_bg", fg="text_muted")

    # Кнопки очистки
    btn_clear_slots = tk.Button(files_frame, command=handlers['clear_slots'])
    btn_clear_slots.pack(fill="x", pady=2)
    localize_widget(btn_clear_slots, "app.btn.clear_slots")
    cfg.register_themed_widget(btn_clear_slots, bg="btn_bg", fg="btn_fg")

    btn_clear_outline = tk.Button(files_frame, command=handlers['clear_outline'])
    btn_clear_outline.pack(fill="x", pady=2)
    localize_widget(btn_clear_outline, "app.btn.clear_outline")
    cfg.register_themed_widget(btn_clear_outline, bg="btn_bg", fg="btn_fg")

    # Выбор формата координат
    format_frame = tk.Frame(files_frame)
    format_frame.pack(fill="x", pady=2)
    cfg.register_themed_widget(format_frame, bg="panel_bg")
    
    format_lbl = tk.Label(format_frame)
    localize_widget(format_lbl, "app.lbl.format")
    format_lbl.pack(side="left")
    cfg.register_themed_widget(format_lbl, bg="panel_bg", fg="panel_fg")
    
    format_combobox = ttk.Combobox(format_frame, values=["2.4", "3.3", "4.2"], width=6)
    format_combobox.set("4.2")
    format_combobox.pack(side="left", padx=5)
    format_combobox.bind("<<ComboboxSelected>>", handlers['on_format_change'])
    cfg.set_widget("format_combobox", format_combobox)

    return files_frame
