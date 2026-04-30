"""
Главное приложение UI: создание GUI, всех виджетов, привязка событий.
"""
import os
import tkinter as tk
from tkinter import ttk, filedialog
from version import VERSION
from ui import themed_messagebox as messagebox
from core.mode_engine import ModeEngine
from core.gcode_params import GCodeParams
from core.app_settings import settings, default_settings_path
from core.i18n import t, set_language, get_language, register_listener
import core.config as cfg
from ui.enhanced_tooltip import EnhancedTooltip, TOOLTIPS

# Глобальный движок режимов
mode_engine = ModeEngine()
# Менеджер параметров G-code
gcode_params = GCodeParams()


# ==========================================================
# Реестр локализуемых виджетов
# Каждая запись — функция, которая знает, как обновить виджет при смене языка.
# ==========================================================
_lang_callbacks = []


def _register_lang_update(callback):
    """Запомнить колбэк перерисовки текста виджета при смене языка."""
    _lang_callbacks.append(callback)


def _apply_language_to_ui():
    """Вызвать все зарегистрированные колбэки — перерисовать тексты UI."""
    for cb in list(_lang_callbacks):
        try:
            cb()
        except Exception:
            pass
    # Обновить легенду при смене языка
    try:
        from ui.legend import update_legend
        update_legend()
    except Exception:
        pass


def _localize_widget(widget, key: str, **fmt_kwargs):
    """Установить виджету `text=t(key)` и зарегистрировать колбэк на смену языка."""
    def update():
        widget.config(text=t(key, **fmt_kwargs))
    update()
    _register_lang_update(update)
    return widget


