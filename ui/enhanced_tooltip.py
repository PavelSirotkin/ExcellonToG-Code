"""
Улучшенные всплывающие подсказки для элементов интерфейса.

Тексты подсказок локализованы — берутся через `core.i18n.t()` в момент показа.
"""
import tkinter as tk
from core.i18n import t
import core.config as cfg


# Список всех известных подсказок. Используется для проверки наличия ключа
# (раньше код делал `if key in TOOLTIPS:` — теперь это `is_tooltip_key()`).
_TOOLTIP_KEYS = frozenset({
    "btn_open_excellon",
    "btn_open_slots",
    "btn_open_gerber",
    "entry_safe_z",
    "entry_drill_z",
    "entry_feed_rate",
    "entry_mill_feed",
    "entry_rapid_rate",
    "entry_park_z",
    "mode_toggle",
    "btn_gen_drilling",
    "btn_gen_milling",
    "btn_gen_combined",
    "btn_gen_outline",
    "btn_visualize",
    "btn_statistics",
    "btn_help",
    "entry_outline_tool_diameter",
    "entry_outline_depth_per_pass",
    "entry_outline_n_tabs",
    "entry_outline_tab_width",
    "entry_outline_tab_height",
    "combo_outline_direction",
    "canvas",
})


class _TooltipsProxy:
    """Прокси к локализованным подсказкам.

    Позволяет писать `TOOLTIPS["btn_open_excellon"]` и `if key in TOOLTIPS`,
    но за сценой — каждый запрос идёт через i18n, поэтому смена языка
    мгновенно отражается в новых показах подсказок.
    """

    def __getitem__(self, key: str) -> str:
        return t(f"tt.{key}")

    def __contains__(self, key: str) -> bool:
        return key in _TOOLTIP_KEYS

    def get(self, key: str, default: str = "") -> str:
        if key in _TOOLTIP_KEYS:
            return t(f"tt.{key}")
        return default


TOOLTIPS = _TooltipsProxy()


class EnhancedTooltip:
    """Улучшенная всплывающая подсказка с задержкой и форматированием."""

    def __init__(self, widget, text, delay=500):
        """
        Args:
            widget: Виджет, к которому привязывается подсказка.
            text: Либо готовый текст, либо callable, возвращающий текст
                  (для динамической локализации). Также можно передать
                  результат TOOLTIPS["..."] — он уже свежий на момент чтения.
            delay: Задержка перед показом в миллисекундах.
        """
        self.widget = widget
        self._text_provider = text
        self.delay = delay
        self.tooltip_window = None
        self.show_timer = None

        self.widget.bind("<Enter>", self._on_enter)
        self.widget.bind("<Leave>", self._on_leave)
        self.widget.bind("<Button>", self._on_leave)
        # Иначе при пересоздании виджета (смена темы/языка) запланированный
        # `after()` сработает на уже уничтоженном виджете и упадёт TclError.
        self.widget.bind("<Destroy>", self._on_destroy, add="+")

    def _on_destroy(self, event=None):
        if event is not None and event.widget is not self.widget:
            return
        self._cancel_timer()
        self._hide_tooltip()

    @property
    def text(self) -> str:
        """Текущий текст подсказки (резолвится при каждом показе)."""
        if callable(self._text_provider):
            return self._text_provider()
        return self._text_provider

    def _on_enter(self, event=None):
        self._cancel_timer()
        self.show_timer = self.widget.after(self.delay, self._show_tooltip)

    def _on_leave(self, event=None):
        self._cancel_timer()
        self._hide_tooltip()

    def _cancel_timer(self):
        if self.show_timer:
            self.widget.after_cancel(self.show_timer)
            self.show_timer = None

    def _show_tooltip(self):
        """Показать подсказку."""
        text = self.text
        if self.tooltip_window or not text:
            return

        x = self.widget.winfo_rootx() + 20
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 5

        self.tooltip_window = tk.Toplevel(self.widget)
        self.tooltip_window.wm_overrideredirect(True)
        self.tooltip_window.wm_geometry(f"+{x}+{y}")

        frame = tk.Frame(self.tooltip_window,
                         background=cfg.get_color("tooltip_bg"),
                         relief="solid",
                         borderwidth=1)
        frame.pack()

        label = tk.Label(frame,
                         text=text,
                         background=cfg.get_color("tooltip_bg"),
                         foreground=cfg.get_color("tooltip_fg"),
                         font=("Arial", 9),
                         justify="left",
                         padx=8,
                         pady=6)
        label.pack()

        hint = tk.Label(frame,
                        text=t("tooltip.f1_hint"),
                        background=cfg.get_color("tooltip_bg"),
                        foreground=cfg.get_color("tooltip_hint_fg"),
                        font=("Arial", 8, "italic"),
                        padx=8,
                        pady=2)
        hint.pack()

    def _hide_tooltip(self):
        if self.tooltip_window:
            self.tooltip_window.destroy()
            self.tooltip_window = None
