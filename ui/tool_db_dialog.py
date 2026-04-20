"""
Диалог управления базой инструментов (для "Про" режима).
Две вкладки: Сверла / Фрезы с Treeview и кнопками CRUD.
"""
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from core.tool_database import ToolDatabase


def _apply_table_style(tree):
    """Применить стиль таблицы: цветной заголовок, чередование строк, границы."""
    style = ttk.Style(tree)
    style_name = "ToolDB.Treeview"
    style.configure(style_name,
                    background="#FFFFFF",
                    foreground="#1A1A1A",
                    rowheight=24,
                    fieldbackground="#FFFFFF",
                    borderwidth=1,
                    relief="solid",
                    font=("Arial", 9))
    style.configure(f"{style_name}.Heading",
                    background="#4A6FA5",
                    foreground="#FFFFFF",
                    font=("Arial", 9, "bold"),
                    relief="flat",
                    borderwidth=1)
    style.map(f"{style_name}.Heading",
              background=[("active", "#3A5F95")])
    style.map(style_name,
              background=[("selected", "#B3CCE8")],
              foreground=[("selected", "#1A1A1A")])

    tree.configure(style=style_name)
    tree.tag_configure("odd",  background="#FFFFFF")
    tree.tag_configure("even", background="#EFEFEF")


def _restripe(tree):
    """Перекрасить строки чередованием нечётная/чётная."""
    for i, item in enumerate(tree.get_children()):
        tree.item(item, tags=("even" if i % 2 == 0 else "odd",))


