"""
Глобальное состояние и константы приложения ExcellonToG-Code.
"""
import logging

logger = logging.getLogger(__name__)

# ==========================================================
# Тёмная тема — палитры
# ==========================================================
THEME_LIGHT = {
    # Фоны
    "bg": "#F0F0F0",            # общий фон
    "panel_bg": "#F0F0F0",       # фон LabelFrame, Frame
    "panel_fg": "#000000",
    "btn_bg": "#E0E0E0",         # обычные кнопки
    "btn_fg": "#000000",
    "entry_bg": "#FFFFFF",        # Entry, Text
    "entry_fg": "#000000",
    "canvas_bg": "#F0F0F0",       # фон canvas
    "workarea_bg": "#FFFFFF",     # рабочая область платы
    "ruler_fg": "#000000",        # деления линеек
    "grid_fg": "lightgray",
    # Сущности на canvas
    "hole": "red",                # отверстия по умолчанию (если не выбран color из HOLE_COLORS)
    "slot_path": "#444444",
    "outline_path": "#444444",
    "violation": "red",
    "selected_outline": "white",
    # Статус
    "text_status": "#666666",
    "text_muted": "#7F8C8D",
    # Подсветка легенды
    "highlight_hover": "#D0E8FF",
    "highlight_solo": "#C8F0C8",
    "highlight_inactive": "#F0F0F0",
    "highlight_selected": "#FFE08A",
    # Tooltip
    "tooltip_bg": "#FFFACD",
    "tooltip_fg": "#000000",
    "tooltip_hint_fg": "#666666",
    # Кнопки генерации (зелёная/синяя/оранжевая/жёлтая)
    "btn_gen_drilling": "#90EE90",
    "btn_gen_milling": "#87CEEB",
    "btn_gen_outline": "#FFA07A",
    "btn_gen_combined": "#FFD700",
    # Mode toggle
    "mode_simple_bg": "#90EE90",
    "mode_pro_bg": "#87CEEB",
    # Stats окно
    "stats_bg": "#F5F5F5",
    "stats_header_bg": "#2C3E50",
    "stats_header_fg": "white",
    "stats_table_header_bg": "#34495E",
    "stats_row_even": "#ECF0F1",
    "stats_row_odd": "white",
    "stats_summary_holes": "#27AE60",
    "stats_summary_slots": "#E74C3C",
    "stats_summary_outline": "#3498DB",
    "stats_progress_bg": "#E0E0E0",
    # Акценты
    "accent_success": "#0a7a0a",
}

THEME_DARK = {
    "bg": "#1E1E1E",
    "panel_bg": "#252526",
    "panel_fg": "#E0E0E0",
    "btn_bg": "#3D3D3D",
    "btn_fg": "#E0E0E0",
    "entry_bg": "#2D2D2D",
    "entry_fg": "#E0E0E0",
    "canvas_bg": "#1A1A1A",
    "workarea_bg": "#252526",
    "ruler_fg": "#C0C0C0",
    "grid_fg": "#3A3A3A",
    "hole": "#FF6060",
    "slot_path": "#888888",
    "outline_path": "#888888",
    "violation": "#FF6060",
    "selected_outline": "#E0E0E0",
    "text_status": "#A0A0A0",
    "text_muted": "#7F8C8D",
    "highlight_hover": "#264F78",
    "highlight_solo": "#2D5A2D",
    "highlight_inactive": "#2A2A2A",
    "highlight_selected": "#7A5C20",
    "tooltip_bg": "#3F3F1F",
    "tooltip_fg": "#E0E0E0",
    "tooltip_hint_fg": "#A0A0A0",
    "btn_gen_drilling": "#3A7A3A",
    "btn_gen_milling": "#3D6F95",
    "btn_gen_outline": "#7A4030",
    "btn_gen_combined": "#807030",
    "mode_simple_bg": "#3A7A3A",
    "mode_pro_bg": "#3D6F95",
    "stats_bg": "#252526",
    "stats_header_bg": "#3D3D3D",
    "stats_header_fg": "#E0E0E0",
    "stats_table_header_bg": "#3D3D3D",
    "stats_row_even": "#2D2D2D",
    "stats_row_odd": "#252526",
    "stats_summary_holes": "#3A7A3A",
    "stats_summary_slots": "#A04040",
    "stats_summary_outline": "#3D6F95",
    "stats_progress_bg": "#3D3D3D",
    "accent_success": "#5FD05F",
}

