"""
Диалог ввода параметров инструмента (для "Про" режима).
Показывается когда инструмент не найден в базе.
"""
import tkinter as tk
from tkinter import ttk
from ui import themed_messagebox as messagebox
from ui.numeric_entry import attach_numeric_validation
from core.i18n import t
from core.validators import parse_decimal
import core.config as cfg


def _unregister_widget_recursive(widget):
    """Рекурсивно отменить регистрацию виджета и всех его дочерних виджетов."""
    # Сначала обработать дочерние виджеты
    for child in widget.winfo_children():
        _unregister_widget_recursive(child)
    # Затем отменить регистрацию самого виджета
    cfg.unregister_themed_widget(widget)


def show_tool_params_dialog(parent, tool_type: str, diameter: float,
                            defaults: dict = None) -> dict:
    """
    Показать диалог ввода параметров инструмента.
    Центрируется на parent.
    """
    result = {}

    dlg = tk.Toplevel(parent)
    dlg.title(t("tool_params.title", diameter=f"{diameter:.2f}"))
    dlg.resizable(False, False)
    dlg.transient(parent)
    dlg.grab_set()
    dlg.protocol("WM_DELETE_WINDOW", lambda: None)
    
    # Применить тему к окну
    cfg.register_themed_widget(dlg, bg="panel_bg")
    cfg.apply_window_theme(dlg)

    # Центрирование на parent
    dlg.update_idletasks()
    px = parent.winfo_rootx()
    py = parent.winfo_rooty()
    pw = parent.winfo_width()
    ph = parent.winfo_height()
    dw = 350
    dh = 280 if tool_type == "drill" else 280
    dlg.geometry(f"+{px + (pw - dw) // 2}+{py + (ph - dh) // 2}")

    frm = tk.Frame(dlg)
    cfg.register_themed_widget(frm, bg="panel_bg")
    frm.pack(fill="x", padx=15, pady=15)

    type_name = t("tool_params.drill") if tool_type == "drill" else t("tool_params.endmill")
    lbl_title = tk.Label(frm, text=t("tool_params.not_found", type_name=type_name, diameter=f"{diameter:.2f}"),
                         font=("Arial", 10, "bold"))
    cfg.register_themed_widget(lbl_title, bg="panel_bg", fg="panel_fg")
    lbl_title.pack(pady=(0, 10))

    entries = {}
    row = 0

    def add_field(label_text, default, row_ref):
        r = tk.Frame(frm)
        cfg.register_themed_widget(r, bg="panel_bg")
        r.pack(fill="x", pady=2)
        
        lbl = tk.Label(r, text=label_text, width=24, anchor="w")
        cfg.register_themed_widget(lbl, bg="panel_bg", fg="panel_fg")
        lbl.pack(side="left")
        
        e = tk.Entry(r, width=10)
        cfg.register_themed_widget(e, bg="entry_bg", fg="entry_fg", insertbackground="entry_fg")
        e.insert(0, str(default if default is not None else ""))
        e.pack(side="right")
        attach_numeric_validation(e, dlg)
        entries[label_text] = e
        return row_ref + 1

    if tool_type == "drill":
        add_field(t("tool_params.fld.spindle_rpm"), defaults.get("spindle_speed", 10000) if defaults else 10000, row)
        row += 1
        add_field(t("tool_params.fld.plunge_feed"), defaults.get("feed_rate", 100) if defaults else 100, row)
        row += 1
        add_field(t("tool_params.fld.retract_feed"), defaults.get("rapid_rate", 500) if defaults else 500, row)
        row += 1
    else:
        add_field(t("tool_params.fld.spindle_rpm"), defaults.get("spindle_speed", 15000) if defaults else 15000, row)
        row += 1
        add_field(t("tool_params.fld.cutting_feed"), defaults.get("mill_feed", 50) if defaults else 50, row)
        row += 1

    add_to_db_var = tk.BooleanVar(value=False)
    chk_frame = tk.Frame(frm)
    cfg.register_themed_widget(chk_frame, bg="panel_bg")
    chk_frame.pack(fill="x", pady=(10, 5))
    
    chk = tk.Checkbutton(chk_frame, text=t("tool_params.add_to_db"), variable=add_to_db_var)
    cfg.register_themed_widget(chk, bg="panel_bg", fg="panel_fg", selectcolor="entry_bg")
    chk.pack(anchor="w")

    btn_frame = tk.Frame(frm)
    cfg.register_themed_widget(btn_frame, bg="panel_bg")
    btn_frame.pack(fill="x", pady=(10, 0))

    def on_ok():
        try:
            vals = {}
            for label, entry in entries.items():
                raw = entry.get().strip()
                if not raw:
                    raise ValueError(t("tool_params.field_empty", field=label))
                num = parse_decimal(raw)
                if num is None:
                    raise ValueError(t("app.dlg.invalid_number", value=raw))
                vals[label] = num

            if tool_type == "drill":
                result["spindle_speed"] = int(vals.get(t("tool_params.fld.spindle_rpm"), 10000))
                result["feed_rate"] = vals[t("tool_params.fld.plunge_feed")]
                result["rapid_rate"] = vals[t("tool_params.fld.retract_feed")]
            else:
                result["spindle_speed"] = int(vals.get(t("tool_params.fld.spindle_rpm"), 15000))
                result["mill_feed"] = vals[t("tool_params.fld.cutting_feed")]

            result["add_to_db"] = add_to_db_var.get()
            result["diameter"] = diameter
            result["tool_type"] = tool_type
            _unregister_widget_recursive(dlg)
            dlg.destroy()
        except ValueError as e:
            messagebox.showerror(t("app.dlg.error"), str(e), parent=dlg)
    
    def on_cancel():
        _unregister_widget_recursive(dlg)
        dlg.destroy()

    btn_ok = tk.Button(btn_frame, text=t("app.dlg.ok"), command=on_ok, width=10)
    cfg.register_themed_widget(btn_ok, bg="btn_bg", fg="btn_fg")
    btn_ok.pack(side="left", padx=5)
    
    btn_cancel = tk.Button(btn_frame, text=t("app.dlg.cancel"), command=on_cancel, width=10)
    cfg.register_themed_widget(btn_cancel, bg="btn_bg", fg="btn_fg")
    btn_cancel.pack(side="left", padx=5)
    
    dlg.protocol("WM_DELETE_WINDOW", on_cancel)

    dlg.wait_window()
    return result if result else None