def create_app():
    """Создание главного окна и всех UI компонентов."""
    # Загрузка пользовательских настроек (язык/тема) ДО создания виджетов
    settings.path = default_settings_path()
    settings.load()
    set_language(settings.get("language", "ru"))
    cfg.apply_theme(settings.get("theme", "light"))

    root = tk.Tk()
    def _update_title():
        root.title(t("app.title", version=VERSION))
    _update_title()
    _register_lang_update(_update_title)
    root.geometry("1720x900")
    root.minsize(1400, 800)
    ttk.Style(root).theme_use("clam")
    cfg.set_widget("root", root)
    cfg.register_themed_widget(root, bg="bg")

    main_frame = tk.Frame(root)
    main_frame.pack(fill="both", expand=True)
    cfg.register_themed_widget(main_frame, bg="bg")

    left_frame = tk.Frame(main_frame)
    left_frame.pack(side="left", fill="both", expand=True)
    cfg.register_themed_widget(left_frame, bg="bg")

    canvas = tk.Canvas(left_frame, width=cfg.CANVAS_WIDTH, height=cfg.CANVAS_HEIGHT)
    canvas.pack(fill="both", expand=True, padx=5, pady=5)
    cfg.set_widget("canvas", canvas)
    cfg.register_themed_widget(canvas, bg="canvas_bg")

    # Правая панель — две колонки: «Настройки» и «Работа»
    right_container = tk.Frame(main_frame)
    right_container.pack(side="right", fill="y", padx=5, pady=5)
    cfg.register_themed_widget(right_container, bg="bg")

    col_settings = tk.Frame(right_container, width=280)
    col_settings.pack(side="left", fill="y", padx=(0, 5))
    col_settings.pack_propagate(False)
    cfg.register_themed_widget(col_settings, bg="bg")

    col_state = tk.Frame(right_container, width=280)
    col_state.pack(side="left", fill="both", expand=True)
    col_state.pack_propagate(False)
    cfg.register_themed_widget(col_state, bg="bg")

    # ==========================================================
    # Колонка 1 — «Настройки»
    # ==========================================================

    # --- Файлы ---
    files_frame = tk.LabelFrame(col_settings, padx=5, pady=5)
    files_frame.pack(fill="x", padx=5, pady=2)
    _localize_widget(files_frame, "app.frame.files")
    cfg.register_themed_widget(files_frame, bg="panel_bg", fg="panel_fg")

    btn_excellon = tk.Button(files_frame, command=_choose_file)
    btn_excellon.pack(fill="x", pady=2)
    _localize_widget(btn_excellon, "app.btn.open_excellon")
    cfg.register_themed_widget(btn_excellon, bg="btn_bg", fg="btn_fg")
    EnhancedTooltip(btn_excellon, lambda: t("tt.btn_open_excellon"))

    holes_file_label = tk.Label(files_frame, font=("Arial", 8))
    holes_file_label.pack(anchor="w")
    _localize_widget(holes_file_label, "app.lbl.holes_not_loaded")
    cfg.set_widget("holes_file_label", holes_file_label)
    cfg.register_themed_widget(holes_file_label, bg="panel_bg", fg="text_muted")

    btn_slots = tk.Button(files_frame, command=_choose_slot_file)
    btn_slots.pack(fill="x", pady=2)
    _localize_widget(btn_slots, "app.btn.open_slots")
    cfg.register_themed_widget(btn_slots, bg="btn_bg", fg="btn_fg")
    EnhancedTooltip(btn_slots, lambda: t("tt.btn_open_slots"))

    slot_file_label = tk.Label(files_frame, font=("Arial", 8))
    slot_file_label.pack(anchor="w")
    _localize_widget(slot_file_label, "app.lbl.slots_not_loaded")
    cfg.set_widget("slot_file_label", slot_file_label)
    cfg.register_themed_widget(slot_file_label, bg="panel_bg", fg="text_muted")

    # --- Контур платы (Gerber) ---
    btn_gerber = tk.Button(files_frame, command=_choose_outline_file)
    btn_gerber.pack(fill="x", pady=2)
    _localize_widget(btn_gerber, "app.btn.open_outline")
    cfg.register_themed_widget(btn_gerber, bg="btn_bg", fg="btn_fg")
    EnhancedTooltip(btn_gerber, lambda: t("tt.btn_open_gerber"))
    outline_file_label = tk.Label(files_frame, font=("Arial", 8))
    outline_file_label.pack(anchor="w")
    _localize_widget(outline_file_label, "app.lbl.outline_not_loaded")
    cfg.set_widget("outline_file_label", outline_file_label)
    cfg.register_themed_widget(outline_file_label, bg="panel_bg", fg="text_muted")

    btn_clear_outline = tk.Button(files_frame, command=_clear_outline)
    btn_clear_outline.pack(fill="x", pady=2)
    _localize_widget(btn_clear_outline, "app.btn.clear_outline")
    cfg.register_themed_widget(btn_clear_outline, bg="btn_bg", fg="btn_fg")

    format_frame = tk.Frame(files_frame)
    format_frame.pack(fill="x", pady=2)
    cfg.register_themed_widget(format_frame, bg="panel_bg")
    format_lbl = tk.Label(format_frame)
    _localize_widget(format_lbl, "app.lbl.format")
    format_lbl.pack(side="left")
    cfg.register_themed_widget(format_lbl, bg="panel_bg", fg="panel_fg")
    format_combobox = ttk.Combobox(format_frame, values=["2.4", "3.3", "4.2"], width=6)
    format_combobox.set("4.2")
    format_combobox.pack(side="left", padx=5)
    format_combobox.bind("<<ComboboxSelected>>", _on_format_change)
    cfg.set_widget("format_combobox", format_combobox)

    # --- Параметры G-кода ---
    params_frame = tk.LabelFrame(col_settings, padx=5, pady=5)
    params_frame.pack(fill="x", padx=5, pady=2)
    _localize_widget(params_frame, "app.frame.gcode_params")
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

    for label_key, key, default in params:
        row = tk.Frame(params_frame)
        row.pack(fill="x", pady=1)
        cfg.register_themed_widget(row, bg="panel_bg")
        lbl = tk.Label(row, width=22, anchor="w")
        _localize_widget(lbl, label_key)
        lbl.pack(side="left")
        cfg.register_themed_widget(lbl, bg="panel_bg", fg="panel_fg")
        entry = tk.Entry(row, width=8)
        entry.insert(0, default)
        cfg.register_themed_widget(entry, bg="entry_bg", fg="entry_fg", insertbackground="entry_fg")
        entry.pack(side="right")
        # Автосохранение при потере фокуса или Enter
        entry.bind("<FocusOut>", _on_param_change)
        entry.bind("<Return>", _on_param_change)
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

    # --- Параметры обрезки по контуру ---
    outline_frame = tk.LabelFrame(col_settings, padx=5, pady=5)
    outline_frame.pack(fill="x", padx=5, pady=2)
    _localize_widget(outline_frame, "app.frame.outline_cut")
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
    for label_key, key, default in outline_params:
        row = tk.Frame(outline_frame)
        row.pack(fill="x", pady=1)
        cfg.register_themed_widget(row, bg="panel_bg")
        lbl = tk.Label(row, width=22, anchor="w")
        _localize_widget(lbl, label_key)
        lbl.pack(side="left")
        cfg.register_themed_widget(lbl, bg="panel_bg", fg="panel_fg")
        entry = tk.Entry(row, width=8)
        entry.insert(0, default)
        cfg.register_themed_widget(entry, bg="entry_bg", fg="entry_fg", insertbackground="entry_fg")
        entry.pack(side="right")
        # Автосохранение при потере фокуса или Enter
        entry.bind("<FocusOut>", _on_param_change)
        entry.bind("<Return>", _on_param_change)
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
    _localize_widget(dir_lbl, "app.lbl.outline_direction")
    dir_lbl.pack(side="left")
    cfg.register_themed_widget(dir_lbl, bg="panel_bg", fg="panel_fg")
    outline_direction_var = tk.StringVar(value="CCW")
    dir_combo = ttk.Combobox(dir_row, values=["CCW", "CW"], width=6, textvariable=outline_direction_var)
    dir_combo.pack(side="right")
    dir_combo.bind("<<ComboboxSelected>>", _on_param_change)
    EnhancedTooltip(dir_combo, lambda: t("tt.combo_outline_direction"))
    cfg.set_widget("outline_direction_var", outline_direction_var)

    # --- Группа "Опции" ---
    options_frame = tk.LabelFrame(col_settings, padx=5, pady=5)
    _localize_widget(options_frame, "app.frame.options")
    options_frame.pack(fill="both", expand=True, padx=5, pady=2)
    cfg.register_themed_widget(options_frame, bg="panel_bg", fg="panel_fg")

    # Верхняя часть: Режим и База
    top_frame = tk.Frame(options_frame)
    top_frame.pack(fill="x", pady=2)
    cfg.register_themed_widget(top_frame, bg="panel_bg")

    # --- Переключатель режимов ---
    from ui.mode_toggle import ModeToggle
    mode_toggle = ModeToggle(top_frame, mode_engine, on_mode_change=_on_mode_change)
    mode_toggle.pack(fill="x", pady=2)
    cfg.set_widget("mode_toggle", mode_toggle)

    # --- Кнопка базы инструментов (всегда видна, disabled в simple) ---
    btn_tool_db = tk.Button(top_frame,
                             command=_show_tool_db,
                             state="normal" if mode_engine.is_pro else "disabled")
    _localize_widget(btn_tool_db, "app.btn.tool_db")
    btn_tool_db.pack(fill="x", pady=2)
    cfg.set_widget("btn_tool_db", btn_tool_db)
    cfg.register_themed_widget(btn_tool_db, bg="btn_bg", fg="btn_fg")

    # Нижняя часть: Визуализация, Статистика, Справка
    bottom_frame = tk.Frame(options_frame)
    bottom_frame.pack(fill="x", side="bottom", pady=2)
    cfg.register_themed_widget(bottom_frame, bg="panel_bg")

    # --- Кнопка визуализации ---
    btn_visualize = tk.Button(bottom_frame,
                              command=_toggle_viz_mode, state="disabled",
                              font=("Arial", 9, "bold"))
    _localize_widget(btn_visualize, "app.btn.visualize")
    btn_visualize.pack(fill="x", pady=2)
    EnhancedTooltip(btn_visualize, lambda: t("tt.btn_visualize"))
    cfg.set_widget("btn_visualize", btn_visualize)
    cfg.register_themed_widget(btn_visualize, bg="btn_bg", fg="btn_fg")

    # --- Статистика и справка ---
    btn_stats = tk.Button(bottom_frame, command=_show_statistics)
    _localize_widget(btn_stats, "app.btn.statistics")
    btn_stats.pack(fill="x", pady=1)
    EnhancedTooltip(btn_stats, lambda: t("tt.btn_statistics"))
    cfg.register_themed_widget(btn_stats, bg="btn_bg", fg="btn_fg")
    
    btn_help = tk.Button(bottom_frame, command=_open_help)
    _localize_widget(btn_help, "app.btn.help")
    btn_help.pack(fill="x", pady=1)
    EnhancedTooltip(btn_help, lambda: t("tt.btn_help"))
    cfg.register_themed_widget(btn_help, bg="btn_bg", fg="btn_fg")

    # ==========================================================
    # Колонка 2 — «Работа»
    # ==========================================================

    # --- Отображение ---
    display_frame = tk.LabelFrame(col_state, padx=5, pady=5)
    _localize_widget(display_frame, "app.frame.display")
    display_frame.pack(fill="x", padx=5, pady=2)
    cfg.register_themed_widget(display_frame, bg="panel_bg", fg="panel_fg")

    show_paths_var = tk.BooleanVar(value=False)
    chk_paths = tk.Checkbutton(display_frame, variable=show_paths_var, command=_on_show_paths_change)
    _localize_widget(chk_paths, "app.lbl.show_paths")
    chk_paths.pack(anchor="w")
    cfg.set_widget("show_paths_var", show_paths_var)
    cfg.register_themed_widget(chk_paths, bg="panel_bg", fg="panel_fg", selectcolor="entry_bg")
    cfg.show_paths_var = show_paths_var

    # --- Кнопки генерации G-кода ---
    gcode_frame = tk.LabelFrame(col_state, padx=5, pady=5)
    _localize_widget(gcode_frame, "app.frame.gcode_gen")
    gcode_frame.pack(fill="x", padx=5, pady=2)
    cfg.register_themed_widget(gcode_frame, bg="panel_bg", fg="panel_fg")

    btn_gen_drill = tk.Button(gcode_frame, command=_generate_drilling_gcode)
    _localize_widget(btn_gen_drill, "app.btn.gen_drilling")
    btn_gen_drill.pack(fill="x", pady=2)
    EnhancedTooltip(btn_gen_drill, lambda: t("tt.btn_gen_drilling"))
    cfg.register_themed_widget(btn_gen_drill, bg="btn_gen_drilling", fg="btn_fg")
    
    btn_gen_mill = tk.Button(gcode_frame, command=_generate_milling_gcode)
    _localize_widget(btn_gen_mill, "app.btn.gen_milling")
    btn_gen_mill.pack(fill="x", pady=2)
    EnhancedTooltip(btn_gen_mill, lambda: t("tt.btn_gen_milling"))
    cfg.register_themed_widget(btn_gen_mill, bg="btn_gen_milling", fg="btn_fg")
    
    btn_gen_outline = tk.Button(gcode_frame, command=_generate_outline_gcode)
    _localize_widget(btn_gen_outline, "app.btn.gen_outline")
    btn_gen_outline.pack(fill="x", pady=2)
    EnhancedTooltip(btn_gen_outline, lambda: t("tt.btn_gen_outline"))
    cfg.register_themed_widget(btn_gen_outline, bg="btn_gen_outline", fg="btn_fg")
    
    btn_gen_combined = tk.Button(gcode_frame, command=_generate_combined_gcode)
    _localize_widget(btn_gen_combined, "app.btn.gen_combined")
    btn_gen_combined.pack(fill="x", pady=2)
    EnhancedTooltip(btn_gen_combined, lambda: t("tt.btn_gen_combined"))
    cfg.register_themed_widget(btn_gen_combined, bg="btn_gen_combined", fg="btn_fg")

    # --- Панель плеера (скрыта по умолчанию) — остаётся в left_frame ---
    viz_player_frame = tk.Frame(left_frame, bg="#2C2C3E", pady=4)
    cfg.set_widget("viz_player_frame", viz_player_frame)

    viz_top_row = tk.Frame(viz_player_frame, bg="#2C2C3E")
    viz_top_row.pack(fill="x", padx=6, pady=2)

    viz_btn_play = tk.Button(viz_top_row, text=t("viz.btn.play"), width=3,
                              command=_viz_play_pause, bg="#444466", fg="white",
                              relief="flat", font=("Arial", 11))
    viz_btn_play.pack(side="left", padx=2)
    cfg.set_widget("viz_btn_play", viz_btn_play)

    viz_speed_lbl = tk.Label(viz_top_row, bg="#2C2C3E",
             fg="#AAAACC", font=("Arial", 9))
    _localize_widget(viz_speed_lbl, "app.lbl.speed")
    viz_speed_lbl.pack(side="left", padx=(10, 2))
    viz_speed_var = tk.IntVar(value=5)
    cfg.set_widget("viz_speed_var", viz_speed_var)
    viz_speed_scale = tk.Scale(viz_top_row, from_=1, to=20,
                                orient="horizontal", variable=viz_speed_var,
                                bg="#2C2C3E", fg="#AAAACC", highlightthickness=0,
                                troughcolor="#444466", length=100, showvalue=True)
    viz_speed_scale.pack(side="left")

    viz_pos_label = tk.Label(viz_top_row, text=t("viz.lbl.position", current=0, total=0),
                              bg="#2C2C3E",
                              fg="#AAAACC", font=("Arial", 9))
    viz_pos_label.pack(side="right", padx=6)
    cfg.set_widget("viz_pos_label", viz_pos_label)

    viz_slider = tk.Scale(viz_player_frame, from_=0, to=1,
                           orient="horizontal",
                           bg="#2C2C3E", fg="#CCCCEE", highlightthickness=0,
                           troughcolor="#444466", showvalue=False)
    viz_slider.pack(fill="x", padx=6, pady=(0, 2))
    cfg.set_widget("viz_slider", viz_slider)

    viz_slider.bind("<B1-Motion>", _viz_slider_drag)
    viz_slider.bind("<ButtonRelease-1>", _viz_slider_release)

    # --- Легенда с прокруткой ---
    legend_outer_frame = tk.LabelFrame(col_state, padx=5, pady=5)
    _localize_widget(legend_outer_frame, "app.frame.tools")
    legend_outer_frame.pack(fill="both", expand=True, padx=5, pady=2)
    cfg.register_themed_widget(legend_outer_frame, bg="panel_bg", fg="panel_fg")

    legend_canvas = tk.Canvas(legend_outer_frame, highlightthickness=0)
    cfg.register_themed_widget(legend_canvas, bg="panel_bg")
    legend_scrollbar = tk.Scrollbar(legend_outer_frame, orient="vertical",
                                     command=legend_canvas.yview)
    legend_frame = tk.Frame(legend_canvas)
    cfg.register_themed_widget(legend_frame, bg="panel_bg")

    legend_frame.bind("<Configure>",
                      lambda e: legend_canvas.configure(scrollregion=legend_canvas.bbox("all")))
    legend_canvas.create_window((0, 0), window=legend_frame, anchor="nw")
    legend_canvas.configure(yscrollcommand=legend_scrollbar.set)

    legend_canvas.pack(side="left", fill="both", expand=True)
    legend_scrollbar.pack(side="right", fill="y")

    cfg.set_widget("legend_frame", legend_frame)
    cfg.set_widget("legend_canvas", legend_canvas)

    # --- События мыши ---
    canvas.bind("<ButtonPress-1>", _start_drag)
    canvas.bind("<B1-Motion>", _during_drag)
    canvas.bind("<Double-Button-1>", _on_double_click)
    canvas.bind("<Button-3>", _on_canvas_click)
    canvas.bind("<MouseWheel>", _on_mousewheel)
    canvas.bind("<Button-4>",
                lambda e: _on_mousewheel(tk.Event(type='MouseWheel', delta=120, x=e.x, y=e.y)))
    canvas.bind("<Button-5>",
                lambda e: _on_mousewheel(tk.Event(type='MouseWheel', delta=-120, x=e.x, y=e.y)))
    canvas.bind("<Motion>", _on_mouse_move)

    # Сохраняем оригинальные биндинги для восстановления после viz-режима
    _btn4 = lambda e: _on_mousewheel(tk.Event(type='MouseWheel', delta=120, x=e.x, y=e.y))
    _btn5 = lambda e: _on_mousewheel(tk.Event(type='MouseWheel', delta=-120, x=e.x, y=e.y))
    cfg.widgets["original_bindings"] = {
        "button_press_1": _start_drag,
        "b1_motion": _during_drag,
        "double_button_1": _on_double_click,
        "button_3": _on_canvas_click,
        "mousewheel": _on_mousewheel,
        "button_4": _btn4,
        "button_5": _btn5,
        "motion": _on_mouse_move,
    }

    # --- Строка состояния ---
    status_frame = tk.Frame(root, bd=1, relief=tk.SUNKEN)
    status_frame.pack(side="bottom", fill="x")
    cfg.register_themed_widget(status_frame, bg="panel_bg")
    status_label = tk.Label(status_frame, anchor="w", font=("Arial", 9))
    def _update_status():
        status_label.config(text=t("app.status.ready"))
    _update_status()
    _register_lang_update(_update_status)
    status_label.pack(side="left", padx=5)
    cfg.set_widget("status_label", status_label)
    cfg.register_themed_widget(status_label, bg="panel_bg", fg="text_status")
    
    coord_label = tk.Label(status_frame, anchor="e", font=("Arial", 9))
    def _update_coord():
        coord_label.config(text=t("app.status.coord_empty"))
    _update_coord()
    _register_lang_update(_update_coord)
    coord_label.pack(side="right", padx=5)
    cfg.set_widget("coord_label", coord_label)
    cfg.register_themed_widget(coord_label, bg="panel_bg", fg="text_status")

    canvas.bind("<Configure>", _on_canvas_resize)
    
    # Горячая клавиша F1 для вызова справки
    root.bind("<F1>", lambda e: _open_help())

    from ui.renderer import redraw_grid
    redraw_grid()

    # ==========================================================
    # Автозагрузка файлов базы инструментов и параметров G-code
    # ==========================================================
    # Определяем директорию приложения
    # Для .exe (PyInstaller) — директория .exe файла
    # Для запуска из исходников — корень проекта
    import sys
    if getattr(sys, 'frozen', False):
        # Запуск из .exe (PyInstaller)
        project_dir = os.path.dirname(sys.executable)
    else:
        # Запуск из исходников
        app_dir = os.path.dirname(os.path.abspath(__file__))
        project_dir = os.path.dirname(app_dir)

    # Загрузка параметров G-code
    gcode_params_file = os.path.join(project_dir, "gcode_params.json")
    gcode_params.path = gcode_params_file
    gcode_params.load()
    # Применить к Entry-виджетам
    gcode_params.apply_to_ui(cfg.widgets)

    # Загрузка базы инструментов
    tool_db_file = os.path.join(project_dir, "tool_base.json")
    mode_engine.tool_db.path = tool_db_file
    mode_engine.tool_db.load(tool_db_file)

    # Регистрация глобального слушателя смены языка
    register_listener(_apply_language_to_ui)

    # Добавить переключатель языка в правую панель (в группу "Вид")
    appearance_frame = tk.LabelFrame(col_settings, padx=5, pady=5)
    _localize_widget(appearance_frame, "app.frame.appearance")
    appearance_frame.pack(fill="x", padx=5, pady=2)
    cfg.register_themed_widget(appearance_frame, bg="panel_bg", fg="panel_fg")
    
    lang_row = tk.Frame(appearance_frame)
    lang_row.pack(fill="x", pady=2)
    cfg.register_themed_widget(lang_row, bg="panel_bg")
    lang_lbl = tk.Label(lang_row, width=18, anchor="w")
    _localize_widget(lang_lbl, "app.lbl.language")
    lang_lbl.pack(side="left")
    cfg.register_themed_widget(lang_lbl, bg="panel_bg", fg="panel_fg")
    
    lang_var = tk.StringVar(value=get_language())
    lang_combo = ttk.Combobox(lang_row, values=["ru", "en"], width=6, textvariable=lang_var, state="readonly")
    lang_combo.pack(side="right")
    
    def _on_language_change(event=None):
        new_lang = lang_var.get()
        set_language(new_lang)
        settings.set("language", new_lang)
        settings.save()
    
    lang_combo.bind("<<ComboboxSelected>>", _on_language_change)

    # Тема
    theme_row = tk.Frame(appearance_frame)
    theme_row.pack(fill="x", pady=2)
    cfg.register_themed_widget(theme_row, bg="panel_bg")
    theme_lbl = tk.Label(theme_row, width=18, anchor="w")
    _localize_widget(theme_lbl, "app.lbl.theme")
    theme_lbl.pack(side="left")
    cfg.register_themed_widget(theme_lbl, bg="panel_bg", fg="panel_fg")

    theme_var = tk.StringVar(value=cfg.current_theme())
    theme_combo = ttk.Combobox(theme_row, values=["light", "dark"], width=6,
                                textvariable=theme_var, state="readonly")
    theme_combo.pack(side="right")

    def _on_theme_change(event=None):
        new_theme = theme_var.get()
        cfg.apply_theme(new_theme)
        # Применить тему к заголовку главного окна
        cfg.apply_window_theme(root)
        settings.set("theme", new_theme)
        settings.save()

    theme_combo.bind("<<ComboboxSelected>>", _on_theme_change)

    # Настройка ttk-стилей для темы
    def _apply_ttk_styles():
        style = ttk.Style()
        style.configure("TCombobox",
                        fieldbackground=cfg.get_color("entry_bg"),
                        background=cfg.get_color("btn_bg"),
                        foreground=cfg.get_color("entry_fg"))
        style.map("TCombobox",
                  fieldbackground=[("readonly", cfg.get_color("entry_bg"))],
                  foreground=[("readonly", cfg.get_color("entry_fg"))],
                  selectbackground=[("readonly", cfg.get_color("entry_bg"))],
                  selectforeground=[("readonly", cfg.get_color("entry_fg"))])
        
        # Настройка Scrollbar для темной темы
        style.configure("Vertical.TScrollbar",
                        background=cfg.get_color("panel_bg"),
                        troughcolor=cfg.get_color("stats_bg"),
                        bordercolor=cfg.get_color("panel_bg"),
                        arrowcolor=cfg.get_color("panel_fg"))
        style.map("Vertical.TScrollbar",
                  background=[("active", cfg.get_color("entry_bg")),
                             ("pressed", cfg.get_color("entry_bg"))])

    cfg.register_theme_listener(_apply_ttk_styles)
    _apply_ttk_styles()  # Применить сразу

    # Применить темную тему к заголовку окна после полной инициализации
    root.after(100, lambda: cfg.apply_window_theme(root))

    return root


