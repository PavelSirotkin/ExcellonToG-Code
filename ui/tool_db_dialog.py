"""
Диалог управления базой инструментов (для "Про" режима).
Две вкладки: Сверла / Фрезы с Treeview и кнопками CRUD.
"""
import tkinter as tk
from tkinter import ttk, filedialog
from ui import themed_messagebox as messagebox
from ui.numeric_entry import attach_numeric_validation
from core.tool_database import ToolDatabase
from core.i18n import t
from core.validators import parse_decimal, parse_int
from core.path_validator import validate_save_path
import core.config as cfg


def _unregister_widget_recursive(widget):
    """Рекурсивно отменить регистрацию виджета и всех его дочерних виджетов."""
    # Сначала обработать дочерние виджеты
    for child in widget.winfo_children():
        _unregister_widget_recursive(child)
    # Затем отменить регистрацию самого виджета
    cfg.unregister_themed_widget(widget)


def _apply_table_style(tree):
    """Применить стиль таблицы: цветной заголовок, чередование строк, границы."""
    style = ttk.Style(tree)
    style_name = "ToolDB.Treeview"
    
    # Определяем цвета в зависимости от темы
    if cfg.current_theme() == "dark":
        bg_color = "#2D2D2D"
        fg_color = "#E0E0E0"
        field_bg = "#2D2D2D"
        header_bg = "#3D6F95"
        header_fg = "#E0E0E0"
        header_active = "#2D5F85"
        selected_bg = "#264F78"
        selected_fg = "#E0E0E0"
        odd_bg = "#2D2D2D"
        even_bg = "#252526"
    else:
        bg_color = "#FFFFFF"
        fg_color = "#1A1A1A"
        field_bg = "#FFFFFF"
        header_bg = "#4A6FA5"
        header_fg = "#FFFFFF"
        header_active = "#3A5F95"
        selected_bg = "#B3CCE8"
        selected_fg = "#1A1A1A"
        odd_bg = "#FFFFFF"
        even_bg = "#EFEFEF"
    
    style.configure(style_name,
                    background=bg_color,
                    foreground=fg_color,
                    rowheight=24,
                    fieldbackground=field_bg,
                    borderwidth=1,
                    relief="solid",
                    font=("Arial", 9))
    style.configure(f"{style_name}.Heading",
                    background=header_bg,
                    foreground=header_fg,
                    font=("Arial", 9, "bold"),
                    relief="flat",
                    borderwidth=1)
    style.map(f"{style_name}.Heading",
              background=[("active", header_active)])
    style.map(style_name,
              background=[("selected", selected_bg)],
              foreground=[("selected", selected_fg)])

    tree.configure(style=style_name)
    tree.tag_configure("odd",  background=odd_bg)
    tree.tag_configure("even", background=even_bg)


def _restripe(tree):
    """Перекрасить строки чередованием нечётная/чётная."""
    for i, item in enumerate(tree.get_children()):
        tree.item(item, tags=("even" if i % 2 == 0 else "odd",))


