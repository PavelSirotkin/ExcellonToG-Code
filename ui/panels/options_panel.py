"""
Панель опций (режим, база инструментов, визуализация, статистика, справка).
"""
import tkinter as tk
from core.i18n import t
import core.config as cfg
from ui.enhanced_tooltip import EnhancedTooltip


def create_options_panel(parent, context, localize_widget, handlers):
    """Создать панель опций.
    
    Args:
        parent: Родительский виджет
        context: Контекст приложения
        localize_widget: Функция локализации виджетов
        handlers: Словарь с обработчиками событий
    
    Returns:
        LabelFrame с панелью опций
    """
    options_frame = tk.LabelFrame(parent, padx=5, pady=5)
    localize_widget(options_frame, "app.frame.options")
    options_frame.pack(fill="both", expand=True, padx=5, pady=2)
    cfg.register_themed_widget(options_frame, bg="panel_bg", fg="panel_fg")

    # Верхняя часть: Режим и База
    top_frame = tk.Frame(options_frame)
    top_frame.pack(fill="x", pady=2)
    cfg.register_themed_widget(top_frame, bg="panel_bg")

    # Переключатель режимов
    from ui.mode_toggle import ModeToggle
    mode_toggle = ModeToggle(top_frame, context.mode_engine, on_mode_change=handlers['on_mode_change'])
    mode_toggle.pack(fill="x", pady=2)
    cfg.set_widget("mode_toggle", mode_toggle)

    # Кнопка базы инструментов (всегда видна, disabled в simple)
    btn_tool_db = tk.Button(top_frame,
                             command=handlers['show_tool_db'],
                             state="normal" if context.mode_engine.is_pro else "disabled")
    localize_widget(btn_tool_db, "app.btn.tool_db")
    btn_tool_db.pack(fill="x", pady=2)
    cfg.set_widget("btn_tool_db", btn_tool_db)
    cfg.register_themed_widget(btn_tool_db, bg="btn_bg", fg="btn_fg")

    # Нижняя часть: Визуализация, Статистика, Справка
    bottom_frame = tk.Frame(options_frame)
    bottom_frame.pack(fill="x", side="bottom", pady=2)
    cfg.register_themed_widget(bottom_frame, bg="panel_bg")

    # Кнопка визуализации
    btn_visualize = tk.Button(bottom_frame,
                              command=handlers['toggle_viz_mode'], state="disabled",
                              font=("Arial", 9, "bold"))
    localize_widget(btn_visualize, "app.btn.visualize")
    btn_visualize.pack(fill="x", pady=2)
    EnhancedTooltip(btn_visualize, lambda: t("tt.btn_visualize"))
    cfg.set_widget("btn_visualize", btn_visualize)
    cfg.register_themed_widget(btn_visualize, bg="btn_bg", fg="btn_fg")

    # Статистика и справка
    btn_stats = tk.Button(bottom_frame, command=handlers['show_statistics'])
    localize_widget(btn_stats, "app.btn.statistics")
    btn_stats.pack(fill="x", pady=1)
    EnhancedTooltip(btn_stats, lambda: t("tt.btn_statistics"))
    cfg.register_themed_widget(btn_stats, bg="btn_bg", fg="btn_fg")
    
    btn_help = tk.Button(bottom_frame, command=handlers['open_help'])
    localize_widget(btn_help, "app.btn.help")
    btn_help.pack(fill="x", pady=1)
    EnhancedTooltip(btn_help, lambda: t("tt.btn_help"))
    cfg.register_themed_widget(btn_help, bg="btn_bg", fg="btn_fg")

    return options_frame