# ---- Обработчики событий (тонкая обёртка над модулями) ----

def _choose_file():
    from ui.widgets import choose_file
    choose_file()


def _choose_slot_file():
    from ui.widgets import choose_slot_file
    choose_slot_file()


def _choose_outline_file():
    from ui.widgets import choose_outline_file
    choose_outline_file()


def _clear_outline():
    from ui.widgets import clear_outline
    clear_outline()


def _on_format_change(event):
    from ui.widgets import on_format_change
    on_format_change(event)


def _on_show_paths_change():
    from ui.widgets import on_show_paths_change
    on_show_paths_change()


def _check_missing_tools(tool_type: str, tools_dict: dict) -> list:
    """В pro-режиме проверить, какие инструменты отсутствуют в базе.
    Возвращает список строк вида 'T1 D=1.00мм'."""
    if mode_engine.is_simple:
        return []
    missing = []
    if not tools_dict:
        return missing
    for tool_num, data in tools_dict.items():
        if not data['visible'] or not (data.get('holes') or data.get('slots')):
            continue
        if tool_type == "drill":
            if mode_engine.tool_db.find_drill(data['diameter']) is None:
                missing.append(f"T{tool_num} D={data['diameter']:.2f}мм")
        elif tool_type == "endmill":
            db = mode_engine.tool_db
            if (db.find_endmill(data['diameter']) is None and
                    db.find_endmill_smaller_than(data['diameter']) is None):
                missing.append(f"T{tool_num} D={data['diameter']:.2f}мм")
    return missing