def show_tool_db_dialog(parent, tool_db: ToolDatabase):
    """Показать диалог редактирования базы инструментов. Центрируется на parent."""

    dlg = tk.Toplevel(parent)
    dlg.title("База инструментов")
    dlg.geometry("1000x500")
    dlg.resizable(False, True)
    dlg.transient(parent)
    dlg.grab_set()

    # Центрирование на parent
    dlg.update_idletasks()
    px = parent.winfo_rootx()
    py = parent.winfo_rooty()
    pw = parent.winfo_width()
    ph = parent.winfo_height()
    dw = 1000
    dh = 500
    dlg.geometry(f"+{px + (pw - dw) // 2}+{py + (ph - dh) // 2}")
    dlg.minsize(1000, dh)

    # ---- Вкладки ----
    notebook = ttk.Notebook(dlg)
    notebook.pack(fill="both", expand=True, padx=5, pady=5)

    # ---- Сверла ----
    drill_frame = ttk.Frame(notebook, padding=5)
    notebook.add(drill_frame, text="Сверла")

    drill_tree = ttk.Treeview(drill_frame, columns=(
        "diameter", "spindle_speed", "plunge_feed", "retract_feed"
    ), show="headings", height=15)

    for col, width, heading in [
        ("diameter", 120, "Диаметр (мм)"),
        ("spindle_speed", 200, "Частота вращения (об/мин)"),
        ("plunge_feed", 220, "Скорость погружения (мм/мин)"),
        ("retract_feed", 200, "Скорость подъёма (мм/мин)"),
    ]:
        drill_tree.heading(col, text=heading, anchor="center")
        drill_tree.column(col, width=width, minwidth=50, anchor="center")

    # ---- Кнопки действий (вертикально, справа) — пакуются ДО скроллбара и дерева ----
    drill_btn_frame = ttk.Frame(drill_frame)
    drill_btn_frame.pack(side="right", fill="y", padx=5, pady=(5, 0))
    ttk.Button(drill_btn_frame, text="Добавить", command=lambda: _add_drill(tool_db, drill_tree)).pack(fill="x", pady=2)
    ttk.Button(drill_btn_frame, text="Редактировать", command=lambda: _edit_drill_selected(tool_db, drill_tree)).pack(fill="x", pady=2)
    ttk.Button(drill_btn_frame, text="Удалить", command=lambda: _delete_drill_selected(tool_db, drill_tree)).pack(fill="x", pady=2)

    _apply_table_style(drill_tree)
    drill_scroll = ttk.Scrollbar(drill_frame, orient="vertical", command=drill_tree.yview)
    drill_tree.configure(yscrollcommand=drill_scroll.set)
    drill_scroll.pack(side="right", fill="y")
    drill_tree.pack(side="left", fill="both", expand=True)

    # ---- Фрезы ----
    endmill_frame = ttk.Frame(notebook, padding=5)
    notebook.add(endmill_frame, text="Фрезы")

    endmill_tree = ttk.Treeview(endmill_frame, columns=(
        "diameter", "spindle_speed", "cutting_feed", "stepover"
    ), show="headings", height=15)

    for col, width, heading in [
        ("diameter", 120, "Диаметр (мм)"),
        ("spindle_speed", 200, "Частота вращения (об/мин)"),
        ("cutting_feed", 200, "Скорость реза (мм/мин)"),
        ("stepover", 200, "Ширина перекрытия (%)"),
    ]:
        endmill_tree.heading(col, text=heading, anchor="center")
        endmill_tree.column(col, width=width, minwidth=50, anchor="center")

    # ---- Кнопки действий (вертикально, справа) — пакуются ДО скроллбара и дерева ----
    endmill_btn_frame = ttk.Frame(endmill_frame)
    endmill_btn_frame.pack(side="right", fill="y", padx=5, pady=(5, 0))
    ttk.Button(endmill_btn_frame, text="Добавить", command=lambda: _add_endmill(tool_db, endmill_tree)).pack(fill="x", pady=2)
    ttk.Button(endmill_btn_frame, text="Редактировать", command=lambda: _edit_endmill_selected(tool_db, endmill_tree)).pack(fill="x", pady=2)
    ttk.Button(endmill_btn_frame, text="Удалить", command=lambda: _delete_endmill_selected(tool_db, endmill_tree)).pack(fill="x", pady=2)

    _apply_table_style(endmill_tree)
    endmill_scroll = ttk.Scrollbar(endmill_frame, orient="vertical", command=endmill_tree.yview)
    endmill_tree.configure(yscrollcommand=endmill_scroll.set)
    endmill_scroll.pack(side="right", fill="y")
    endmill_tree.pack(side="left", fill="both", expand=True)

    # ---- Общие кнопки внизу ----
    btn_frame = ttk.Frame(dlg, padding=5)
    btn_frame.pack(fill="x", padx=5, pady=5)

    def _populate_drills():
        for item in drill_tree.get_children():
            drill_tree.delete(item)
        for i, t in enumerate(tool_db.get_all_drills()):
            tag = "even" if i % 2 == 0 else "odd"
            drill_tree.insert("", "end", tags=(tag,), values=(
                t.get("diameter", 0), t.get("spindle_speed", 0),
                t.get("plunge_feed", 0), t.get("retract_feed", 0)
            ))

    def _populate_endmills():
        for item in endmill_tree.get_children():
            endmill_tree.delete(item)
        for i, t in enumerate(tool_db.get_all_endmills()):
            tag = "even" if i % 2 == 0 else "odd"
            endmill_tree.insert("", "end", tags=(tag,), values=(
                t.get("diameter", 0), t.get("spindle_speed", 0),
                t.get("cutting_feed", 0), t.get("stepover", 0)
            ))

    def _export_json():
        filename = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            title="Экспорт базы инструментов"
        )
        if filename:
            if tool_db.save(filename):
                messagebox.showinfo("Экспорт", "База успешно сохранена.")
            else:
                messagebox.showerror("Ошибка", "Не удалось сохранить файл.")

    def _import_json():
        filename = filedialog.askopenfilename(
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            title="Импорт базы инструментов"
        )
        if filename:
            if tool_db.load(filename):
                _populate_drills()
                _populate_endmills()
                messagebox.showinfo("Импорт", "База успешно загружена.")
            else:
                messagebox.showerror("Ошибка", "Не удалось загрузить файл.")

    ttk.Button(btn_frame, text="Экспорт", command=_export_json).pack(side="left", padx=2)
    ttk.Button(btn_frame, text="Импорт", command=_import_json).pack(side="left", padx=2)
    ttk.Button(btn_frame, text="Закрыть", command=dlg.destroy).pack(side="right", padx=2)

    # Заполнить
    _populate_drills()
    _populate_endmills()