_THEMES = {"light": THEME_LIGHT, "dark": THEME_DARK}
_current_theme_name = "light"
_themed_widgets = []  # [(widget, role_dict)] — для обхода при смене темы
_theme_listeners = []


def get_color(role: str) -> str:
    """Получить цвет по семантической роли в текущей теме."""
    return _THEMES[_current_theme_name].get(role, "#FF00FF")  # magenta — индикатор пропуска


def current_theme() -> str:
    return _current_theme_name


def register_themed_widget(widget, **role_map) -> None:
    """Запомнить виджет с маппингом аргументов config → роль палитры.

    Пример:
        register_themed_widget(my_button, bg="btn_bg", fg="btn_fg")
        # При apply_theme() вызовет: my_button.config(bg=get_color("btn_bg"), fg=get_color("btn_fg"))
    """
    if not role_map:
        return
    _themed_widgets.append((widget, dict(role_map)))
    # Сразу применить
    _apply_to_widget(widget, role_map)


def unregister_themed_widget(widget) -> None:
    """Удалить виджет из реестра тем перед его уничтожением.
    
    Предотвращает утечку памяти при многократном пересоздании виджетов.
    """
    global _themed_widgets
    _themed_widgets = [(w, role_map) for w, role_map in _themed_widgets if w is not widget]


def _apply_to_widget(widget, role_map):
    try:
        kwargs = {k: get_color(role) for k, role in role_map.items()}
        widget.config(**kwargs)
    except Exception as e:
        # Виджет уничтожен или не поддерживает опцию — пропускаем
        logger.debug("Failed to apply theme to widget: %s", e)


def register_theme_listener(callback) -> None:
    if callback not in _theme_listeners:
        _theme_listeners.append(callback)


def unregister_theme_listener(callback) -> None:
    if callback in _theme_listeners:
        _theme_listeners.remove(callback)


def apply_theme(name: str) -> None:
    """Применить тему ко всем зарегистрированным виджетам и ttk-стилям."""
    global _current_theme_name
    if name not in _THEMES:
        name = "light"
    _current_theme_name = name

    # Проход по плоским виджетам
    for widget, role_map in list(_themed_widgets):
        _apply_to_widget(widget, role_map)

    # Уведомить листенеров — они занимаются ttk-стилями, canvas-перерисовкой и т.п.
    for cb in list(_theme_listeners):
        try:
            cb()
        except Exception as e:
            logger.exception("Theme listener callback failed: %s", e)


def apply_window_theme(window) -> None:
    """Применить темную тему к заголовку окна (Windows-only).
    
    Использует Windows DWM API для применения тёмной темы к рамке окна.
    На Linux/macOS функция является no-op (не выполняет никаких действий).
    
    Args:
        window: Tk или Toplevel окно
    
    Note:
        Windows-only; на других платформах молча игнорируется.
    """
    try:
        import ctypes
        if _current_theme_name == "dark":
            # DWMWA_USE_IMMERSIVE_DARK_MODE = 20
            ctypes.windll.dwmapi.DwmSetWindowAttribute(
                ctypes.windll.user32.GetParent(window.winfo_id()),
                20,
                ctypes.byref(ctypes.c_int(1)),
                ctypes.sizeof(ctypes.c_int)
            )
        else:
            # Сбросить на светлую тему
            ctypes.windll.dwmapi.DwmSetWindowAttribute(
                ctypes.windll.user32.GetParent(window.winfo_id()),
                20,
                ctypes.byref(ctypes.c_int(0)),
                ctypes.sizeof(ctypes.c_int)
            )
    except Exception as e:
        # Не критично, если не получилось (не Windows или старая версия)
        logger.debug("Failed to apply window theme: %s", e)