def _show_missing_tools_warning(missing_tools: list) -> bool:
    """Показать предупреждение о недостающих инструментах.
    Возвращает True если пользователь согласился продолжить."""
    if not missing_tools:
        return True
    tool_list = "\n".join(f"  • {tool}" for tool in missing_tools)
    msg = t("app.dlg.missing_tools.msg", tool_list=tool_list)
    return messagebox.askyesno(t("app.dlg.missing_tools.title"), msg)


def _check_endmill_multipass(tools_dict) -> list:
    """В pro-режиме найти слоты, которые будут обработаны меньшей фрезой.
    Возвращает список строк для отображения пользователю."""
    if mode_engine.is_simple or not tools_dict:
        return []
    from core.gcode_generator import _calc_multipass_offsets
    result = []
    for tool_num, data in tools_dict.items():
        if not data['visible'] or not data['slots']:
            continue
        slot_d = data['diameter']
        db = mode_engine.tool_db
        if db.find_endmill(slot_d) is not None:
            continue  # точное совпадение — не multi-pass
        smaller = db.find_endmill_smaller_than(slot_d)
        if smaller is None:
            continue  # нет ничего — попадёт в missing
        tool_d = float(smaller["diameter"])
        stepover = smaller.get("stepover", 0)
        offsets = _calc_multipass_offsets(slot_d, tool_d, stepover)
        n = len(offsets)
        result.append(
            f"T{tool_num} ⌀{slot_d:.2f}мм → фреза ⌀{tool_d:.2f}мм, {n} проход{'а' if 2 <= n <= 4 else 'ов' if n >= 5 else ''}"
        )
    return result


