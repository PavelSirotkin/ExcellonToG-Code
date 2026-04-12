"""
Кнопка-переключатель режимов "Простой" / "Про".
"""
import tkinter as tk
from core.mode_engine import ModeEngine


class ModeToggle(tk.Frame):
    """Кнопка-тогл режимов работы."""

    def __init__(self, parent, mode_engine: ModeEngine, on_mode_change=None):
        super().__init__(parent)
        self.engine = mode_engine
        self.on_mode_change = on_mode_change

        self.btn = tk.Button(
            self, text=self._get_label(), command=self._toggle,
            bg="#87CEEB" if mode_engine.is_pro else "#90EE90",
            font=("Arial", 9, "bold"), width=16
        )
        self.btn.pack(fill="x")

    def _get_label(self) -> str:
        if self.engine.is_pro:
            return "⚙ Режим: Про"
        return "🔧 Режим: Простой"

    def _toggle(self):
        self.engine.toggle()
        self.btn.config(text=self._get_label(),
                        bg="#87CEEB" if self.engine.is_pro else "#90EE90")
        if self.on_mode_change:
            self.on_mode_change(self.engine.mode)

    def update_display(self):
        """Обновить отображение (если режим изменён извне)."""
        self.btn.config(text=self._get_label(),
                        bg="#87CEEB" if self.engine.is_pro else "#90EE90")