# ==========================================================
# Константы отображения
# ==========================================================
CANVAS_WIDTH = 980
CANVAS_HEIGHT = 620
WORKAREA_WIDTH = 900
WORKAREA_HEIGHT = 560
WORKAREA_OFFSET_X = 60
WORKAREA_OFFSET_Y = 10
X_MIN, X_MAX = -300, 300
Y_MIN, Y_MAX = -200, 200
MIN_SCALE = 1.5
BACKGROUND_PAD = 500  # Дополнительный размер фона canvas за пределы рабочей области
EXCELLON_HEADER_LINES = 10  # Сколько строк проверять на заголовок Excellon

# Цвета для отображения инструментов
HOLE_COLORS = ['red', 'green', 'blue', 'orange', 'purple', 'cyan', 'magenta', 'yellow']
SLOT_COLORS = ['#FF69B4', '#00CED1', '#FFD700', '#8B4513', '#DC143C', '#00FF7F']

# ==========================================================
# Режимы работы
# ==========================================================
app_mode = "simple"  # "simple" | "pro"
tool_db_path = None  # Путь к файлу базы инструментов

# ==========================================================
# Глобальное состояние — навигация
# ==========================================================
offset_x = 0
offset_y = 0
scale_factor = 1.5
drag_start_real_x = 0
drag_start_real_y = 0
initial_offset_x = 0
initial_offset_y = 0

# ==========================================================
# Глобальное состояние — данные
# ==========================================================
current_tools = None
coordinate_format = "4.2"
current_filename = None
show_paths_var = None
slot_tools = None
slot_filename = None

# ==========================================================
# Глобальное состояние — контур платы (Gerber outline)
# ==========================================================
board_outline = None          # List[segment]
board_outline_filename = None
board_outline_unit = "mm"
board_outline_visible = True  # Видимость контура на canvas (управляется через легенду)
outline_violations = []       # список (x, y) нарушающих точек

# ==========================================================
# Глобальное состояние — интерактивная легенда
# ==========================================================
hovered_tool = None   # (tool_key, tool_type) или None
solo_tool = None      # (tool_key, tool_type) или None

# Множественный выбор drill-инструментов в легенде (Ctrl/Shift + ЛКМ) для
# операции «Объединить». Содержит ключи (tool_key) выделенных инструментов
# из cfg.current_tools. Сбрасывается при загрузке/перепарсе файла.
selected_tools = set()

# Снимок cfg.current_tools, сделанный сразу после первичного парсинга файла.
# Нужен для отката операции «Объединить» (см. ui.legend.legend_unmerge_all
# и legend.legend_unmerge_selected). None означает, что снимок ещё не сделан.
original_current_tools = None

# История объединений: для каждого ТЕКУЩЕГО инструмента, который является
# результатом merge, хранится множество ОРИГИНАЛЬНЫХ ключей, которые в него
# вошли. Используется для частичного отката «Разъединить выделенные».
# Формат: {current_key: set(original_keys)}.
# Очищается при каждом перепарсе и при «Разъединить все».
merge_groups = {}

# ==========================================================
# Глобальное состояние — визуализатор G-code
# ==========================================================
viz_mode = False           # True = режим визуализации
viz_gcode_lines = []       # Распарсенные сегменты G-code
viz_play_index = 0         # Текущая позиция плеера
viz_playing = False        # Анимация запущена
viz_after_id = None        # ID after()-таймера
viz_sf = 1.0               # Масштаб визуализатора (свой, независимый)
viz_ox = 0.0               # Смещение X визуализатора (мм)
viz_oy = 0.0               # Смещение Y визуализатора (мм)

# ==========================================================
# Глобальное состояние — всплывающая подсказка
# ==========================================================
_tooltip_window = None     # Текущее окно tooltip

