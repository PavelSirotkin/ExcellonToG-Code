"""
Тематические messagebox с поддержкой темной темы.
"""
import tkinter as tk
from tkinter import messagebox
import core.config as cfg
from core.i18n import t


def _create_themed_dialog(parent, title, message, dialog_type="info", buttons="ok"):
    """
    Создать кастомный диалог с поддержкой темы.
    
    Args:
        parent: родительское окно
        title: заголовок диалога
        message: текст сообщения
        dialog_type: тип диалога ("info", "warning", "error")
        buttons: тип кнопок ("ok", "yesno", "okcancel", "yesnocancel", "retrycancel")
    
    Returns:
        True/False для yes/no диалогов, None для info диалогов
    """
    result = [None]  # Используем список для изменяемости в замыкании
    
    # Создаем диалоговое окно
    dialog = tk.Toplevel(parent)
    dialog.title(title)
    dialog.resizable(False, False)
    dialog.transient(parent)
    dialog.grab_set()
    
    # Применяем тему
    cfg.register_themed_widget(dialog, bg="panel_bg")
    
    # Иконка в зависимости от типа
    icon_symbols = {
        "info": "ℹ",
        "warning": "⚠",
        "error": "✖"
    }
    icon_colors = {
        "info": "#3498DB",
        "warning": "#F39C12",
        "error": "#E74C3C"
    }
    
    # Фрейм содержимого
    content_frame = tk.Frame(dialog)
    cfg.register_themed_widget(content_frame, bg="panel_bg")
    content_frame.pack(fill="both", expand=True, padx=20, pady=20)
    
    # Иконка
    icon_label = tk.Label(content_frame, text=icon_symbols.get(dialog_type, "ℹ"),
                          font=("Arial", 32), fg=icon_colors.get(dialog_type, "#3498DB"))
    cfg.register_themed_widget(icon_label, bg="panel_bg")
    icon_label.pack(side="left", padx=(0, 15))
    
    # Сообщение
    msg_label = tk.Label(content_frame, text=message, justify="left", wraplength=350)
    cfg.register_themed_widget(msg_label, bg="panel_bg", fg="panel_fg")
    msg_label.pack(side="left", fill="both", expand=True)
    
    # Фрейм кнопок
    btn_frame = tk.Frame(dialog)
    cfg.register_themed_widget(btn_frame, bg="panel_bg")
    btn_frame.pack(fill="x", padx=20, pady=(0, 20))
    
    def on_close(value=None):
        result[0] = value
        dialog.destroy()
    
    # Создаем кнопки в зависимости от типа
    if buttons == "ok":
        btn = tk.Button(btn_frame, text=t("app.dlg.ok"), command=lambda: on_close(True), width=10)
        cfg.register_themed_widget(btn, bg="btn_bg", fg="btn_fg")
        btn.pack(side="right", padx=5)
        dialog.bind("<Return>", lambda e: on_close(True))
        dialog.bind("<Escape>", lambda e: on_close(True))
    elif buttons == "yesno":
        btn_no = tk.Button(btn_frame, text=t("app.dlg.no"), command=lambda: on_close(False), width=10)
        cfg.register_themed_widget(btn_no, bg="btn_bg", fg="btn_fg")
        btn_no.pack(side="right", padx=5)

        btn_yes = tk.Button(btn_frame, text=t("app.dlg.yes"), command=lambda: on_close(True), width=10)
        cfg.register_themed_widget(btn_yes, bg="btn_bg", fg="btn_fg")
        btn_yes.pack(side="right", padx=5)
        dialog.bind("<Return>", lambda e: on_close(True))
        dialog.bind("<Escape>", lambda e: on_close(False))
    elif buttons == "okcancel":
        btn_cancel = tk.Button(btn_frame, text=t("app.dlg.cancel"), command=lambda: on_close(False), width=10)
        cfg.register_themed_widget(btn_cancel, bg="btn_bg", fg="btn_fg")
        btn_cancel.pack(side="right", padx=5)

        btn_ok = tk.Button(btn_frame, text=t("app.dlg.ok"), command=lambda: on_close(True), width=10)
        cfg.register_themed_widget(btn_ok, bg="btn_bg", fg="btn_fg")
        btn_ok.pack(side="right", padx=5)
        dialog.bind("<Return>", lambda e: on_close(True))
        dialog.bind("<Escape>", lambda e: on_close(False))
    elif buttons == "yesnocancel":
        btn_cancel = tk.Button(btn_frame, text=t("app.dlg.cancel"), command=lambda: on_close(None), width=10)
        cfg.register_themed_widget(btn_cancel, bg="btn_bg", fg="btn_fg")
        btn_cancel.pack(side="right", padx=5)

        btn_no = tk.Button(btn_frame, text=t("app.dlg.no"), command=lambda: on_close(False), width=10)
        cfg.register_themed_widget(btn_no, bg="btn_bg", fg="btn_fg")
        btn_no.pack(side="right", padx=5)

        btn_yes = tk.Button(btn_frame, text=t("app.dlg.yes"), command=lambda: on_close(True), width=10)
        cfg.register_themed_widget(btn_yes, bg="btn_bg", fg="btn_fg")
        btn_yes.pack(side="right", padx=5)
        dialog.bind("<Return>", lambda e: on_close(True))
        dialog.bind("<Escape>", lambda e: on_close(None))
    elif buttons == "retrycancel":
        btn_cancel = tk.Button(btn_frame, text=t("app.dlg.cancel"), command=lambda: on_close(False), width=10)
        cfg.register_themed_widget(btn_cancel, bg="btn_bg", fg="btn_fg")
        btn_cancel.pack(side="right", padx=5)

        btn_retry = tk.Button(btn_frame, text=t("app.dlg.retry"), command=lambda: on_close(True), width=10)
        cfg.register_themed_widget(btn_retry, bg="btn_bg", fg="btn_fg")
        btn_retry.pack(side="right", padx=5)
        dialog.bind("<Return>", lambda e: on_close(True))
        dialog.bind("<Escape>", lambda e: on_close(False))
    
    # Центрирование на родителе
    dialog.update_idletasks()
    if parent:
        px = parent.winfo_rootx()
        py = parent.winfo_rooty()
        pw = parent.winfo_width()
        ph = parent.winfo_height()
        dw = dialog.winfo_width()
        dh = dialog.winfo_height()
        dialog.geometry(f"+{px + (pw - dw) // 2}+{py + (ph - dh) // 2}")
    
    # Применяем тему к заголовку окна
    cfg.apply_window_theme(dialog)
    
    # Ждем закрытия диалога
    dialog.wait_window()
    
    return result[0]