def show_tool_db_dialog(parent, tool_db: ToolDatabase):
    """Показать диалог редактирования базы инструментов. Центрируется на parent."""

    dlg = tk.Toplevel(parent)
    dlg.title(t("tool_db.title"))
    dlg.geometry("1150x500")
    dlg.resizable(False, True)
    dlg.transient(parent)
    dlg.grab_set()

    # Применить тему к окну
    cfg.register_themed_widget(dlg, bg="panel_bg")

    # Центрирование на parent
    dlg.update_idletasks()
    px = parent.winfo_rootx()
    py = parent.winfo_rooty()
    pw = parent.winfo_width()
    ph = parent.winfo_height()
    dw = 1150
    dh = 500
    dlg.geometry(f"+{px + (pw - dw) // 2}+{py + (ph - dh) // 2}")
    dlg.minsize(1150, dh)

    # ---- Вкладки ----
    # Настройка стилей для Notebook
    style = ttk.Style()
    style.configure("ToolDB.TNotebook",
                    background=cfg.get_color("panel_bg"),
                    borderwidth=0)
    style.configure("ToolDB.TNotebook.Tab",
                    background=cfg.get_color("btn_bg"),
                    foreground=cfg.get_color("btn_fg"),
                    padding=[10, 5])
    style.map("ToolDB.TNotebook.Tab",
              background=[("selected", cfg.get_color("entry_bg"))],
              foreground=[("selected", cfg.get_color("entry_fg"))],
              expand=[("selected", [1, 1, 1, 0])])
    
    notebook = ttk.Notebook(dlg, style="ToolDB.TNotebook")
    notebook.pack(fill="both", expand=True, padx=5, pady=5)

    # ---- Сверла ----
    drill_frame = tk.Frame(notebook)
    cfg.register_themed_widget(drill_frame, bg="panel_bg")
    notebook.add(drill_frame, text=t("tool_db.tab.drills"))

    drill_tree = ttk.Treeview(drill_frame, columns=(
        "diameter", "spindle_speed", "plunge_feed", "retract_feed", "extra_depth"
    ), show="headings", height=15)

    for col, width, heading_key in [
        ("diameter", 120, "tool_db.col.diameter"),
        ("spindle_speed", 200, "tool_db.col.spindle_speed"),
        ("plunge_feed", 220, "tool_db.col.plunge_feed"),
        ("retract_feed", 200, "tool_db.col.retract_feed"),
        ("extra_depth", 150, "tool_db.col.extra_depth"),
    ]:
        heading = t(heading_key)
        drill_tree.heading(col, text=heading, anchor="center")
        drill_tree.column(col, width=width, minwidth=50, anchor="center")

    # ---- Кнопки действий (вертикально, справа) — пакуются ДО скроллбара и дерева ----
    drill_btn_frame = tk.Frame(drill_frame)
    cfg.register_themed_widget(drill_btn_frame, bg="panel_bg")
    drill_btn_frame.pack(side="right", fill="y", padx=5, pady=(5, 0))
    
    btn_add_drill = tk.Button(drill_btn_frame, text=t("tool_db.btn.add"), command=lambda: _add_drill(tool_db, drill_tree))
    cfg.register_themed_widget(btn_add_drill, bg="btn_bg", fg="btn_fg")
    btn_add_drill.pack(fill="x", pady=2)
    
    btn_edit_drill = tk.Button(drill_btn_frame, text=t("tool_db.btn.edit"), command=lambda: _edit_drill_selected(tool_db, drill_tree))
    cfg.register_themed_widget(btn_edit_drill, bg="btn_bg", fg="btn_fg")
    btn_edit_drill.pack(fill="x", pady=2)
    
    btn_del_drill = tk.Button(drill_btn_frame, text=t("tool_db.btn.delete"), command=lambda: _delete_drill_selected(tool_db, drill_tree))
    cfg.register_themed_widget(btn_del_drill, bg="btn_bg", fg="btn_fg")
    btn_del_drill.pack(fill="x", pady=2)

    _apply_table_style(drill_tree)
    drill_scroll = ttk.Scrollbar(drill_frame, orient="vertical", command=drill_tree.yview)
    drill_tree.configure(yscrollcommand=drill_scroll.set)
    drill_scroll.pack(side="right", fill="y")
    drill_tree.pack(side="left", fill="both", expand=True)

    # ---- Фрезы ----
    endmill_frame = tk.Frame(notebook)
    cfg.register_themed_widget(endmill_frame, bg="panel_bg")
    notebook.add(endmill_frame, text=t("tool_db.tab.endmills"))

    endmill_tree = ttk.Treeview(endmill_frame, columns=(
        "diameter", "spindle_speed", "cutting_feed", "stepover"
    ), show="headings", height=15)

    for col, width, heading_key in [
        ("diameter", 120, "tool_db.col.diameter"),
        ("spindle_speed", 200, "tool_db.col.spindle_speed"),
        ("cutting_feed", 200, "tool_db.col.cutting_feed"),
        ("stepover", 200, "tool_db.col.stepover"),
    ]:
        heading = t(heading_key)
        endmill_tree.heading(col, text=heading, anchor="center")
        endmill_tree.column(col, width=width, minwidth=50, anchor="center")

    # ---- Кнопки действий (вертикально, справа) — пакуются ДО скроллбара и дерева ----
    endmill_btn_frame = tk.Frame(endmill_frame)
    cfg.register_themed_widget(endmill_btn_frame, bg="panel_bg")
    endmill_btn_frame.pack(side="right", fill="y", padx=5, pady=(5, 0))
    
    btn_add_endmill = tk.Button(endmill_btn_frame, text=t("tool_db.btn.add"), command=lambda: _add_endmill(tool_db, endmill_tree))
    cfg.register_themed_widget(btn_add_endmill, bg="btn_bg", fg="btn_fg")
    btn_add_endmill.pack(fill="x", pady=2)
    
    btn_edit_endmill = tk.Button(endmill_btn_frame, text=t("tool_db.btn.edit"), command=lambda: _edit_endmill_selected(tool_db, endmill_tree))
    cfg.register_themed_widget(btn_edit_endmill, bg="btn_bg", fg="btn_fg")
    btn_edit_endmill.pack(fill="x", pady=2)
    
    btn_del_endmill = tk.Button(endmill_btn_frame, text=t("tool_db.btn.delete"), command=lambda: _delete_endmill_selected(tool_db, endmill_tree))
    cfg.register_themed_widget(btn_del_endmill, bg="btn_bg", fg="btn_fg")
    btn_del_endmill.pack(fill="x", pady=2)

    _apply_table_style(endmill_tree)
    endmill_scroll = ttk.Scrollbar(endmill_frame, orient="vertical", command=endmill_tree.yview)
    endmill_tree.configure(yscrollcommand=endmill_scroll.set)
    endmill_scroll.pack(side="right", fill="y")
    endmill_tree.pack(side="left", fill="both", expand=True)

    # ---- Общие кнопки внизу ----
    btn_frame = tk.Frame(dlg)
    cfg.register_themed_widget(btn_frame, bg="panel_bg")
    btn_frame.pack(fill="x", padx=5, pady=5)

    def _populate_drills():
        for item in drill_tree.get_children():
            drill_tree.delete(item)
        for i, td in enumerate(tool_db.get_all_drills()):
            tag = "even" if i % 2 == 0 else "odd"
            drill_tree.insert("", "end", tags=(tag,), values=(
                td.get("diameter", 0), td.get("spindle_speed", 0),
                td.get("plunge_feed", 0), td.get("retract_feed", 0),
                # extra_depth: для legacy-записей без поля показываем 0.
                td.get("extra_depth", 0)
            ))

    def _populate_endmills():
        for item in endmill_tree.get_children():
            endmill_tree.delete(item)
        for i, td in enumerate(tool_db.get_all_endmills()):
            tag = "even" if i % 2 == 0 else "odd"
            endmill_tree.insert("", "end", tags=(tag,), values=(
                td.get("diameter", 0), td.get("spindle_speed", 0),
                td.get("cutting_feed", 0), td.get("stepover", 0)
            ))

    def _export_json():
        # parent=dlg критичен на Linux: без него file-dialog появляется за
        # модальным окном базы инструментов и пользователь его не видит.
        filename = filedialog.asksaveasfilename(
            parent=dlg,
            defaultextension=".json",
            filetypes=[(t("app.filetype.json"), "*.json"), (t("app.filetype.all"), "*.*")],
            title=t("tool_db.dlg.export_title")
        )
        if filename:
            # Проверка безопасности пути
            is_valid, error_msg = validate_save_path(filename)
            if not is_valid:
                messagebox.showerror(t("app.dlg.error"),
                                   t("app.err.invalid_path", error=error_msg), parent=dlg)
                return
            if tool_db.save(filename):
                messagebox.showinfo(t("tool_db.dlg.export_ok.title"), t("tool_db.dlg.export_ok.msg"), parent=dlg)
            else:
                messagebox.showerror(t("app.dlg.error"), t("tool_db.dlg.export_err"), parent=dlg)

    def _import_json():
        filename = filedialog.askopenfilename(
            parent=dlg,
            filetypes=[(t("app.filetype.json"), "*.json"), (t("app.filetype.all"), "*.*")],
            title=t("tool_db.dlg.import_title")
        )
        if filename:
            if tool_db.load(filename):
                _populate_drills()
                _populate_endmills()
                messagebox.showinfo(t("tool_db.dlg.import_ok.title"), t("tool_db.dlg.import_ok.msg"), parent=dlg)
            else:
                messagebox.showerror(t("app.dlg.error"), t("tool_db.dlg.import_err"), parent=dlg)

    btn_export = tk.Button(btn_frame, text=t("tool_db.btn.export"), command=_export_json)
    cfg.register_themed_widget(btn_export, bg="btn_bg", fg="btn_fg")
    btn_export.pack(side="left", padx=2)
    
    btn_import = tk.Button(btn_frame, text=t("tool_db.btn.import"), command=_import_json)
    cfg.register_themed_widget(btn_import, bg="btn_bg", fg="btn_fg")
    btn_import.pack(side="left", padx=2)
    
    def _on_close():
        _unregister_widget_recursive(dlg)
        dlg.destroy()
    
    btn_close = tk.Button(btn_frame, text=t("app.dlg.close"), command=_on_close)
    cfg.register_themed_widget(btn_close, bg="btn_bg", fg="btn_fg")
    btn_close.pack(side="right", padx=2)
    
    dlg.protocol("WM_DELETE_WINDOW", _on_close)

    # Заполнить
    _populate_drills()
    _populate_endmills()
    
    # Применить темную тему к заголовку окна синхронно
    dlg.update_idletasks()
    cfg.apply_window_theme(dlg)