# ==========================================================
# Вспомогательные диалоги редактирования
# ==========================================================

def _edit_drill(tool_db: ToolDatabase, diameter, tree, dlg_parent=None):
    """Диалог добавления/редактирования сверла."""
    is_new = diameter is None
    existing = None if is_new else tool_db.find_drill(diameter)

    dlg = tk.Toplevel(tree)
    dlg.title("Добавить сверло" if is_new else f"Редактировать сверло D={diameter}мм")
    dlg.resizable(False, False)
    dlg.transient(dlg_parent or tree.winfo_toplevel())
    dlg.grab_set()

    # Центрирование на родителе
    parent = dlg_parent or tree.winfo_toplevel()
    dlg.update_idletasks()
    px = parent.winfo_rootx()
    py = parent.winfo_rooty()
    pw = parent.winfo_width()
    ph = parent.winfo_height()
    dw = dlg.winfo_width() or 300
    dh = dlg.winfo_height() or 250
    dlg.geometry(f"+{px + (pw - dw) // 2}+{py + (ph - dh) // 2}")

    fields = [
        ("diameter", "Диаметр (мм):", "float"),
        ("spindle_speed", "Частота вращения (об/мин):", "int"),
        ("plunge_feed", "Скорость погружения (мм/мин):", "float"),
        ("retract_feed", "Скорость подъёма (мм/мин):", "float"),
    ]

    entries = {}
    frm = ttk.Frame(dlg, padding=15)
    frm.pack(fill="x")

    for key, label, typ in fields:
        r = tk.Frame(frm)
        r.pack(fill="x", pady=2)
        tk.Label(r, text=label, width=28, anchor="w").pack(side="left")
        e = tk.Entry(r, width=12, justify="center")
        if existing and key in existing:
            e.insert(0, str(existing[key]))
        elif key == "diameter" and not is_new:
            e.insert(0, str(diameter))
        if key == "diameter" and not is_new:
            e.configure(state="readonly")
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
                    vals[key] = float(raw) if raw else 0.0
                elif typ == "int":
                    vals[key] = int(float(raw)) if raw else 0
                else:
                    vals[key] = raw
            d = vals.pop("diameter")
            if is_new:
                if d <= 0:
                    raise ValueError("Диаметр должен быть > 0")
                tool_db.add_drill(d, **vals)
            else:
                tool_db.update_drill(d, **vals)
            _populate_tree_drills(tree, tool_db)
            dlg.destroy()
        except ValueError as e:
            messagebox.showerror("Ошибка", str(e), parent=dlg)

    btn_f = ttk.Frame(frm)
    btn_f.pack(fill="x", pady=(10, 5))
    ttk.Button(btn_f, text="OK", command=on_ok, width=10).pack(side="left", expand=True, padx=5)
    ttk.Button(btn_f, text="Отмена", command=dlg.destroy, width=10).pack(side="left", expand=True, padx=5)