# ==========================================================
# Глобальное состояние — UI элементы (заполняется в main)
# ==========================================================
# Допустимые ключи реестра виджетов — опечатка поймается сразу, а не тихим None
_WIDGET_KEYS: frozenset = frozenset({
    # Файлы
    "holes_file_label", "slot_file_label", "format_combobox",
    "status_label", "coord_label",
    # Параметры G-code
    "safe_z_entry", "drill_z_entry", "feed_rate_entry",
    "mill_feed_entry", "rapid_rate_entry", "park_z_entry",
    "spindle_speed_entry", "spindle_speed_row",
    # Отображение
    "show_paths_var",
    # Кнопки
    "btn_visualize", "btn_tool_db", "mode_toggle",
    # Визуализатор
    "viz_slider", "viz_speed_var", "viz_pos_label",
    "viz_btn_play", "viz_player_frame",
    # Легенда
    "legend_frame", "legend_canvas",
    # Canvas / корневой виджет
    "canvas", "root",
    # Контур платы (Gerber outline)
    "outline_file_label",
    "outline_tool_diameter_entry",
    "outline_depth_per_pass_entry",
    "outline_n_tabs_entry",
    "outline_tab_width_entry",
    "outline_tab_height_entry",
    "outline_direction_var",
})

# Ссылки на виджеты, необходимые из разных модулей
widgets: dict = {key: None for key in _WIDGET_KEYS}


def get_widget(name: str):
    """Получить виджет по имени. KeyError при неизвестном ключе."""
    if name not in _WIDGET_KEYS:
        raise KeyError(f"Неизвестный ключ виджета: '{name}'")
    return widgets[name]


def set_widget(name: str, widget) -> None:
    """Установить виджет по имени. KeyError при неизвестном ключе."""
    if name not in _WIDGET_KEYS:
        raise KeyError(f"Неизвестный ключ виджета: '{name}'")
    widgets[name] = widget


def get_param(name):
    """Получить числовое значение параметра G-code.
    Все известные пути ошибки конвертируются в ValueError с осмысленным
    сообщением: KeyError от незнакомого имени, AttributeError от не-Entry
    виджета, ValueError/TypeError от пустого/нечислового значения. Это
    позволяет вызывающему коду показывать пользователю понятное сообщение
    вместо traceback'а из глубины Tkinter."""
    param_map = {
        "safe_z": "safe_z_entry",
        "drill_z": "drill_z_entry",
        "feed_rate": "feed_rate_entry",
        "mill_feed": "mill_feed_entry",
        "rapid_rate": "rapid_rate_entry",
        "park_z": "park_z_entry",
        "spindle_speed": "spindle_speed_entry",
        "outline_tool_diameter": "outline_tool_diameter_entry",
        "outline_depth_per_pass": "outline_depth_per_pass_entry",
        "outline_n_tabs": "outline_n_tabs_entry",
        "outline_tab_width": "outline_tab_width_entry",
        "outline_tab_height": "outline_tab_height_entry",
    }
    if name not in param_map:
        raise ValueError(
            f"Неизвестный параметр '{name}'. Допустимые: {sorted(param_map)}"
        )
    entry = widgets.get(param_map[name])
    if entry is None:
        raise ValueError(f"Виджет параметра '{name}' не найден")
    try:
        return float(entry.get())
    except AttributeError as e:
        # entry существует, но это не Tkinter Entry/Spinbox/Combobox — ошибка
        # инициализации виджета (например, в widgets[<key>] положили None или
        # объект без .get()). Раньше маскировалось голым AttributeError.
        raise ValueError(
            f"Виджет параметра '{name}' инициализирован неправильно "
            f"(нет метода .get()): {e}"
        ) from e
    except (ValueError, TypeError) as e:
        # Пустая строка или нечисловое значение в поле ввода.
        raise ValueError(
            f"Не удалось разобрать значение параметра '{name}' как число: {e}"
        ) from e
