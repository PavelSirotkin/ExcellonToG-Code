"""
Главное приложение UI: создание GUI, всех виджетов, привязка событий.
Рефакторенная версия с модульной структурой.
"""
import logging
import os
import sys
import tkinter as tk
from tkinter import ttk
from version import VERSION
from ui import themed_messagebox as messagebox
from core.mode_engine import ModeEngine
from core.gcode_params import GCodeParams
from core.app_settings import settings, default_settings_path
from core.i18n import t, set_language, get_language, register_listener
import core.config as cfg
from ui.enhanced_tooltip import EnhancedTooltip, TOOLTIPS

logger = logging.getLogger(__name__)


# ==========================================================
# Dependency Injection: AppContext
# ==========================================================
class AppContext:
    """Контейнер зависимостей приложения.
    
    Централизует управление основными компонентами:
    - mode_engine: движок режимов (Simple/Pro)
    - gcode_params: менеджер параметров G-code
    - tool_db: база данных инструментов (доступна через mode_engine)
    
    Преимущества:
    - Упрощает тестирование (можно подменить зависимости)
    - Явные зависимости вместо глобальных переменных
    - Единая точка инициализации компонентов
    """
    def __init__(self):
        self.mode_engine = ModeEngine()
        self.gcode_params = GCodeParams()
    
    @property
    def tool_db(self):
        """Доступ к базе инструментов через mode_engine."""
        return self.mode_engine.tool_db


# Глобальный контекст приложения (инициализируется в create_app)
_app_context: AppContext = None


def get_app_context() -> AppContext:
    """Получить текущий контекст приложения."""
    if _app_context is None:
        raise RuntimeError("AppContext not initialized. Call create_app() first.")
    return _app_context


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
            logger.exception("Language callback failed: %r", cb)
    # Обновить легенду при смене языка
    try:
        from ui.legend import update_legend
        update_legend()
    except Exception:
        logger.exception("update_legend failed during language switch")


def validate_numeric_entry(value, min_val=None, max_val=None):
    """Валидация числового ввода для Entry-виджетов.
    
    Args:
        value: Строка для валидации
        min_val: Минимальное допустимое значение (опционально)
        max_val: Максимальное допустимое значение (опционально)
    
    Returns:
        True если значение валидно, False иначе
    """
    # Пустая строка разрешена (пользователь может очищать поле)
    if value == "":
        return True
    
    # Разрешить минус в начале для отрицательных чисел
    if value == "-":
        return True
    
    try:
        num = float(value)
        if min_val is not None and num < min_val:
            return False
        if max_val is not None and num > max_val:
            return False
        return True
    except ValueError:
        return False


def _localize_widget(widget, key: str, **fmt_kwargs):
    """Установить виджету `text=t(key)` и зарегистрировать колбэк на смену языка."""
    def update():
        widget.config(text=t(key, **fmt_kwargs))
    update()
    _register_lang_update(update)
    return widget


