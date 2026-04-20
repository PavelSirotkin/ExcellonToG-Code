"""
Легенда инструментов: отображение, чекбоксы, контекстное меню, hover/solo.
"""
import tkinter as tk
import core.config as cfg

# Переменная чекбокса видимости контура — создаётся в update_legend, используется в toggle_tool_visibility
_outline_var = None


def toggle_tool_visibility(tool, tool_type):
    """Переключение видимости инструмента."""
    if tool_type == 'holes' and cfg.current_tools and tool in cfg.current_tools:
        var = cfg.current_tools[tool].get('var')
        if var is not None:
            cfg.current_tools[tool]['visible'] = var.get()
    elif tool_type == 'slots' and cfg.slot_tools and tool in cfg.slot_tools:
        var = cfg.slot_tools[tool].get('var')
        if var is not None:
            cfg.slot_tools[tool]['visible'] = var.get()
    elif tool_type == 'outline':
        if _outline_var is not None:
            cfg.board_outline_visible = _outline_var.get()
    from ui.renderer import redraw_grid
    redraw_grid()


def bind_mousewheel_to_children(widget):
    """Рекурсивная привязка прокрутки к дочерним виджетам."""
    legend_canvas = cfg.get_widget("legend_canvas")
    widget.bind("<MouseWheel>", lambda e: legend_canvas.yview_scroll(int(-1 * (e.delta / 120)), "units"))
    widget.bind("<Button-4>", lambda e: legend_canvas.yview_scroll(-1, "units"))
    widget.bind("<Button-5>", lambda e: legend_canvas.yview_scroll(1, "units"))
    for child in widget.winfo_children():
        bind_mousewheel_to_children(child)


