"""
Главное приложение UI: создание GUI, всех виджетов, привязка событий.
"""
import os
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from version import VERSION
from core.mode_engine import ModeEngine
from core.gcode_params import GCodeParams
import core.config as cfg

# Глобальный движок режимов
mode_engine = ModeEngine()
# Менеджер параметров G-code
gcode_params = GCodeParams()


def create_app():
    """Создание главного окна и всех UI компонентов."""
    root = tk.Tk()
    root.title(f"Excellon To G-code: Сверление + Фрезеровка слотов V {VERSION}")
    root.geometry("1600x900")
    root.minsize(1280, 800)
    ttk.Style(root).theme_use("clam")
    cfg.set_widget("root", root)

    main_frame = tk.Frame(root)
    main_frame.pack(fill="both", expand=True)

    left_frame = tk.Frame(main_frame)
    left_frame.pack(side="left", fill="both", expand=True)

    canvas = tk.Canvas(left_frame, width=cfg.CANVAS_WIDTH, height=cfg.CANVAS_HEIGHT, bg="#F0F0F0")
    canvas.pack(fill="both", expand=True, padx=5, pady=5)
    cfg.set_widget("canvas", canvas)

    right_frame = tk.Frame(main_frame, width=280)
    right_frame.pack(side="right", fill="y", padx=5, pady=5)
    right_frame.pack_propagate(False)

    # --- Файлы ---
    files_frame = tk.LabelFrame(right_frame, text="Файлы", padx=5, pady=5)
    files_frame.pack(fill="x", padx=5, pady=2)

    tk.Button(files_frame, text="📂 Открыть Excellon (отверстия)",
              command=_choose_file).pack(fill="x", pady=2)
    holes_file_label = tk.Label(files_frame, text="Отверстия: не загружены",
                                font=("Arial", 8), fg="gray")
    holes_file_label.pack(anchor="w")
    cfg.set_widget("holes_file_label", holes_file_label)

    tk.Button(files_frame, text="📂 Открыть SlotHoles (слоты)",
              command=_choose_slot_file).pack(fill="x", pady=2)
    slot_file_label = tk.Label(files_frame, text="Слоты: не загружены",
                               font=("Arial", 8), fg="gray")
    slot_file_label.pack(anchor="w")
    cfg.set_widget("slot_file_label", slot_file_label)

    format_frame = tk.Frame(files_frame)
    format_frame.pack(fill="x", pady=2)
    tk.Label(format_frame, text="Формат:").pack(side="left")
    format_combobox = ttk.Combobox(format_frame, values=["2.4", "3.3", "4.2"], width=6)
    format_combobox.set("4.2")
    format_combobox.pack(side="left", padx=5)
    format_combobox.bind("<<ComboboxSelected>>", _on_format_change)
    cfg.set_widget("format_combobox", format_combobox)

    # --- Параметры G-кода ---
    params_frame = tk.LabelFrame(right_frame, text="Параметры G-кода", padx=5, pady=5)
    params_frame.pack(fill="x", padx=5, pady=2)

    params = [
        ("Безопасная Z (мм):", "safe_z", "5.0"),
        ("Глубина (мм):", "drill_z", "-2.5"),
        ("Подача (мм/мин):", "feed_rate", "100"),
        ("Подача фрезы (мм/мин):", "mill_feed", "50"),
        ("Быстрая подача (мм/мин):", "rapid_rate", "500"),
        ("Парковка Z (мм):", "park_z", "30"),
    ]

    param_entries = {}
    for label_text, key, default in params:
        row = tk.Frame(params_frame)
        row.pack(fill="x", pady=1)
        tk.Label(row, text=label_text, width=22, anchor="w").pack(side="left")
        entry = tk.Entry(row, width=8)
        entry.insert(0, default)
        entry.pack(side="right")
        param_entries[key] = entry

    cfg.set_widget("safe_z_entry", param_entries["safe_z"])
    cfg.set_widget("drill_z_entry", param_entries["drill_z"])
    cfg.set_widget("feed_rate_entry", param_entries["feed_rate"])
    cfg.set_widget("mill_feed_entry", param_entries["mill_feed"])
    cfg.set_widget("rapid_rate_entry", param_entries["rapid_rate"])
    cfg.set_widget("park_z_entry", param_entries["park_z"])

    # --- Отображение ---
    options_frame = tk.LabelFrame(right_frame, text="Отображение", padx=5, pady=5)
    options_frame.pack(fill="x", padx=5, pady=2)

    show_paths_var = tk.BooleanVar(value=False)
    tk.Checkbutton(options_frame, text="Отобразить пути",
                   variable=show_paths_var, command=_on_show_paths_change).pack(anchor="w")
    cfg.set_widget("show_paths_var", show_paths_var)
    cfg.show_paths_var = show_paths_var

    # --- Переключатель режимов ---
    from ui.mode_toggle import ModeToggle
    mode_toggle = ModeToggle(right_frame, mode_engine, on_mode_change=_on_mode_change)
    mode_toggle.pack(fill="x", padx=5, pady=2)
    cfg.set_widget("mode_toggle", mode_toggle)

    # --- Кнопка базы инструментов (всегда видна, disabled в simple) ---
    btn_tool_db = tk.Button(right_frame, text="🗄 База инструментов",
                             command=_show_tool_db, bg="#E0E0E0",
                             state="normal" if mode_engine.is_pro else "disabled")
    btn_tool_db.pack(fill="x", padx=5, pady=2)
    cfg.set_widget("btn_tool_db", btn_tool_db)

    # --- Кнопки генерации G-кода ---
    gcode_frame = tk.LabelFrame(right_frame, text="Генерация G-кода", padx=5, pady=5)
    gcode_frame.pack(fill="x", padx=5, pady=2)

    tk.Button(gcode_frame, text="⚙ G-код сверления",
              command=_generate_drilling_gcode, bg="#90EE90").pack(fill="x", pady=2)
    tk.Button(gcode_frame, text="⚙ G-код фрезеровки слотов",
              command=_generate_milling_gcode, bg="#87CEEB").pack(fill="x", pady=2)
    tk.Button(gcode_frame, text="⚙ Объединённый G-код",
              command=_generate_combined_gcode, bg="#FFD700").pack(fill="x", pady=2)

    # Статистика и справка
    tk.Button(right_frame, text="📊 Статистика", command=_show_statistics).pack(
        fill="x", padx=5, pady=2)
    tk.Button(right_frame, text="❓ Справка", command=_open_help).pack(
        fill="x", padx=5, pady=2)

    # --- Кнопка визуализации ---
    btn_visualize = tk.Button(right_frame, text="🎬 Визуализация G-code",
                              command=_toggle_viz_mode,
                              bg="#DDA0DD", state="disabled",
                              font=("Arial", 9, "bold"))
    btn_visualize.pack(fill="x", padx=5, pady=4)
    cfg.set_widget("btn_visualize", btn_visualize)

    # --- Панель плеера (скрыта по умолчанию) ---
    viz_player_frame = tk.Frame(left_frame, bg="#2C2C3E", pady=4)
    cfg.set_widget("viz_player_frame", viz_player_frame)

    viz_top_row = tk.Frame(viz_player_frame, bg="#2C2C3E")
    viz_top_row.pack(fill="x", padx=6, pady=2)

    viz_btn_play = tk.Button(viz_top_row, text="▶", width=3,
                              command=_viz_play_pause, bg="#444466", fg="white",
                              relief="flat", font=("Arial", 11))
    viz_btn_play.pack(side="left", padx=2)
    cfg.set_widget("viz_btn_play", viz_btn_play)

    tk.Label(viz_top_row, text="Скорость:", bg="#2C2C3E",
             fg="#AAAACC", font=("Arial", 9)).pack(side="left", padx=(10, 2))
    viz_speed_var = tk.IntVar(value=5)
    cfg.set_widget("viz_speed_var", viz_speed_var)
    viz_speed_scale = tk.Scale(viz_top_row, from_=1, to=20,
                                orient="horizontal", variable=viz_speed_var,
                                bg="#2C2C3E", fg="#AAAACC", highlightthickness=0,
                                troughcolor="#444466", length=100, showvalue=True)
    viz_speed_scale.pack(side="left")

    viz_pos_label = tk.Label(viz_top_row, text="0 / 0", bg="#2C2C3E",
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
    legend_outer_frame = tk.LabelFrame(right_frame, text="Инструменты", padx=5, pady=5)
    legend_outer_frame.pack(fill="both", expand=True, padx=5, pady=2)

    legend_canvas = tk.Canvas(legend_outer_frame, highlightthickness=0)
    legend_scrollbar = tk.Scrollbar(legend_outer_frame, orient="vertical",
                                     command=legend_canvas.yview)
    legend_frame = tk.Frame(legend_canvas)

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
    status_label = tk.Label(status_frame, text="Готово. Загрузите файл Excellon.",
                            anchor="w", font=("Arial", 9))
    status_label.pack(side="left", padx=5)
    cfg.set_widget("status_label", status_label)
    
    coord_label = tk.Label(status_frame, text="X: --- Y: ---",
                            anchor="e", font=("Arial", 9))
    coord_label.pack(side="right", padx=5)
    cfg.set_widget("coord_label", coord_label)

    canvas.bind("<Configure>", _on_canvas_resize)

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

    return root


# ---- Обработчики событий (тонкая обёртка над модулями) ----

def _choose_file():
    from ui.widgets import choose_file
    choose_file()


def _choose_slot_file():
    from ui.widgets import choose_slot_file
    choose_slot_file()


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
    tool_list = "\n".join(f"  • {t}" for t in missing_tools)
    msg = (f"Отсутствуют инструменты в базе:\n\n{tool_list}\n\n"
           f"Для них будет создан G-code без параметров шпинделя.\n\n"
           f"Продолжить генерацию?")
    return messagebox.askyesno("Отсутствуют инструменты", msg)


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
    tool_list = "\n".join(f"  • {t}" for t in multipass_list)
    msg = (f"Точные фрезы не найдены. Будет использована фреза меньшего диаметра\n"
           f"с несколькими параллельными проходами:\n\n{tool_list}\n\n"
           f"Сгенерировать G-code с многопроходной фрезеровкой?")
    return messagebox.askyesno("Многопроходная фрезеровка", msg)


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
        messagebox.showwarning("Предупреждение", "\n".join(errors))
        return
    filename = filedialog.asksaveasfilename(
        defaultextension=".tap",
        filetypes=[("TAP files", "*.tap"), ("G-Code files", "*.gcode;*.nc;*.ngc"),
                   ("All files", "*.*")],
        title="Сохранить G-код сверления"
    )
    if not filename:
        return
    try:
        with open(filename, 'w') as f:
            f.write(gcode_text)
    except IOError as e:
        messagebox.showerror("Ошибка записи", f"Не удалось сохранить файл:\n{e}")
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
        messagebox.showwarning("Предупреждение", "\n".join(errors))
        return
    filename = filedialog.asksaveasfilename(
        defaultextension=".tap",
        filetypes=[("TAP files", "*.tap"), ("G-Code files", "*.gcode;*.nc;*.ngc"),
                   ("All files", "*.*")],
        title="Сохранить G-код фрезеровки слотов"
    )
    if not filename:
        return
    try:
        with open(filename, 'w') as f:
            f.write(gcode_text)
    except IOError as e:
        messagebox.showerror("Ошибка записи", f"Не удалось сохранить файл:\n{e}")
        return
    _store_gcode_for_viz(gcode_text)
    show_result_dialog(filename)


def _generate_combined_gcode():
    from core.gcode_generator import _build_combined_gcode
    from ui.gcode_viz import _store_gcode_for_viz
    from ui.dialogs import show_result_dialog

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

    gcode_text, errors = _build_combined_gcode(cfg.current_tools, cfg.current_filename,
                                                cfg.slot_tools, cfg.slot_filename,
                                                params, tool_params_dict if tool_params_dict else None)
    if errors:
        messagebox.showwarning("Предупреждение", "\n".join(errors))
        return
    filename = filedialog.asksaveasfilename(
        defaultextension=".tap",
        filetypes=[("TAP files", "*.tap"), ("G-Code files", "*.gcode;*.nc;*.ngc"),
                   ("All files", "*.*")],
        title="Сохранить объединённый G-код"
    )
    if not filename:
        return
    try:
        with open(filename, 'w') as f:
            f.write(gcode_text)
    except IOError as e:
        messagebox.showerror("Ошибка записи", f"Не удалось сохранить файл:\n{e}")
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
    cfg.get_widget("viz_pos_label").config(text=f"{cfg.viz_play_index} / {len(cfg.viz_gcode_lines)}")
    from ui.gcode_viz import redraw_viz
    redraw_viz(cfg.viz_play_index)


def _viz_slider_release(event):
    """Отпустили ползунок — останавливаем автовоспроизведение."""
    from ui.gcode_viz import viz_stop
    if cfg.viz_playing:
        viz_stop()
    cfg.viz_play_index = int(cfg.get_widget("viz_slider").get())
    cfg.get_widget("viz_pos_label").config(text=f"{cfg.viz_play_index} / {len(cfg.viz_gcode_lines)}")
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
    status = "Про (база инструментов)" if mode == "pro" else "Простой"
    cfg.get_widget("status_label").config(text=f"Режим: {status}")


def _show_tool_db():
    """Показать диалог базы инструментов."""
    from ui.tool_db_dialog import show_tool_db_dialog
    show_tool_db_dialog(cfg.get_widget("root"), mode_engine.tool_db)
