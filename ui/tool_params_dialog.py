"""
Диалог ввода параметров инструмента (для "Про" режима).
Показывается когда инструмент не найден в базе.
"""
import tkinter as tk
from tkinter import ttk


def show_tool_params_dialog(parent, tool_type: str, diameter: float,
                            defaults: dict = None) -> dict:
    """
    Показать диалог ввода параметров инструмента.
    Центрируется на parent.
    """
    result = {}

    dlg = tk.Toplevel(parent)
    dlg.title(f"Параметры инструмента D={diameter:.2f}мм")
    dlg.resizable(False, False)
    dlg.transient(parent)
    dlg.grab_set()
    dlg.protocol("WM_DELETE_WINDOW", lambda: None)

    # Центрирование на parent
    dlg.update_idletasks()
    px = parent.winfo_rootx()
    py = parent.winfo_rooty()
    pw = parent.winfo_width()
    ph = parent.winfo_height()
    dw = 350
    dh = 280 if tool_type == "drill" else 280
    dlg.geometry(f"+{px + (pw - dw) // 2}+{py + (ph - dh) // 2}")

    frm = ttk.Frame(dlg, padding=15)
    frm.pack(fill="x")

    type_name = "Сверло" if tool_type == "drill" else "Фреза"
    ttk.Label(frm, text=f"{type_name} D={diameter:.2f}мм — не найдено в базе",
              font=("Arial", 10, "bold")).pack(pady=(0, 10))

    entries = {}
    row = 0

    def add_field(label_text, default, row_ref):
        r = tk.Frame(frm)
        r.pack(fill="x", pady=2)
        tk.Label(r, text=label_text, width=24, anchor="w").pack(side="left")
        e = tk.Entry(r, width=10)
        e.insert(0, str(default if default is not None else ""))
        e.pack(side="right")
        entries[label_text] = e
        return row_ref + 1

    if tool_type == "drill":
        add_field("Обороты шпинделя (RPM):", defaults.get("spindle_speed", 10000) if defaults else 10000, row)
        row += 1
        add_field("Подача погружения (мм/мин):", defaults.get("feed_rate", 100) if defaults else 100, row)
        row += 1
        add_field("Подача подъёма (мм/мин):", defaults.get("rapid_rate", 500) if defaults else 500, row)
        row += 1
    else:
        add_field("Обороты шпинделя (RPM):", defaults.get("spindle_speed", 15000) if defaults else 15000, row)
        row += 1
        add_field("Скорость реза XY (мм/мин):", defaults.get("mill_feed", 50) if defaults else 50, row)
        row += 1

    add_to_db_var = tk.BooleanVar(value=False)
    chk_frame = tk.Frame(frm)
    chk_frame.pack(fill="x", pady=(10, 5))
    ttk.Checkbutton(chk_frame, text="Добавить в базу инструментов",
                     variable=add_to_db_var).pack(anchor="w")

    btn_frame = tk.Frame(frm)
    btn_frame.pack(fill="x", pady=(10, 0))

    def on_ok():
        try:
            vals = {}
            for label, entry in entries.items():
                raw = entry.get().strip()
                if not raw:
                    raise ValueError(f"Поле '{label}' не заполнено")
                vals[label] = float(raw)

            if tool_type == "drill":
                result["spindle_speed"] = int(vals.get("Обороты шпинделя (RPM):", 10000))
                result["feed_rate"] = vals["Подача погружения (мм/мин):"]
                result["rapid_rate"] = vals["Подача подъёма (мм/мин):"]
            else:
                result["spindle_speed"] = int(vals.get("Обороты шпинделя (RPM):", 15000))
                result["mill_feed"] = vals["Скорость реза XY (мм/мин):"]

            result["add_to_db"] = add_to_db_var.get()
            result["diameter"] = diameter
            result["tool_type"] = tool_type
            dlg.destroy()
        except ValueError as e:
            from tkinter import messagebox
            messagebox.showerror("Ошибка", str(e), parent=dlg)

    ttk.Button(btn_frame, text="OK", command=on_ok, width=10).pack(side="left", padx=5)
    ttk.Button(btn_frame, text="Отмена", command=dlg.destroy, width=10).pack(side="left", padx=5)

    dlg.wait_window()
    return result if result else None