# ==========================================================
# Вспомогательные диалоги редактирования
# ==========================================================

def _edit_drill(tool_db: ToolDatabase, diameter, tree, dlg_parent=None):
    """Диалог добавления/редактирования сверла."""
    is_new = diameter is None
    existing = None if is_new else tool_db.find_drill(diameter)

    dlg = tk.Toplevel(tree)
    dlg.title(t("tool_db.dlg.add_drill") if is_new else t("tool_db.dlg.edit_drill", diameter=diameter))
    dlg.resizable(False, False)
    dlg.transient(dlg_parent or tree.winfo_toplevel())
    dlg.grab_set()
    
    # Применить тему к окну
    cfg.register_themed_widget(dlg, bg="panel_bg")

    # Центрирование на родителе
    parent = dlg_parent or tree.winfo_toplevel()

    fields = [
        ("diameter", t("tool_db.fld.diameter"), "float"),
        ("spindle_speed", t("tool_db.fld.spindle_speed"), "int"),
        ("plunge_feed", t("tool_db.fld.plunge_feed"), "float"),
        ("retract_feed", t("tool_db.fld.retract_feed"), "float"),
        ("extra_depth", t("tool_db.fld.extra_depth"), "float"),
    ]

    entries = {}
    frm = tk.Frame(dlg)
    cfg.register_themed_widget(frm, bg="panel_bg")
    frm.pack(fill="x", padx=15, pady=15)

    for key, label, typ in fields:
        r = tk.Frame(frm)
        cfg.register_themed_widget(r, bg="panel_bg")
        r.pack(fill="x", pady=2)

        lbl = tk.Label(r, text=label, width=28, anchor="w")
        cfg.register_themed_widget(lbl, bg="panel_bg", fg="panel_fg")
        lbl.pack(side="left")

        e = tk.Entry(r, width=12, justify="center")
        if existing:
            # .get(key, 0) — для legacy-записей без новых полей (extra_depth)
            # показываем «0» вместо пустого поля. На существующие поля не
            # влияет: они всегда есть в записи после add_drill.
            e.insert(0, str(existing.get(key, 0)))
        elif key == "diameter" and not is_new:
            e.insert(0, str(diameter))
        if key == "diameter" and not is_new:
            e.configure(state="readonly")
            # Для readonly полей применяем тему после установки состояния
            cfg.register_themed_widget(e, bg="entry_bg", fg="entry_fg", readonlybackground="entry_bg")
        else:
            cfg.register_themed_widget(e, bg="entry_bg", fg="entry_fg", insertbackground="entry_fg")
            attach_numeric_validation(e, dlg)
        e.pack(side="right")
        entries[key] = (e, typ)

    def on_ok():
        try:
            vals = {}
            for key, (e, typ) in entries.items():
                if key == "diameter" and not is_new:
                    vals[key] = diameter  # используем исходный диаметр как ключ
                    continue
                raw = e.get().strip()
                if typ == "float":
                    vals[key] = parse_decimal(raw, None) if raw else 0.0
                    if vals[key] is None:
                        raise ValueError(t("app.dlg.invalid_number", value=raw))
                elif typ == "int":
                    vals[key] = parse_int(raw, None) if raw else 0
                    if vals[key] is None:
                        raise ValueError(t("app.dlg.invalid_number", value=raw))
                else:
                    vals[key] = raw
            d = vals.pop("diameter")
            if is_new:
                if d <= 0:
                    raise ValueError(t("tool_db.dlg.diameter_positive"))
                tool_db.add_drill(d, **vals)
            else:
                tool_db.update_drill(d, **vals)
            _populate_tree_drills(tree, tool_db)
            _unregister_widget_recursive(dlg)
            dlg.destroy()
        except ValueError as e:
            messagebox.showerror(t("app.dlg.error"), str(e), parent=dlg)
    
    def on_cancel():
        _unregister_widget_recursive(dlg)
        dlg.destroy()

    btn_f = tk.Frame(frm)
    cfg.register_themed_widget(btn_f, bg="panel_bg")
    btn_f.pack(fill="x", pady=(10, 5))
    
    btn_ok = tk.Button(btn_f, text=t("app.dlg.ok"), command=on_ok, width=10)
    cfg.register_themed_widget(btn_ok, bg="btn_bg", fg="btn_fg")
    btn_ok.pack(side="left", expand=True, padx=5)
    
    btn_cancel = tk.Button(btn_f, text=t("app.dlg.cancel"), command=on_cancel, width=10)
    cfg.register_themed_widget(btn_cancel, bg="btn_bg", fg="btn_fg")
    btn_cancel.pack(side="left", expand=True, padx=5)
    
    dlg.protocol("WM_DELETE_WINDOW", on_cancel)
    
    # Центрирование и применение темы после создания всех виджетов
    dlg.update_idletasks()
    px = parent.winfo_rootx()
    py = parent.winfo_rooty()
    pw = parent.winfo_width()
    ph = parent.winfo_height()
    dw = dlg.winfo_width() or 300
    dh = dlg.winfo_height() or 250
    dlg.geometry(f"+{px + (pw - dw) // 2}+{py + (ph - dh) // 2}")
    cfg.apply_window_theme(dlg)