def create_app(context: AppContext = None):
    """Создание главного окна и всех UI компонентов.
    
    Args:
        context: Контекст приложения с зависимостями. Если None, создаётся новый.
    
    Returns:
        Корневое окно Tkinter.
    """
    # Инициализация контекста приложения
    global _app_context
    if context is None:
        context = AppContext()
    _app_context = context
    
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
    root.geometry("1720x970")
    root.minsize(1540, 920)
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
    # Импорт обработчиков
    # ==========================================================
    from ui.handlers.file_handlers import (
        choose_file, choose_slot_file, choose_outline_file,
        clear_slots, clear_outline, on_format_change, on_show_paths_change
    )
    from ui.handlers.gcode_handlers import (
        generate_drilling_gcode, generate_milling_gcode,
        generate_combined_gcode, generate_outline_gcode,
        on_param_change
    )

    # Словарь обработчиков для передачи в панели
    file_handlers = {
        'choose_file': choose_file,
        'choose_slot_file': choose_slot_file,
        'choose_outline_file': choose_outline_file,
        'clear_slots': clear_slots,
        'clear_outline': clear_outline,
        'on_format_change': on_format_change,
    }

    gcode_handlers = {
        'generate_drilling_gcode': generate_drilling_gcode,
        'generate_milling_gcode': generate_milling_gcode,
        'generate_combined_gcode': generate_combined_gcode,
        'generate_outline_gcode': generate_outline_gcode,
    }

    option_handlers = {
        'on_mode_change': _on_mode_change,
        'show_tool_db': _show_tool_db,
        'toggle_viz_mode': _toggle_viz_mode,
        'show_statistics': _show_statistics,
        'open_help': _open_help,
    }

    # ==========================================================
    # Колонка 1 — «Настройки» (используем модули панелей)
    # ==========================================================
    from ui.panels.files_panel import create_files_panel
    from ui.panels.params_panel import create_gcode_params_panel, create_outline_params_panel
    from ui.panels.options_panel import create_options_panel

    # Панель файлов
    create_files_panel(col_settings, _localize_widget, file_handlers)

    # Панель параметров G-code
    create_gcode_params_panel(col_settings, root, _localize_widget, validate_numeric_entry, on_param_change)

    # Панель параметров контура
    create_outline_params_panel(col_settings, root, _localize_widget, validate_numeric_entry, on_param_change)

    # Панель опций
    create_options_panel(col_settings, context, _localize_widget, option_handlers)

    # Панель внешнего вида (язык/тема)
    _create_appearance_panel(col_settings, _localize_widget)

    # ==========================================================
    # Колонка 2 — «Работа»
    # ==========================================================
    from ui.panels.gcode_panel import create_display_panel, create_gcode_panel

    # Панель отображения
    create_display_panel(col_state, _localize_widget, on_show_paths_change)

    # Панель генерации G-code
    create_gcode_panel(col_state, _localize_widget, gcode_handlers)

    # Панель плеера визуализации (скрыта по умолчанию)
    _create_viz_player(left_frame, _localize_widget)

    # Легенда с прокруткой
    _create_legend_panel(col_state, _localize_widget)

    # ==========================================================
    # События мыши на canvas
    # ==========================================================
    _setup_canvas_events(canvas)

    # ==========================================================
    # Строка состояния
    # ==========================================================
    _create_status_bar(root, _localize_widget, _register_lang_update)

    canvas.bind("<Configure>", _on_canvas_resize)
    
    # Горячая клавиша F1 для вызова справки
    root.bind("<F1>", lambda e: _open_help())

    from ui.renderer import redraw_grid
    redraw_grid()

    # ==========================================================
    # Автозагрузка файлов базы инструментов и параметров G-code
    # ==========================================================
    _load_app_data(context)

    # Регистрация глобального слушателя смены языка
    register_listener(_apply_language_to_ui)

    # Настройка ttk-стилей для темы
    _apply_ttk_styles()
    cfg.register_theme_listener(_apply_ttk_styles)

    # Применить темную тему к заголовку окна после полной инициализации
    root.after(100, lambda: cfg.apply_window_theme(root))

    return root


def _create_appearance_panel(parent, localize_widget):
    """Создать панель внешнего вида (язык/тема)."""
    appearance_frame = tk.LabelFrame(parent, padx=5, pady=5)
    localize_widget(appearance_frame, "app.frame.appearance")
    appearance_frame.pack(fill="x", padx=5, pady=2)
    cfg.register_themed_widget(appearance_frame, bg="panel_bg", fg="panel_fg")
    
    # Язык
    lang_row = tk.Frame(appearance_frame)
    lang_row.pack(fill="x", pady=2)
    cfg.register_themed_widget(lang_row, bg="panel_bg")
    lang_lbl = tk.Label(lang_row, width=18, anchor="w")
    localize_widget(lang_lbl, "app.lbl.language")
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
    localize_widget(theme_lbl, "app.lbl.theme")
    theme_lbl.pack(side="left")
    cfg.register_themed_widget(theme_lbl, bg="panel_bg", fg="panel_fg")

    theme_var = tk.StringVar(value=cfg.current_theme())
    theme_combo = ttk.Combobox(theme_row, values=["light", "dark"], width=6,
                                textvariable=theme_var, state="readonly")
    theme_combo.pack(side="right")

    def _on_theme_change(event=None):
        new_theme = theme_var.get()
        cfg.apply_theme(new_theme)
        cfg.apply_window_theme(cfg.get_widget("root"))
        settings.set("theme", new_theme)
        settings.save()

    theme_combo.bind("<<ComboboxSelected>>", _on_theme_change)


def _create_viz_player(parent, localize_widget):
    """Создать панель плеера визуализации."""
    viz_player_frame = tk.Frame(parent, bg="#2C2C3E", pady=4)
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
    localize_widget(viz_speed_lbl, "app.lbl.speed")
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