def update_legend():
    """Построение/перестройка легенды с чекбоксами."""
    global _outline_var
    cfg.hovered_tool = None
    cfg.solo_tool = None
    _outline_var = None

    legend_frame = cfg.get_widget("legend_frame")
    for widget in legend_frame.winfo_children():
        widget.destroy()
    colors = cfg.HOLE_COLORS
    slot_colors = cfg.SLOT_COLORS

    def make_context_menu(event):
        menu = tk.Menu(cfg.get_widget("root"), tearoff=0)
        menu.add_command(label="✅ Показать все",
                         command=lambda: legend_show_all())
        menu.add_command(label="🚫 Скрыть все",
                         command=lambda: legend_hide_all())
        menu.add_separator()
        menu.add_command(label="❌ Отмена изоляции",
                         command=lambda: legend_cancel_solo())
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()

    def legend_show_all():
        if cfg.current_tools:
            for d in cfg.current_tools.values():
                d['visible'] = True
                if d['var']:
                    d['var'].set(True)
        if cfg.slot_tools:
            for d in cfg.slot_tools.values():
                d['visible'] = True
                if d['var']:
                    d['var'].set(True)
        if cfg.board_outline:
            cfg.board_outline_visible = True
            if _outline_var is not None:
                _outline_var.set(True)
        _refresh_legend_highlight()
        from ui.renderer import redraw_grid
        redraw_grid()

    def legend_hide_all():
        if cfg.current_tools:
            for d in cfg.current_tools.values():
                d['visible'] = False
                if d['var']:
                    d['var'].set(False)
        if cfg.slot_tools:
            for d in cfg.slot_tools.values():
                d['visible'] = False
                if d['var']:
                    d['var'].set(False)
        if cfg.board_outline:
            cfg.board_outline_visible = False
            if _outline_var is not None:
                _outline_var.set(False)
        _refresh_legend_highlight()
        from ui.renderer import redraw_grid
        redraw_grid()

    def legend_cancel_solo():
        cfg.solo_tool = None
        legend_show_all()

    def on_row_enter(event, tool, tool_type):
        cfg.hovered_tool = (tool, tool_type)
        _refresh_legend_highlight()
        from ui.renderer import redraw_grid
        redraw_grid()

    def on_row_leave(event, tool, tool_type):
        if cfg.hovered_tool == (tool, tool_type):
            cfg.hovered_tool = None
            _refresh_legend_highlight()
            from ui.renderer import redraw_grid
            redraw_grid()

    def on_solo_click(tool, tool_type):
        if cfg.solo_tool == (tool, tool_type):
            cfg.solo_tool = None
            if cfg.current_tools:
                for d in cfg.current_tools.values():
                    d['visible'] = True
                    if d['var']:
                        d['var'].set(True)
            if cfg.slot_tools:
                for d in cfg.slot_tools.values():
                    d['visible'] = True
                    if d['var']:
                        d['var'].set(True)
            if cfg.board_outline:
                cfg.board_outline_visible = True
                if _outline_var is not None:
                    _outline_var.set(True)
        else:
            cfg.solo_tool = (tool, tool_type)
            if cfg.current_tools:
                for t, d in cfg.current_tools.items():
                    vis = (tool_type == 'holes' and t == tool)
                    d['visible'] = vis
                    if d['var']:
                        d['var'].set(vis)
            if cfg.slot_tools:
                for t, d in cfg.slot_tools.items():
                    vis = (tool_type == 'slots' and t == tool)
                    d['visible'] = vis
                    if d['var']:
                        d['var'].set(vis)
            if cfg.board_outline:
                outline_vis = (tool_type == 'outline')
                cfg.board_outline_visible = outline_vis
                if _outline_var is not None:
                    _outline_var.set(outline_vis)
        _refresh_legend_highlight()
        from ui.renderer import redraw_grid
        redraw_grid()

    # Хранилище строк легенды
    legend_rows = {}

    def _build_row(parent, tool, data, color, icon_text, label_text, tool_type):
        frame = tk.Frame(parent, cursor="hand2")
        frame.pack(anchor="w", fill="x", padx=2, pady=1)
        legend_rows[(tool, tool_type)] = frame

        var = tk.BooleanVar(value=data['visible'])
        data['var'] = var
        cb = tk.Checkbutton(frame, variable=var,
                            command=lambda t=tool, tt=tool_type: toggle_tool_visibility(t, tt))
        cb.pack(side="left")

        solo_btn = tk.Label(frame, text="👁", font=("Arial", 9), cursor="hand2",
                            relief="flat", padx=2)
        solo_btn.pack(side="left")
        solo_btn.bind("<Button-1>",
                      lambda e, t=tool, tt=tool_type: on_solo_click(t, tt))

        tk.Label(frame, text=icon_text, fg=color, font=("Arial", 12)).pack(side="left")
        lbl = tk.Label(frame, text=label_text, font=("Arial", 9))
        lbl.pack(side="left")

        for w in [frame, cb, solo_btn, lbl]:
            w.bind("<Enter>", lambda e, t=tool, tt=tool_type: on_row_enter(e, t, tt))
            w.bind("<Leave>", lambda e, t=tool, tt=tool_type: on_row_leave(e, t, tt))
            w.bind("<Button-3>", make_context_menu)

        return frame

    legend_frame.bind("<Button-3>", make_context_menu)

    if cfg.current_tools:
        hdr = tk.Label(legend_frame, text="Круглые отверстия:",
                       font=("Arial", 9, "bold"))
        hdr.pack(anchor="w")
        hdr.bind("<Button-3>", make_context_menu)
        for i, (tool, data) in enumerate(cfg.current_tools.items()):
            color = colors[i % len(colors)]
            text = f"T{tool} ⌀{data['diameter']:.2f}мм ({len(data['holes'])} отв.)"
            _build_row(legend_frame, tool, data, color, "●", text, 'holes')

    if cfg.slot_tools:
        sp = tk.Label(legend_frame, text="")
        sp.pack()
        sp.bind("<Button-3>", make_context_menu)
        hdr2 = tk.Label(legend_frame, text="Овальные отверстия (слоты):",
                        font=("Arial", 9, "bold"))
        hdr2.pack(anchor="w")
        hdr2.bind("<Button-3>", make_context_menu)
        for i, (tool, data) in enumerate(cfg.slot_tools.items()):
            color = slot_colors[i % len(slot_colors)]
            text = f"T{tool} ⌀{data['diameter']:.2f}мм ({len(data['slots'])} слот.)"
            _build_row(legend_frame, tool, data, color, "━", text, 'slots')

    # Контур платы (Gerber outline) — если загружен
    if cfg.board_outline:
        sp3 = tk.Label(legend_frame, text="")
        sp3.pack()
        sp3.bind("<Button-3>", make_context_menu)
        hdr3 = tk.Label(legend_frame, text="Обрезка по контуру:",
                        font=("Arial", 9, "bold"))
        hdr3.pack(anchor="w")
        hdr3.bind("<Button-3>", make_context_menu)

        # Считываем параметры обрезки из Entry-виджетов
        try:
            outline_d = float(cfg.get_widget("outline_tool_diameter_entry").get())
        except (ValueError, AttributeError):
            outline_d = 0.0
        try:
            n_tabs = int(cfg.get_widget("outline_n_tabs_entry").get())
        except (ValueError, AttributeError):
            n_tabs = 0

        # Фиктивный data-словарь для переиспользования _build_row
        outline_data = {'visible': cfg.board_outline_visible, 'var': None}
        text = f"⌀{outline_d:.2f}мм  (фреза, {n_tabs} tabs)"
        _build_row(legend_frame, 'outline', outline_data,
                   "#444444", "▭", text, 'outline')
        # Запоминаем созданную переменную для toggle_tool_visibility
        _outline_var = outline_data['var']

    if cfg.current_tools or cfg.slot_tools or cfg.board_outline:
        sp2 = tk.Label(legend_frame, text="")
        sp2.pack()
        sp2.bind("<Button-3>", make_context_menu)
        total_holes = sum(len(d['holes']) for d in cfg.current_tools.values()) if cfg.current_tools else 0
        total_slots = sum(len(d['slots']) for d in cfg.slot_tools.values()) if cfg.slot_tools else 0
        ft = tk.Label(legend_frame,
                      text=f"Всего: {total_holes} отв. + {total_slots} слот.",
                      font=("Arial", 9, "bold"))
        ft.pack(anchor="w")
        ft.bind("<Button-3>", make_context_menu)

    def _refresh_legend_highlight():
        for key, frame in legend_rows.items():
            is_solo_active = cfg.solo_tool is not None
            is_this_solo = (cfg.solo_tool == key)
            is_hovered = (cfg.hovered_tool == key)

            if is_hovered and not is_solo_active:
                bg = "#D0E8FF"
            elif is_this_solo:
                bg = "#C8F0C8"
            elif is_solo_active and not is_this_solo:
                bg = "#F0F0F0"
            else:
                bg = frame.master.cget("bg") if frame.master else "SystemButtonFace"

            frame.config(bg=bg)
            for w in frame.winfo_children():
                try:
                    w.config(bg=bg)
                except Exception:
                    pass

    # Привязка прокрутки
    legend_canvas = cfg.get_widget("legend_canvas")
    if legend_canvas:
        bind_mousewheel_to_children(legend_frame)
