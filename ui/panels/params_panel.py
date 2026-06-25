"""
Панель параметров G-code и обрезки по контуру.
"""
import tkinter as tk
from tkinter import ttk
from core.i18n import t
import core.config as cfg
from ui.enhanced_tooltip import EnhancedTooltip
from ui.numeric_entry import normalize_comma_inplace


def create_gcode_params_panel(parent, root, localize_widget, validate_numeric_entry, on_param_change):
    """Создать панель параметров G-code.
    
    Args:
        parent: Родительский виджет
        root: Корневое окно (для регистрации валидации)
        localize_widget: Функция локализации виджетов
        validate_numeric_entry: Функция валидации числовых полей
        on_param_change: Обработчик изменения параметров
    
    Returns:
        LabelFrame с панелью параметров
    """
    params_frame = tk.LabelFrame(parent, padx=5, pady=5)
    params_frame.pack(fill="x", padx=5, pady=2)
    localize_widget(params_frame, "app.frame.gcode_params")
    cfg.register_themed_widget(params_frame, bg="panel_bg", fg="panel_fg")

    params = [
        ("app.lbl.safe_z", "safe_z", "5.0"),
        ("app.lbl.drill_z", "drill_z", "-2.5"),
        ("app.lbl.feed_rate", "feed_rate", "100"),
        ("app.lbl.mill_feed", "mill_feed", "50"),
        ("app.lbl.rapid_rate", "rapid_rate", "500"),
        ("app.lbl.park_z", "park_z", "30"),
    ]

    param_entries = {}
    tooltip_keys = {
        "safe_z": "entry_safe_z",
        "drill_z": "entry_drill_z",
        "feed_rate": "entry_feed_rate",
        "mill_feed": "entry_mill_feed",
        "rapid_rate": "entry_rapid_rate",
        "park_z": "entry_park_z"
    }

    # Создать команду валидации для числовых полей
    validate_cmd = (root.register(validate_numeric_entry), '%P')

    for label_key, key, default in params:
        row = tk.Frame(params_frame)
        row.pack(fill="x", pady=1)
        cfg.register_themed_widget(row, bg="panel_bg")
        
        lbl = tk.Label(row, width=22, anchor="w")
        localize_widget(lbl, label_key)
        lbl.pack(side="left")
        cfg.register_themed_widget(lbl, bg="panel_bg", fg="panel_fg")
        
        entry = tk.Entry(row, width=8, validate='key', validatecommand=validate_cmd)
        entry.insert(0, default)
        cfg.register_themed_widget(entry, bg="entry_bg", fg="entry_fg", insertbackground="entry_fg")
        entry.pack(side="right")

        # Живая замена запятой на точку ('0,3' -> '0.3')
        entry.bind("<KeyRelease>", lambda e, w=entry: normalize_comma_inplace(w), add="+")
        # Автосохранение при потере фокуса или Enter
        entry.bind("<FocusOut>", on_param_change)
        entry.bind("<Return>", on_param_change)
        param_entries[key] = entry

        # Добавить tooltip
        if key in tooltip_keys:
            tt_key = f"tt.{tooltip_keys[key]}"
            EnhancedTooltip(entry, lambda k=tt_key: t(k))

    cfg.set_widget("safe_z_entry", param_entries["safe_z"])
    cfg.set_widget("drill_z_entry", param_entries["drill_z"])
    cfg.set_widget("feed_rate_entry", param_entries["feed_rate"])
    cfg.set_widget("mill_feed_entry", param_entries["mill_feed"])
    cfg.set_widget("rapid_rate_entry", param_entries["rapid_rate"])
    cfg.set_widget("park_z_entry", param_entries["park_z"])

    return params_frame