def _create_legend_panel(parent, localize_widget):
    """Создать панель легенды с прокруткой."""
    legend_outer_frame = tk.LabelFrame(parent, padx=5, pady=5)
    localize_widget(legend_outer_frame, "app.frame.tools")
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


def _setup_canvas_events(canvas):
    """Настроить события мыши на canvas."""
    canvas.bind("<ButtonPress-1>", _start_drag)
    canvas.bind("<B1-Motion>", _during_drag)
    canvas.bind("<Double-Button-1>", _on_double_click)
    canvas.bind("<Button-3>", _on_canvas_click)
    canvas.bind("<MouseWheel>", _on_mousewheel)
    # Linux: колесо мыши приходит как <Button-4> (вверх) / <Button-5> (вниз)
    # без атрибута .delta. Подставляем delta вручную и переиспользуем event,
    # т.к. tk.Event() не принимает kwargs в конструкторе.
    canvas.bind("<Button-4>", _on_wheel_up)
    canvas.bind("<Button-5>", _on_wheel_down)
    canvas.bind("<Motion>", _on_mouse_move)

    # Сохраняем оригинальные биндинги для восстановления после viz-режима
    cfg.widgets["original_bindings"] = {
        "button_press_1": _start_drag,
        "b1_motion": _during_drag,
        "double_button_1": _on_double_click,
        "button_3": _on_canvas_click,
        "mousewheel": _on_mousewheel,
        "button_4": _on_wheel_up,
        "button_5": _on_wheel_down,
        "motion": _on_mouse_move,
    }


def _create_status_bar(root, localize_widget, register_lang_update):
    """Создать строку состояния."""
    status_frame = tk.Frame(root, bd=1, relief=tk.SUNKEN)
    status_frame.pack(side="bottom", fill="x")
    cfg.register_themed_widget(status_frame, bg="panel_bg")
    
    status_label = tk.Label(status_frame, anchor="w", font=("Arial", 9))
    def _update_status():
        status_label.config(text=t("app.status.ready"))
    _update_status()
    register_lang_update(_update_status)
    status_label.pack(side="left", padx=5)
    cfg.set_widget("status_label", status_label)
    cfg.register_themed_widget(status_label, bg="panel_bg", fg="text_status")
    
    coord_label = tk.Label(status_frame, anchor="e", font=("Arial", 9))
    def _update_coord():
        coord_label.config(text=t("app.status.coord_empty"))
    _update_coord()
    register_lang_update(_update_coord)
    coord_label.pack(side="right", padx=5)
    cfg.set_widget("coord_label", coord_label)
    cfg.register_themed_widget(coord_label, bg="panel_bg", fg="text_status")


def _load_app_data(context):
    """Загрузить данные приложения (параметры G-code и база инструментов)."""
    # Определяем директорию приложения
    if getattr(sys, 'frozen', False):
        # Запуск из .exe (PyInstaller)
        project_dir = os.path.dirname(sys.executable)
    else:
        # Запуск из исходников
        app_dir = os.path.dirname(os.path.abspath(__file__))
        project_dir = os.path.dirname(app_dir)

    # Загрузка параметров G-code
    gcode_params_file = os.path.join(project_dir, "gcode_params.json")
    context.gcode_params.path = gcode_params_file
    context.gcode_params.load()
    context.gcode_params.apply_to_ui(cfg.widgets)

    # Загрузка базы инструментов
    tool_db_file = os.path.join(project_dir, "tool_base.json")
    context.tool_db.path = tool_db_file
    context.tool_db.load(tool_db_file)


def _apply_ttk_styles():
    """Применить стили ttk для текущей темы."""
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


# ---- Обработчики событий (тонкая обёртка над модулями) ----

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


def _on_wheel_up(event):
    """Linux: <Button-4> = прокрутка вверх. Проставляем delta и переиспользуем event,
    т.к. tk.Event() не принимает kwargs и не позволяет синтезировать MouseWheel-событие."""
    event.delta = 120
    _on_mousewheel(event)


def _on_wheel_down(event):
    """Linux: <Button-5> = прокрутка вниз. Проставляем delta и переиспользуем event."""
    event.delta = -120
    _on_mousewheel(event)


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
    context = get_app_context()
    from ui.tool_db_dialog import show_tool_db_dialog
    show_tool_db_dialog(cfg.get_widget("root"), context.tool_db)
