"""
Вспомогательные диалоги: результат, статистика, помощь.
"""
import os
import math
import tkinter as tk
from tkinter import messagebox
import core.config as cfg


def show_result_dialog(filename):
    """Диалог подтверждения сохранения G-code."""
    dlg = tk.Toplevel(cfg.get_widget("root"))
    dlg.title("Готово")
    dlg.resizable(False, False)
    dlg.transient(cfg.get_widget("root"))
    dlg.grab_set()

    frm = tk.Frame(dlg, padx=20, pady=15)
    frm.pack()

    tk.Label(frm, text="G-код успешно сохранён:", font=("Arial", 10)).pack(pady=(0, 5))
    tk.Label(frm, text=os.path.basename(filename),
             font=("Arial", 10, "bold"), fg="darkgreen").pack()

    tk.Label(frm, text="Нажмите «🎬 Визуализация G-code» для просмотра.",
             font=("Arial", 9), fg="#555555").pack(pady=(8, 0))

    tk.Button(frm, text="OK", width=12, command=dlg.destroy).pack(pady=(10, 0))

    # Центрирование окна относительно главного окна
    dlg.update_idletasks()
    dlg_w = dlg.winfo_width()
    dlg_h = dlg.winfo_height()
    root_x = cfg.get_widget("root").winfo_x()
    root_y = cfg.get_widget("root").winfo_y()
    root_w = cfg.get_widget("root").winfo_width()
    root_h = cfg.get_widget("root").winfo_height()
    x = root_x + (root_w - dlg_w) // 2
    y = root_y + (root_h - dlg_h) // 2
    dlg.geometry(f"+{x}+{y}")


def show_statistics():
    """Расчёт и показ статистики."""
    from ui.statistics_window import show_statistics_window
    show_statistics_window(cfg.get_widget("root"))


def open_help():
    """Справочное окно."""
    from ui.help_window import open_help_window
    open_help_window(cfg.get_widget("root"))