def showinfo(title, message, **options):
    """Показать информационное сообщение с поддержкой темы."""
    parent = options.get('parent') or cfg.get_widget("root")
    _create_themed_dialog(parent, title, message, "info", "ok")


def showwarning(title, message, **options):
    """Показать предупреждение с поддержкой темы."""
    parent = options.get('parent') or cfg.get_widget("root")
    _create_themed_dialog(parent, title, message, "warning", "ok")


def showerror(title, message, **options):
    """Показать ошибку с поддержкой темы."""
    parent = options.get('parent') or cfg.get_widget("root")
    _create_themed_dialog(parent, title, message, "error", "ok")


def askyesno(title, message, **options):
    """Показать диалог да/нет с поддержкой темы."""
    parent = options.get('parent') or cfg.get_widget("root")
    return _create_themed_dialog(parent, title, message, "info", "yesno")


def askokcancel(title, message, **options):
    """Показать диалог OK/Отмена с поддержкой темы."""
    parent = options.get('parent') or cfg.get_widget("root")
    return _create_themed_dialog(parent, title, message, "info", "okcancel")


def askretrycancel(title, message, **options):
    """Показать диалог Повтор/Отмена с поддержкой темы."""
    parent = options.get('parent') or cfg.get_widget("root")
    return _create_themed_dialog(parent, title, message, "warning", "retrycancel")


def askyesnocancel(title, message, **options):
    """Показать диалог да/нет/отмена с поддержкой темы."""
    parent = options.get('parent') or cfg.get_widget("root")
    return _create_themed_dialog(parent, title, message, "info", "yesnocancel")