def _show_multipass_warning(multipass_list: list) -> bool:
    """Предупредить пользователя о генерации multi-pass кода и спросить подтверждение."""
    if not multipass_list:
        return True
    tool_list = "\n".join(f"  • {tool}" for tool in multipass_list)
    msg = t("app.dlg.multipass.msg", tool_list=tool_list)
    return messagebox.askyesno(t("app.dlg.multipass.title"), msg)


def _build_drill_tool_params_dict():
    """В pro-режиме собрать {tool_number: params} из базы.
    Если инструмент не найден — параметры не добавляются (будет M03 без S)."""
    if mode_engine.is_simple:
        return None
    global_params = {
        'safe_z': cfg.get_param("safe_z"), 'drill_z': cfg.get_param("drill_z"),
        'feed_rate': cfg.get_param("feed_rate"), 'rapid_rate': cfg.get_param("rapid_rate"),
        'park_z': cfg.get_param("park_z"),
    }
    result = {}
    if not cfg.current_tools:
        return None
    for tool_num, data in cfg.current_tools.items():
        if not data['visible'] or not data['holes']:
            continue
        tp = mode_engine.get_drill_params(data['diameter'], global_params)
        if tp is not None:
            result[tool_num] = tp
        # Если None — инструмент не найден, генерируем без параметров
    return result