def _edit_endmill(tool_db: ToolDatabase, diameter, tree, dlg_parent=None):
    """Диалог добавления/редактирования фрезы."""
    is_new = diameter is None
    existing = None if is_new else tool_db.find_endmill(diameter)

    dlg = tk.Toplevel(tree)
    dlg.title(t("tool_db.dlg.add_endmill") if is_new else t("tool_db.dlg.edit_endmill", diameter=diameter))
    dlg.resizable(False, False)
    dlg.transient(dlg_parent or tree.winfo_toplevel())
    dlg.grab_set()
    
    # Применить тему к окну
    cfg.register_themed_widget(dlg, bg="panel_bg")

    parent = dlg_parent or tree.winfo_toplevel()

    fields = [
        ("diameter", t("tool_db.fld.diameter"), "float"),
        ("spindle_speed", t("tool_db.fld.spindle_speed"), "int"),
        ("cutting_feed", t("tool_db.fld.cutting_feed"), "float"),
        ("stepover", t("tool_db.fld.stepover"), "float"),
    ]

    entries = {}
    frm = tk.Frame(dlg)
    cfg.register_themed_widget(frm, bg="panel_bg")
    frm.pack(fill="x", padx=15, pady=15)

    for key, label, typ in fields:
        r = tk.Frame(frm)
        cfg.register_themed_widget(r, bg="panel_bg")
        r.pack(fill="x", pady=2)
        
        lbl = tk.Label(r, text=label, width=28, anchor="w")
        cfg.register_themed_widget(lbl, bg="panel_bg", fg="panel_fg")
        lbl.pack(side="left")
        
        e = tk.Entry(r, width=12, justify="center")
        if existing and key in existing:
            e.insert(0, str(existing[key]))
        elif key == "diameter" and not is_new:
            e.insert(0, str(diameter))
        if key == "diameter" and not is_new:
            e.configure(state="readonly")
            # Для readonly полей применяем тему после установки состояния
            cfg.register_themed_widget(e, bg="entry_bg", fg="entry_fg", readonlybackground="entry_bg")
        else:
            cfg.register_themed_widget(e, bg="entry_bg", fg="entry_fg", insertbackground="entry_fg")
            attach_numeric_validation(e, dlg)
        e.pack(side="right")
        entries[key] = (e, typ)

    def on_ok():
        try:
            vals = {}
            for key, (e, typ) in entries.items():
                if key == "diameter" and not is_new:
                    vals[key] = diameter  # используем исходный диаметр как ключ
                    continue
                raw = e.get().strip()
                if typ == "float":
                    vals[key] = parse_decimal(raw, None) if raw else 0.0
                    if vals[key] is None:
                        raise ValueError(t("app.dlg.invalid_number", value=raw))
                elif typ == "int":
                    vals[key] = parse_int(raw, None) if raw else 0
                    if vals[key] is None:
                        raise ValueError(t("app.dlg.invalid_number", value=raw))
                else:
                    vals[key] = raw
            d = vals.pop("diameter")
            if is_new:
                if d <= 0:
                    raise ValueError(t("tool_db.dlg.diameter_positive"))
                tool_db.add_endmill(d, **vals)
            else:
                tool_db.update_endmill(d, **vals)
            _populate_tree_endmills(tree, tool_db)
            _unregister_widget_recursive(dlg)
            dlg.destroy()
        except ValueError as e:
            messagebox.showerror(t("app.dlg.error"), str(e), parent=dlg)
    
    def on_cancel():
        _unregister_widget_recursive(dlg)
        dlg.destroy()

    btn_f = tk.Frame(frm)
    cfg.register_themed_widget(btn_f, bg="panel_bg")
    btn_f.pack(fill="x", pady=(10, 5))
    
    btn_ok = tk.Button(btn_f, text=t("app.dlg.ok"), command=on_ok, width=10)
    cfg.register_themed_widget(btn_ok, bg="btn_bg", fg="btn_fg")
    btn_ok.pack(side="left", expand=True, padx=5)
    
    btn_cancel = tk.Button(btn_f, text=t("app.dlg.cancel"), command=on_cancel, width=10)
    cfg.register_themed_widget(btn_cancel, bg="btn_bg", fg="btn_fg")
    btn_cancel.pack(side="left", expand=True, padx=5)
    
    dlg.protocol("WM_DELETE_WINDOW", on_cancel)
    
    # Центрирование и применение темы после создания всех виджетов
    dlg.update_idletasks()
    px = parent.winfo_rootx()
    py = parent.winfo_rooty()
    pw = parent.winfo_width()
    ph = parent.winfo_height()
    dw = dlg.winfo_width() or 300
    dh = dlg.winfo_height() or 300
    dlg.geometry(f"+{px + (pw - dw) // 2}+{py + (ph - dh) // 2}")
    cfg.apply_window_theme(dlg)