def create_outline_params_panel(parent, root, localize_widget, validate_numeric_entry, on_param_change):
    """Создать панель параметров обрезки по контуру.
    
    Args:
        parent: Родительский виджет
        root: Корневое окно (для регистрации валидации)
        localize_widget: Функция локализации виджетов
        validate_numeric_entry: Функция валидации числовых полей
        on_param_change: Обработчик изменения параметров
    
    Returns:
        LabelFrame с панелью параметров контура
    """
    outline_frame = tk.LabelFrame(parent, padx=5, pady=5)
    outline_frame.pack(fill="x", padx=5, pady=2)
    localize_widget(outline_frame, "app.frame.outline_cut")
    cfg.register_themed_widget(outline_frame, bg="panel_bg", fg="panel_fg")

    outline_params = [
        ("app.lbl.outline_tool_d", "outline_tool_diameter", "2.0"),
        ("app.lbl.outline_depth", "outline_depth_per_pass", "0.5"),
        ("app.lbl.outline_n_tabs", "outline_n_tabs", "4"),
        ("app.lbl.outline_tab_width", "outline_tab_width", "3.0"),
        ("app.lbl.outline_tab_height", "outline_tab_height", "1.0"),
    ]

    outline_entries = {}
    outline_tooltip_keys = {
        "outline_tool_diameter": "entry_outline_tool_diameter",
        "outline_depth_per_pass": "entry_outline_depth_per_pass",
        "outline_n_tabs": "entry_outline_n_tabs",
        "outline_tab_width": "entry_outline_tab_width",
        "outline_tab_height": "entry_outline_tab_height",
    }
    
    validate_cmd = (root.register(validate_numeric_entry), '%P')
    
    for label_key, key, default in outline_params:
        row = tk.Frame(outline_frame)
        row.pack(fill="x", pady=1)
        cfg.register_themed_widget(row, bg="panel_bg")
        
        lbl = tk.Label(row, width=22, anchor="w")
        localize_widget(lbl, label_key)
        lbl.pack(side="left")
        cfg.register_themed_widget(lbl, bg="panel_bg", fg="panel_fg")
        
        entry = tk.Entry(row, width=8, validate='key', validatecommand=validate_cmd)
        entry.insert(0, default)
        cfg.register_themed_widget(entry, bg="entry_bg", fg="entry_fg", insertbackground="entry_fg")
        entry.pack(side="right")

        # Живая замена запятой на точку ('0,3' -> '0.3')
        entry.bind("<KeyRelease>", lambda e, w=entry: normalize_comma_inplace(w), add="+")
        # Автосохранение при потере фокуса или Enter
        entry.bind("<FocusOut>", on_param_change)
        entry.bind("<Return>", on_param_change)
        outline_entries[key] = entry

        # Добавить tooltip
        if key in outline_tooltip_keys:
            tt_key = f"tt.{outline_tooltip_keys[key]}"
            EnhancedTooltip(entry, lambda k=tt_key: t(k))

    cfg.set_widget("outline_tool_diameter_entry", outline_entries["outline_tool_diameter"])
    cfg.set_widget("outline_depth_per_pass_entry", outline_entries["outline_depth_per_pass"])
    cfg.set_widget("outline_n_tabs_entry", outline_entries["outline_n_tabs"])
    cfg.set_widget("outline_tab_width_entry", outline_entries["outline_tab_width"])
    cfg.set_widget("outline_tab_height_entry", outline_entries["outline_tab_height"])

    # Direction (CCW/CW)
    dir_row = tk.Frame(outline_frame)
    dir_row.pack(fill="x", pady=1)
    cfg.register_themed_widget(dir_row, bg="panel_bg")
    
    dir_lbl = tk.Label(dir_row, width=18, anchor="w")
    localize_widget(dir_lbl, "app.lbl.outline_direction")
    dir_lbl.pack(side="left")
    cfg.register_themed_widget(dir_lbl, bg="panel_bg", fg="panel_fg")
    
    outline_direction_var = tk.StringVar(value="CCW")
    dir_combo = ttk.Combobox(dir_row, values=["CCW", "CW"], width=6, textvariable=outline_direction_var)
    dir_combo.pack(side="right")
    dir_combo.bind("<<ComboboxSelected>>", on_param_change)
    EnhancedTooltip(dir_combo, lambda: t("tt.combo_outline_direction"))
    cfg.set_widget("outline_direction_var", outline_direction_var)

    return outline_frame