def _build_endmill_tool_params_dict():
    """В pro-режиме собрать {tool_number: params} из базы для фрез."""
    if mode_engine.is_simple:
        return None
    global_params = {
        'safe_z': cfg.get_param("safe_z"), 'drill_z': cfg.get_param("drill_z"),
        'feed_rate': cfg.get_param("feed_rate"), 'mill_feed': cfg.get_param("mill_feed"),
        'rapid_rate': cfg.get_param("rapid_rate"), 'park_z': cfg.get_param("park_z"),
    }
    result = {}
    if not cfg.slot_tools:
        return None
    for tool_num, data in cfg.slot_tools.items():
        if not data['visible'] or not data['slots']:
            continue
        tp = mode_engine.get_endmill_params_for_slot(data['diameter'], global_params)
        if tp is not None:
            result[tool_num] = tp
    return result


def _save_gcode_params_from_ui():
    """Сохранить текущие параметры G-code из Entry-виджетов."""
    gcode_params.read_from_ui(cfg.widgets)
    gcode_params.save()


def _on_param_change(event=None):
    """Автосохранение параметров при потере фокуса / нажатии Enter / выборе в Combobox."""
    try:
        _save_gcode_params_from_ui()
    except Exception:
        # Не ломаем UI из-за ошибки сохранения (например, временно невалидное значение)
        pass


def _enrich_outline_params_with_tool(outline_params: dict, global_params: dict) -> None:
    """Добавить в outline_params рабочую подачу и обороты шпинделя.

    Simple mode → подача берётся из "Подача фрезы" (mill_feed) глобальных параметров.
    Pro mode   → ищем фрезу по диаметру в базе и берём "cutting_feed" и "spindle_speed".
                 Если точной фрезы нет — пробуем меньшую.
                 Если не найдено ничего — откат на глобальные параметры.

    Изменяет outline_params in-place, добавляя ключи: mill_feed, plunge_feed, spindle_speed.
    """
    # Погружение по Z всегда от глобальной "Подача" (feed_rate)
    outline_params['plunge_feed'] = global_params.get('feed_rate', 100)

    diameter = outline_params.get('tool_diameter', 2.0)

    if mode_engine.is_simple:
        # Simple — единая «Подача фрезы»
        outline_params['mill_feed'] = global_params.get('mill_feed', 50)
        outline_params['spindle_speed'] = None
        return

    # Pro — ищем фрезу в базе
    db = mode_engine.tool_db
    tool = db.find_endmill(diameter)
    if tool is None:
        tool = db.find_endmill_smaller_than(diameter)

    if tool is not None:
        outline_params['mill_feed'] = float(tool.get('cutting_feed',
                                                     global_params.get('mill_feed', 50)))
        ss = tool.get('spindle_speed')
        outline_params['spindle_speed'] = int(ss) if ss else None
    else:
        # В базе нет — падаем на глобальные
        outline_params['mill_feed'] = global_params.get('mill_feed', 50)
        outline_params['spindle_speed'] = None


def _generate_drilling_gcode():
    from core.gcode_generator import _build_drilling_gcode
    from ui.gcode_viz import _store_gcode_for_viz
    from ui.dialogs import show_result_dialog

    _save_gcode_params_from_ui()

    # Проверка недостающих инструментов в pro-режиме
    missing = _check_missing_tools("drill", cfg.current_tools)
    if not _show_missing_tools_warning(missing):
        return

    params = {
        'safe_z': cfg.get_param("safe_z"),
        'drill_z': cfg.get_param("drill_z"),
        'feed_rate': cfg.get_param("feed_rate"),
        'rapid_rate': cfg.get_param("rapid_rate"),
        'park_z': cfg.get_param("park_z"),
    }
    tool_params = _build_drill_tool_params_dict()
    gcode_text, errors = _build_drilling_gcode(cfg.current_tools, cfg.current_filename, params, tool_params)
    if errors:
        messagebox.showwarning(t("app.dlg.warning"), "\n".join(errors))
        return
    filename = filedialog.asksaveasfilename(
        defaultextension=".tap",
        filetypes=[(t("app.filetype.tap"), "*.tap"), (t("app.filetype.gcode"), "*.gcode;*.nc;*.ngc"),
                   (t("app.filetype.all"), "*.*")],
        title=t("app.dlg.save_drilling.title")
    )
    if not filename:
        return
    try:
        with open(filename, 'w') as f:
            f.write(gcode_text)
    except IOError as e:
        messagebox.showerror(t("app.err.write.title"), t("app.err.write.msg", error=str(e)))
        return
    _store_gcode_for_viz(gcode_text)
    show_result_dialog(filename)