def _populate_tree_drills(tree, tool_db):
    for item in tree.get_children():
        tree.delete(item)
    for i, td in enumerate(tool_db.get_all_drills()):
        tag = "even" if i % 2 == 0 else "odd"
        tree.insert("", "end", tags=(tag,), values=(
            td["diameter"], td["spindle_speed"], td["plunge_feed"], td["retract_feed"],
            # extra_depth: для legacy-записей без поля показываем 0.
            td.get("extra_depth", 0)
        ))


def _populate_tree_endmills(tree, tool_db):
    for item in tree.get_children():
        tree.delete(item)
    for i, td in enumerate(tool_db.get_all_endmills()):
        tag = "even" if i % 2 == 0 else "odd"
        tree.insert("", "end", tags=(tag,), values=(
            td.get("diameter", 0), td.get("spindle_speed", 0),
            td.get("cutting_feed", 0), td.get("stepover", 0)
        ))


def _add_drill(tool_db, tree):
    _edit_drill(tool_db, None, tree, dlg_parent=tree.winfo_toplevel())


def _edit_drill_selected(tool_db, tree):
    top = tree.winfo_toplevel()
    sel = tree.selection()
    if not sel:
        messagebox.showwarning(t("app.dlg.warning"), t("tool_db.dlg.select_drill"), parent=top)
        return
    vals = tree.item(sel[0])["values"]
    diameter = float(vals[0])
    _edit_drill(tool_db, diameter, tree, dlg_parent=top)


