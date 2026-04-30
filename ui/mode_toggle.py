"""
Кнопка-переключатель режимов "Простой" / "Про".
"""
import tkinter as tk
from core.mode_engine import ModeEngine
from core.i18n import t, register_listener
import core.config as cfg


class ModeToggle(tk.Frame):
    """Кнопка-тогл режимов работы."""

    def __init__(self, parent, mode_engine: ModeEngine, on_mode_change=None):
        super().__init__(parent)
        self.engine = mode_engine
        self.on_mode_change = on_mode_change

        self.btn = tk.Button(
            self, text=self._get_label(), command=self._toggle,
            font=("Arial", 9, "bold"), width=16
        )
        self.btn.pack(fill="x")
        self._update_colors()
        
        # Регистрация для обновления при смене языка и темы
        register_listener(self._update_label)
        cfg.register_theme_listener(self._update_colors)

    def _get_label(self) -> str:
        if self.engine.is_pro:
            return t("app.mode.toggle.pro")
        return t("app.mode.toggle.simple")

    def _toggle(self):
        self.engine.toggle()
        self._update_colors()
        self.btn.config(text=self._get_label())
        if self.on_mode_change:
            self.on_mode_change(self.engine.mode)

    def _update_label(self):
        """Обновить текст кнопки (для смены языка)."""
        self.btn.config(text=self._get_label())
    
    def _update_colors(self):
        """Обновить цвета кнопки (для смены темы)."""
        bg_color = cfg.get_color("mode_pro_bg") if self.engine.is_pro else cfg.get_color("mode_simple_bg")
        self.btn.config(bg=bg_color, fg=cfg.get_color("btn_fg"))
    
    def update_display(self):
        """Обновить отображение (если режим изменён извне)."""
        self.btn.config(text=self._get_label())
        self._update_colors()