def _generate_milling_gcode():
    from core.gcode_generator import _build_milling_gcode
    from ui.gcode_viz import _store_gcode_for_viz
    from ui.dialogs import show_result_dialog

    _save_gcode_params_from_ui()

    # Проверка недостающих инструментов и multi-pass в pro-режиме
    missing = _check_missing_tools("endmill", cfg.slot_tools)
    if missing and not _show_missing_tools_warning(missing):
        return
    multipass = _check_endmill_multipass(cfg.slot_tools)
    if multipass and not _show_multipass_warning(multipass):
        return

    params = {
        'safe_z': cfg.get_param("safe_z"),
        'drill_z': cfg.get_param("drill_z"),
        'feed_rate': cfg.get_param("feed_rate"),
        'mill_feed': cfg.get_param("mill_feed"),
        'rapid_rate': cfg.get_param("rapid_rate"),
        'park_z': cfg.get_param("park_z"),
    }
    tool_params = _build_endmill_tool_params_dict()
    gcode_text, errors = _build_milling_gcode(cfg.slot_tools, cfg.slot_filename, params, tool_params)
    if errors:
        messagebox.showwarning(t("app.dlg.warning"), "\n".join(errors))
        return
    filename = filedialog.asksaveasfilename(
        defaultextension=".tap",
        filetypes=[(t("app.filetype.tap"), "*.tap"), (t("app.filetype.gcode"), "*.gcode;*.nc;*.ngc"),
                   (t("app.filetype.all"), "*.*")],
        title=t("app.dlg.save_milling.title")
    )
    if not filename:
        return
    try:
        with open(filename, 'w') as f:
            f.write(gcode_text)
    except IOError as e:
        messagebox.showerror(t("app.err.write.title"), t("app.err.write.msg", error=str(e)))
        return
    _store_gcode_for_viz(gcode_text)
    show_result_dialog(filename)


def _generate_combined_gcode():
    from core.gcode_generator import _build_combined_gcode
    from ui.gcode_viz import _store_gcode_for_viz
    from ui.dialogs import show_result_dialog
    from core.validators import validate_holes_within_outline, validate_outline_params
    from core.polygon_ops import flatten
    from ui.renderer import redraw_grid

    _save_gcode_params_from_ui()

    # Проверка недостающих инструментов и multi-pass в pro-режиме
    missing_drills = _check_missing_tools("drill", cfg.current_tools)
    missing_endmills = _check_missing_tools("endmill", cfg.slot_tools)
    all_missing = missing_drills + missing_endmills
    if all_missing and not _show_missing_tools_warning(all_missing):
        return
    multipass = _check_endmill_multipass(cfg.slot_tools)
    if multipass and not _show_multipass_warning(multipass):
        return

    params = {
        'safe_z': cfg.get_param("safe_z"),
        'drill_z': cfg.get_param("drill_z"),
        'feed_rate': cfg.get_param("feed_rate"),
        'mill_feed': cfg.get_param("mill_feed"),
        'rapid_rate': cfg.get_param("rapid_rate"),
        'park_z': cfg.get_param("park_z"),
    }
    drill_tp = _build_drill_tool_params_dict()
    endmill_tp = _build_endmill_tool_params_dict()
    tool_params_dict = {}
    if drill_tp:
        tool_params_dict["drills"] = drill_tp
    if endmill_tp:
        tool_params_dict["endmills"] = endmill_tp

    # Параметры обрезки по контуру
    outline_params = None
    if cfg.board_outline:
        outline_params = {
            'tool_diameter': cfg.get_param("outline_tool_diameter"),
            'depth_per_pass': cfg.get_param("outline_depth_per_pass"),
            'n_tabs': int(cfg.get_param("outline_n_tabs")),
            'tab_width': cfg.get_param("outline_tab_width"),
            'tab_height': cfg.get_param("outline_tab_height"),
            'direction': cfg.get_widget("outline_direction_var").get(),
        }
        # Подача / шпиндель: из global mill_feed (simple) или базы (pro)
        _enrich_outline_params_with_tool(outline_params, params)
        # Валидация параметров
        outline_errors = validate_outline_params(outline_params, params['drill_z'])
        if outline_errors:
            messagebox.showwarning(t("app.dlg.outline_params.title"), "\n".join(outline_errors))
            return

    # Валидация отверстий внутри контура
    if cfg.board_outline:
        outline_polygon = flatten(cfg.board_outline, tol_mm=0.5)
        violations = validate_holes_within_outline(
            cfg.current_tools, cfg.slot_tools, outline_polygon
        )
        cfg.outline_violations = [(desc, (x, y)) for desc, (x, y) in violations]
        redraw_grid()
        if violations:
            violation_list = "\n".join(f"  • {desc}" for desc, _ in violations[:10])
            if len(violations) > 10:
                violation_list += "\n" + t("app.dlg.violations.more", count=len(violations) - 10)
            msg = t("app.dlg.violations.msg", violation_list=violation_list)
            if not messagebox.askyesno(t("app.dlg.violations.title"), msg):
                return

    gcode_text, errors = _build_combined_gcode(
        cfg.current_tools, cfg.current_filename,
        cfg.slot_tools, cfg.slot_filename,
        params, tool_params_dict if tool_params_dict else None,
        board_outline=cfg.board_outline,
        board_outline_filename=cfg.board_outline_filename,
        outline_params=outline_params
    )
    if errors:
        messagebox.showwarning(t("app.dlg.warning"), "\n".join(errors))
        return
    filename = filedialog.asksaveasfilename(
        defaultextension=".tap",
        filetypes=[(t("app.filetype.tap"), "*.tap"), (t("app.filetype.gcode"), "*.gcode;*.nc;*.ngc"),
                   (t("app.filetype.all"), "*.*")],
        title=t("app.dlg.save_combined.title")
    )
    if not filename:
        return
    try:
        with open(filename, 'w') as f:
            f.write(gcode_text)
    except IOError as e:
        messagebox.showerror(t("app.err.write.title"), t("app.err.write.msg", error=str(e)))
        return
    _store_gcode_for_viz(gcode_text)
    show_result_dialog(filename)


