"""
Вспомогательные диалоги: результат, статистика, помощь.
"""
import os
import math
import tkinter as tk
from tkinter import messagebox
from core.i18n import t
import core.config as cfg


def show_result_dialog(filename):
    """Диалог подтверждения сохранения G-code."""
    dlg = tk.Toplevel(cfg.get_widget("root"))
    dlg.title(t("app.dlg.save.title"))
    dlg.resizable(False, False)
    dlg.transient(cfg.get_widget("root"))
    dlg.grab_set()
    
    # Применить тему к окну
    cfg.register_themed_widget(dlg, bg="panel_bg")

    frm = tk.Frame(dlg, padx=20, pady=15)
    cfg.register_themed_widget(frm, bg="panel_bg")
    frm.pack()

    lbl_msg = tk.Label(frm, text=t("app.dlg.save.msg"), font=("Arial", 10))
    cfg.register_themed_widget(lbl_msg, bg="panel_bg", fg="panel_fg")
    lbl_msg.pack(pady=(0, 5))
    
    lbl_file = tk.Label(frm, text=os.path.basename(filename), font=("Arial", 10, "bold"))
    cfg.register_themed_widget(lbl_file, bg="panel_bg", fg="accent_success")
    lbl_file.pack()

    lbl_hint = tk.Label(frm, text=t("app.dlg.save.hint"), font=("Arial", 9))
    cfg.register_themed_widget(lbl_hint, bg="panel_bg", fg="text_muted")
    lbl_hint.pack(pady=(8, 0))

    btn_ok = tk.Button(frm, text=t("app.dlg.ok"), width=12, command=dlg.destroy)
    cfg.register_themed_widget(btn_ok, bg="btn_bg", fg="btn_fg")
    btn_ok.pack(pady=(10, 0))

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
    
    # Применить тему к заголовку окна после создания всех виджетов
    cfg.apply_window_theme(dlg)


def show_statistics():
    """Расчёт и показ статистики."""
    from ui.statistics_window import show_statistics_window
    show_statistics_window(cfg.get_widget("root"))


def open_help():
    """Справочное окно."""
    from ui.help_window import open_help_window
    open_help_window(cfg.get_widget("root"))