def _delete_drill_selected(tool_db, tree):
    sel = tree.selection()
    if not sel:
        return
    top = tree.winfo_toplevel()
    vals = tree.item(sel[0])["values"]
    diameter = float(vals[0])
    if messagebox.askyesno(t("app.dlg.confirm_delete"),
                            t("tool_db.dlg.confirm_delete_drill", diameter=diameter),
                            parent=top):
        tool_db.delete_drill(diameter)
        _populate_tree_drills(tree, tool_db)


def _add_endmill(tool_db, tree):
    _edit_endmill(tool_db, None, tree, dlg_parent=tree.winfo_toplevel())


def _edit_endmill_selected(tool_db, tree):
    top = tree.winfo_toplevel()
    sel = tree.selection()
    if not sel:
        messagebox.showwarning(t("app.dlg.warning"), t("tool_db.dlg.select_endmill"), parent=top)
        return
    vals = tree.item(sel[0])["values"]
    diameter = float(vals[0])
    _edit_endmill(tool_db, diameter, tree, dlg_parent=top)


def _delete_endmill_selected(tool_db, tree):
    sel = tree.selection()
    if not sel:
        return
    top = tree.winfo_toplevel()
    vals = tree.item(sel[0])["values"]
    diameter = float(vals[0])
    if messagebox.askyesno(t("app.dlg.confirm_delete"),
                            t("tool_db.dlg.confirm_delete_endmill", diameter=diameter),
                            parent=top):
        tool_db.delete_endmill(diameter)
        _populate_tree_endmills(tree, tool_db)