def _edit_endmill(tool_db: ToolDatabase, diameter, tree, dlg_parent=None):
    """Диалог добавления/редактирования фрезы."""
    is_new = diameter is None
    existing = None if is_new else tool_db.find_endmill(diameter)

    dlg = tk.Toplevel(tree)
    dlg.title("Добавить фрезу" if is_new else f"Редактировать фрезу D={diameter}мм")
    dlg.resizable(False, False)
    dlg.transient(dlg_parent or tree.winfo_toplevel())
    dlg.grab_set()

    parent = dlg_parent or tree.winfo_toplevel()
    dlg.update_idletasks()
    px = parent.winfo_rootx()
    py = parent.winfo_rooty()
    pw = parent.winfo_width()
    ph = parent.winfo_height()
    dw = dlg.winfo_width() or 300
    dh = dlg.winfo_height() or 300
    dlg.geometry(f"+{px + (pw - dw) // 2}+{py + (ph - dh) // 2}")

    fields = [
        ("diameter", "Диаметр (мм):", "float"),
        ("spindle_speed", "Частота вращения (об/мин):", "int"),
        ("cutting_feed", "Скорость реза (мм/мин):", "float"),
        ("stepover", "Ширина перекрытия (%):", "float"),
    ]

    entries = {}
    frm = ttk.Frame(dlg, padding=15)
    frm.pack(fill="x")

    for key, label, typ in fields:
        r = tk.Frame(frm)
        r.pack(fill="x", pady=2)
        tk.Label(r, text=label, width=28, anchor="w").pack(side="left")
        e = tk.Entry(r, width=12, justify="center")
        if existing and key in existing:
            e.insert(0, str(existing[key]))
        elif key == "diameter" and not is_new:
            e.insert(0, str(diameter))
        if key == "diameter" and not is_new:
            e.configure(state="readonly")
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
                    vals[key] = float(raw) if raw else 0.0
                elif typ == "int":
                    vals[key] = int(float(raw)) if raw else 0
                else:
                    vals[key] = raw
            d = vals.pop("diameter")
            if is_new:
                if d <= 0:
                    raise ValueError("Диаметр должен быть > 0")
                tool_db.add_endmill(d, **vals)
            else:
                tool_db.update_endmill(d, **vals)
            _populate_tree_endmills(tree, tool_db)
            dlg.destroy()
        except ValueError as e:
            messagebox.showerror("Ошибка", str(e), parent=dlg)

    btn_f = ttk.Frame(frm)
    btn_f.pack(fill="x", pady=(10, 5))
    ttk.Button(btn_f, text="OK", command=on_ok, width=10).pack(side="left", expand=True, padx=5)
    ttk.Button(btn_f, text="Отмена", command=dlg.destroy, width=10).pack(side="left", expand=True, padx=5)


def _populate_tree_drills(tree, tool_db):
    for item in tree.get_children():
        tree.delete(item)
    for i, t in enumerate(tool_db.get_all_drills()):
        tag = "even" if i % 2 == 0 else "odd"
        tree.insert("", "end", tags=(tag,), values=(
            t["diameter"], t["spindle_speed"], t["plunge_feed"], t["retract_feed"]
        ))


def _populate_tree_endmills(tree, tool_db):
    for item in tree.get_children():
        tree.delete(item)
    for i, t in enumerate(tool_db.get_all_endmills()):
        tag = "even" if i % 2 == 0 else "odd"
        tree.insert("", "end", tags=(tag,), values=(
            t.get("diameter", 0), t.get("spindle_speed", 0),
            t.get("cutting_feed", 0), t.get("stepover", 0)
        ))


def _add_drill(tool_db, tree):
    _edit_drill(tool_db, None, tree, dlg_parent=tree.winfo_toplevel())


def _edit_drill_selected(tool_db, tree):
    sel = tree.selection()
    if not sel:
        messagebox.showwarning("Предупреждение", "Выберите сверло для редактирования.")
        return
    vals = tree.item(sel[0])["values"]
    diameter = float(vals[0])
    _edit_drill(tool_db, diameter, tree, dlg_parent=tree.winfo_toplevel())


def _delete_drill_selected(tool_db, tree):
    sel = tree.selection()
    if not sel:
        return
    vals = tree.item(sel[0])["values"]
    diameter = float(vals[0])
    if messagebox.askyesno("Удаление", f"Удалить сверло D={diameter}мм?"):
        tool_db.delete_drill(diameter)
        _populate_tree_drills(tree, tool_db)


def _add_endmill(tool_db, tree):
    _edit_endmill(tool_db, None, tree, dlg_parent=tree.winfo_toplevel())


def _edit_endmill_selected(tool_db, tree):
    sel = tree.selection()
    if not sel:
        messagebox.showwarning("Предупреждение", "Выберите фрезу для редактирования.")
        return
    vals = tree.item(sel[0])["values"]
    diameter = float(vals[0])
    _edit_endmill(tool_db, diameter, tree, dlg_parent=tree.winfo_toplevel())


def _delete_endmill_selected(tool_db, tree):
    sel = tree.selection()
    if not sel:
        return
    vals = tree.item(sel[0])["values"]
    diameter = float(vals[0])
    if messagebox.askyesno("Удаление", f"Удалить фрезу D={diameter}мм?"):
        tool_db.delete_endmill(diameter)
        _populate_tree_endmills(tree, tool_db)
