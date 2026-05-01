"""
Панель генерации G-code.
"""
import tkinter as tk
from core.i18n import t
import core.config as cfg
from ui.enhanced_tooltip import EnhancedTooltip


def create_gcode_panel(parent, localize_widget, handlers):
    """Создать панель генерации G-code.
    
    Args:
        parent: Родительский виджет
        localize_widget: Функция локализации виджетов
        handlers: Словарь с обработчиками событий
    
    Returns:
        LabelFrame с панелью генерации G-code
    """
    gcode_frame = tk.LabelFrame(parent, padx=5, pady=5)
    localize_widget(gcode_frame, "app.frame.gcode_gen")
    gcode_frame.pack(fill="x", padx=5, pady=2)
    cfg.register_themed_widget(gcode_frame, bg="panel_bg", fg="panel_fg")

    # Кнопка генерации сверления
    btn_gen_drill = tk.Button(gcode_frame, command=handlers['generate_drilling_gcode'])
    localize_widget(btn_gen_drill, "app.btn.gen_drilling")
    btn_gen_drill.pack(fill="x", pady=2)
    EnhancedTooltip(btn_gen_drill, lambda: t("tt.btn_gen_drilling"))
    cfg.register_themed_widget(btn_gen_drill, bg="btn_gen_drilling", fg="btn_fg")
    cfg.widgets["btn_gen_drill"] = btn_gen_drill
    
    # Кнопка генерации фрезерования
    btn_gen_mill = tk.Button(gcode_frame, command=handlers['generate_milling_gcode'])
    localize_widget(btn_gen_mill, "app.btn.gen_milling")
    btn_gen_mill.pack(fill="x", pady=2)
    EnhancedTooltip(btn_gen_mill, lambda: t("tt.btn_gen_milling"))
    cfg.register_themed_widget(btn_gen_mill, bg="btn_gen_milling", fg="btn_fg")
    cfg.widgets["btn_gen_mill"] = btn_gen_mill
    
    # Кнопка генерации контура
    btn_gen_outline = tk.Button(gcode_frame, command=handlers['generate_outline_gcode'])
    localize_widget(btn_gen_outline, "app.btn.gen_outline")
    btn_gen_outline.pack(fill="x", pady=2)
    EnhancedTooltip(btn_gen_outline, lambda: t("tt.btn_gen_outline"))
    cfg.register_themed_widget(btn_gen_outline, bg="btn_gen_outline", fg="btn_fg")
    cfg.widgets["btn_gen_outline"] = btn_gen_outline
    
    # Кнопка комбинированной генерации
    btn_gen_combined = tk.Button(gcode_frame, command=handlers['generate_combined_gcode'])
    localize_widget(btn_gen_combined, "app.btn.gen_combined")
    btn_gen_combined.pack(fill="x", pady=2)
    EnhancedTooltip(btn_gen_combined, lambda: t("tt.btn_gen_combined"))
    cfg.register_themed_widget(btn_gen_combined, bg="btn_gen_combined", fg="btn_fg")
    cfg.widgets["btn_gen_combined"] = btn_gen_combined

    return gcode_frame


def create_display_panel(parent, localize_widget, on_show_paths_change):
    """Создать панель отображения.
    
    Args:
        parent: Родительский виджет
        localize_widget: Функция локализации виджетов
        on_show_paths_change: Обработчик переключения отображения путей
    
    Returns:
        LabelFrame с панелью отображения
    """
    display_frame = tk.LabelFrame(parent, padx=5, pady=5)
    localize_widget(display_frame, "app.frame.display")
    display_frame.pack(fill="x", padx=5, pady=2)
    cfg.register_themed_widget(display_frame, bg="panel_bg", fg="panel_fg")

    show_paths_var = tk.BooleanVar(value=False)
    chk_paths = tk.Checkbutton(display_frame, variable=show_paths_var, command=on_show_paths_change)
    localize_widget(chk_paths, "app.lbl.show_paths")
    chk_paths.pack(anchor="w")
    cfg.set_widget("show_paths_var", show_paths_var)
    cfg.register_themed_widget(chk_paths, bg="panel_bg", fg="panel_fg", selectcolor="entry_bg")
    cfg.show_paths_var = show_paths_var

    return display_frame