def _generate_outline_gcode():
    """Генерация G-code только для обрезки по контуру платы."""
    from core.gcode_generator import _build_outline_only_gcode
    from ui.gcode_viz import _store_gcode_for_viz
    from ui.dialogs import show_result_dialog
    from core.validators import validate_holes_within_outline, validate_outline_params
    from core.polygon_ops import flatten
    from ui.renderer import redraw_grid

    _save_gcode_params_from_ui()

    if not cfg.board_outline:
        messagebox.showwarning(t("app.dlg.warning"), t("app.err.no_outline"))
        return

    params = {
        'safe_z': cfg.get_param("safe_z"),
        'drill_z': cfg.get_param("drill_z"),
        'feed_rate': cfg.get_param("feed_rate"),
        'mill_feed': cfg.get_param("mill_feed"),
        'rapid_rate': cfg.get_param("rapid_rate"),
        'park_z': cfg.get_param("park_z"),
    }
    outline_params = {
        'tool_diameter': cfg.get_param("outline_tool_diameter"),
        'depth_per_pass': cfg.get_param("outline_depth_per_pass"),
        'n_tabs': int(cfg.get_param("outline_n_tabs")),
        'tab_width': cfg.get_param("outline_tab_width"),
        'tab_height': cfg.get_param("outline_tab_height"),
        'direction': cfg.get_widget("outline_direction_var").get(),
    }
    # Подача / шпиндель: из global mill_feed (simple) или базы (pro)
    _enrich_outline_params_with_tool(outline_params, params)

    # Валидация параметров обрезки
    outline_errors = validate_outline_params(outline_params, params['drill_z'])
    if outline_errors:
        messagebox.showwarning(t("app.dlg.outline_params.title"), "\n".join(outline_errors))
        return

    # Если есть отверстия/слоты — проверим, что они внутри контура
    if cfg.current_tools or cfg.slot_tools:
        outline_polygon = flatten(cfg.board_outline, tol_mm=0.5)
        violations = validate_holes_within_outline(
            cfg.current_tools, cfg.slot_tools, outline_polygon
        )
        cfg.outline_violations = [(desc, (x, y)) for desc, (x, y) in violations]
        redraw_grid()
        if violations:
            violation_list = "\n".join(f"  • {desc}" for desc, _ in violations[:10])
            if len(violations) > 10:
                violation_list += "\n" + t("app.dlg.violations.more", count=len(violations) - 10)
            msg = t("app.dlg.violations.msg_outline", violation_list=violation_list)
            if not messagebox.askyesno(t("app.dlg.violations.title"), msg):
                return

    gcode_text, errors = _build_outline_only_gcode(
        cfg.board_outline, cfg.board_outline_filename, params, outline_params
    )
    if errors:
        messagebox.showwarning(t("app.dlg.warning"), "\n".join(errors))
        return
    filename = filedialog.asksaveasfilename(
        defaultextension=".tap",
        filetypes=[(t("app.filetype.tap"), "*.tap"), (t("app.filetype.gcode"), "*.gcode;*.nc;*.ngc"),
                   (t("app.filetype.all"), "*.*")],
        title=t("app.dlg.save_outline.title")
    )
    if not filename:
        return
    try:
        with open(filename, 'w') as f:
            f.write(gcode_text)
    except IOError as e:
        messagebox.showerror(t("app.err.write.title"), t("app.err.write.msg", error=str(e)))
        return
    _store_gcode_for_viz(gcode_text)
    show_result_dialog(filename)


def _show_statistics():
    from ui.dialogs import show_statistics
    show_statistics()


def _open_help():
    from ui.dialogs import open_help
    open_help()


def _toggle_viz_mode():
    from ui.gcode_viz import toggle_viz_mode
    toggle_viz_mode()


def _viz_play_pause():
    from ui.gcode_viz import viz_play_pause
    viz_play_pause()


def _viz_slider_drag(event):
    """Пользователь тащит ползунок — обновляем кадр."""
    cfg.viz_play_index = int(cfg.get_widget("viz_slider").get())
    cfg.get_widget("viz_pos_label").config(
        text=t("viz.lbl.position", current=cfg.viz_play_index, total=len(cfg.viz_gcode_lines)))
    from ui.gcode_viz import redraw_viz
    redraw_viz(cfg.viz_play_index)


def _viz_slider_release(event):
    """Отпустили ползунок — останавливаем автовоспроизведение."""
    from ui.gcode_viz import viz_stop
    if cfg.viz_playing:
        viz_stop()
    cfg.viz_play_index = int(cfg.get_widget("viz_slider").get())
    cfg.get_widget("viz_pos_label").config(
        text=t("viz.lbl.position", current=cfg.viz_play_index, total=len(cfg.viz_gcode_lines)))
    from ui.gcode_viz import redraw_viz
    redraw_viz(cfg.viz_play_index)


def _start_drag(event):
    from ui.navigation import start_drag
    start_drag(event)


def _during_drag(event):
    from ui.renderer import redraw_grid
    from ui.navigation import during_drag
    during_drag(event, redraw_grid)


def _on_double_click(event):
    from ui.renderer import redraw_grid
    from ui.navigation import on_double_click
    on_double_click(event, redraw_grid)


def _on_canvas_click(event):
    from ui.tooltip import on_canvas_click
    on_canvas_click(event)


def _on_mousewheel(event):
    from ui.renderer import redraw_grid
    from ui.navigation import on_mousewheel
    on_mousewheel(event, redraw_grid)


def _on_mouse_move(event):
    from ui.widgets import on_mouse_move
    on_mouse_move(event)


def _on_canvas_resize(event):
    from ui.widgets import on_canvas_resize
    on_canvas_resize(event)


def _on_mode_change(mode):
    """Обработчик переключения режима."""
    btn = cfg.get_widget("btn_tool_db")
    if btn:
        btn.config(state="normal" if mode == "pro" else "disabled")
    cfg.app_mode = mode
    # Обновить статус
    status = t("app.mode.pro") if mode == "pro" else t("app.mode.simple")
    cfg.get_widget("status_label").config(text=t("app.status.mode", status=status))


def _show_tool_db():
    """Показать диалог базы инструментов."""
    from ui.tool_db_dialog import show_tool_db_dialog
    show_tool_db_dialog(cfg.get_widget("root"), mode_engine.tool_db)
