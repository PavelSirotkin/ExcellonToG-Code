"""
Глобальное состояние и константы приложения ExcellonToG-Code.
"""

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
# Глобальное состояние — интерактивная легенда
# ==========================================================
hovered_tool = None   # (tool_key, tool_type) или None
solo_tool = None      # (tool_key, tool_type) или None

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
    """Получить числовое значение параметра G-code."""
    param_map = {
        "safe_z": "safe_z_entry",
        "drill_z": "drill_z_entry",
        "feed_rate": "feed_rate_entry",
        "mill_feed": "mill_feed_entry",
        "rapid_rate": "rapid_rate_entry",
        "park_z": "park_z_entry",
    }
    entry = widgets.get(param_map[name])
    if entry is None:
        raise ValueError(f"Виджет параметра '{name}' не найден")
    return float(entry.get())
