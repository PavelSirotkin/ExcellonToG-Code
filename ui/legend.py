"""
Легенда инструментов: отображение, чекбоксы, контекстное меню, hover/solo.
Реализует управление памятью для предотвращения утечек при частых обновлениях.
"""
import logging
import tkinter as tk
import weakref
from core.i18n import t
import core.config as cfg

logger = logging.getLogger(__name__)

# Переменная чекбокса видимости контура — создаётся в update_legend, используется в toggle_tool_visibility
_outline_var = None

# Хранилище привязок событий для явной отписки
_event_bindings = []


def _unbind_events_recursive(widget):
    """
    Рекурсивно отвязать все события от виджета и его дочерних виджетов.
    Предотвращает утечки памяти от lambda-функций и callback'ов.
    """
    try:
        # Получить все привязанные события для виджета
        for sequence in ('<Enter>', '<Leave>', '<Button-1>', '<Button-3>', 
                        '<MouseWheel>', '<Button-4>', '<Button-5>'):
            try:
                widget.unbind(sequence)
            except tk.TclError:
                pass  # Событие не было привязано
        
        # Обработать дочерние виджеты
        for child in widget.winfo_children():
            _unbind_events_recursive(child)
    except tk.TclError:
        # Виджет уже уничтожен
        pass


def _unregister_widget_recursive(widget):
    """
    Рекурсивно отменить регистрацию виджета и всех его дочерних виджетов.
    Включает явную отписку от событий для предотвращения утечек памяти.
    """
    try:
        # Сначала отвязать все события
        _unbind_events_recursive(widget)
        
        # Затем обработать дочерние виджеты
        for child in widget.winfo_children():
            _unregister_widget_recursive(child)
        
        # Наконец, отменить регистрацию самого виджета
        cfg.unregister_themed_widget(widget)
    except tk.TclError:
        # Виджет уже уничтожен
        pass


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
    """
    Рекурсивная привязка прокрутки к дочерним виджетам.
    Использует weak reference для предотвращения циклических ссылок.
    """
    legend_canvas = cfg.get_widget("legend_canvas")
    if not legend_canvas:
        return
    
    # Используем weak reference для canvas
    canvas_ref = weakref.ref(legend_canvas)

    def _needs_scroll(canvas):
        """True, если содержимое не помещается целиком в видимую область.
        canvas.yview() возвращает (top_fraction, bottom_fraction); при полностью
        видимом контенте это (0.0, 1.0) — прокручивать нечего."""
        first, last = canvas.yview()
        return not (first <= 0.0 and last >= 1.0)

    def on_mousewheel(event):
        canvas = canvas_ref()
        if canvas and _needs_scroll(canvas):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def on_button4(event):
        canvas = canvas_ref()
        if canvas and _needs_scroll(canvas):
            canvas.yview_scroll(-1, "units")

    def on_button5(event):
        canvas = canvas_ref()
        if canvas and _needs_scroll(canvas):
            canvas.yview_scroll(1, "units")
    
    widget.bind("<MouseWheel>", on_mousewheel)
    widget.bind("<Button-4>", on_button4)
    widget.bind("<Button-5>", on_button5)
    
    for child in widget.winfo_children():
        bind_mousewheel_to_children(child)


def update_legend():
    """
    Построение/перестройка легенды с чекбоксами.
    Реализует полную очистку памяти перед пересозданием виджетов.
    """
    global _outline_var, _event_bindings
    cfg.hovered_tool = None
    cfg.solo_tool = None
    _outline_var = None
    _event_bindings.clear()

    legend_frame = cfg.get_widget("legend_frame")
    
    # Явная отписка от событий и отмена регистрации перед уничтожением
    # для предотвращения утечки памяти
    for widget in legend_frame.winfo_children():
        _unregister_widget_recursive(widget)
        widget.destroy()
    
    # Принудительная сборка мусора для освобождения памяти (опционально)
    # import gc
    # gc.collect()
    colors = cfg.HOLE_COLORS
    slot_colors = cfg.SLOT_COLORS

    def make_context_menu(event):
        menu = tk.Menu(cfg.get_widget("root"), tearoff=0)
        menu.add_command(label=t("legend.menu.show_all"),
                         command=lambda: legend_show_all())
        menu.add_command(label=t("legend.menu.hide_all"),
                         command=lambda: legend_hide_all())
        menu.add_separator()
        menu.add_command(label=t("legend.menu.cancel_solo"),
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
                for tk, d in cfg.current_tools.items():
                    vis = (tool_type == 'holes' and tk == tool)
                    d['visible'] = vis
                    if d['var']:
                        d['var'].set(vis)
            if cfg.slot_tools:
                for tk, d in cfg.slot_tools.items():
                    vis = (tool_type == 'slots' and tk == tool)
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
        cfg.register_themed_widget(frame, bg="panel_bg")

        var = tk.BooleanVar(value=data['visible'])
        data['var'] = var
        cb = tk.Checkbutton(frame, variable=var,
                            command=lambda t=tool, tt=tool_type: toggle_tool_visibility(t, tt))
        cb.pack(side="left")
        cfg.register_themed_widget(cb, bg="panel_bg", fg="panel_fg", selectcolor="entry_bg")

        solo_btn = tk.Label(frame, text="👁", font=("Arial", 9), cursor="hand2",
                            relief="flat", padx=2)
        solo_btn.pack(side="left")
        solo_btn.bind("<Button-1>",
                      lambda e, t=tool, tt=tool_type: on_solo_click(t, tt))
        cfg.register_themed_widget(solo_btn, bg="panel_bg", fg="panel_fg")

        icon_lbl = tk.Label(frame, text=icon_text, fg=color, font=("Arial", 12))
        icon_lbl.pack(side="left")
        cfg.register_themed_widget(icon_lbl, bg="panel_bg")
        lbl = tk.Label(frame, text=label_text, font=("Arial", 9))
        lbl.pack(side="left")
        cfg.register_themed_widget(lbl, bg="panel_bg", fg="panel_fg")

        for w in [frame, cb, solo_btn, lbl]:
            w.bind("<Enter>", lambda e, t=tool, tt=tool_type: on_row_enter(e, t, tt))
            w.bind("<Leave>", lambda e, t=tool, tt=tool_type: on_row_leave(e, t, tt))
            w.bind("<Button-3>", make_context_menu)

        return frame

    legend_frame.bind("<Button-3>", make_context_menu)

    if cfg.current_tools:
        hdr = tk.Label(legend_frame, text=t("legend.section.holes"),
                       font=("Arial", 9, "bold"))
        hdr.pack(anchor="w")
        cfg.register_themed_widget(hdr, bg="panel_bg", fg="panel_fg")
        hdr.bind("<Button-3>", make_context_menu)
        for i, (tool, data) in enumerate(cfg.current_tools.items()):
            color = colors[i % len(colors)]
            text = t("legend.row.holes", tool=tool, diameter=data['diameter'], count=len(data['holes']))
            _build_row(legend_frame, tool, data, color, "●", text, 'holes')

    if cfg.slot_tools:
        sp = tk.Label(legend_frame, text="")
        sp.pack()
        cfg.register_themed_widget(sp, bg="panel_bg")
        sp.bind("<Button-3>", make_context_menu)
        hdr2 = tk.Label(legend_frame, text=t("legend.section.slots"),
                        font=("Arial", 9, "bold"))
        hdr2.pack(anchor="w")
        cfg.register_themed_widget(hdr2, bg="panel_bg", fg="panel_fg")
        hdr2.bind("<Button-3>", make_context_menu)
        for i, (tool, data) in enumerate(cfg.slot_tools.items()):
            color = slot_colors[i % len(slot_colors)]
            text = t("legend.row.slots", tool=tool, diameter=data['diameter'], count=len(data['slots']))
            _build_row(legend_frame, tool, data, color, "━", text, 'slots')

    # Контур платы (Gerber outline) — если загружен
    if cfg.board_outline:
        sp3 = tk.Label(legend_frame, text="")
        sp3.pack()
        cfg.register_themed_widget(sp3, bg="panel_bg")
        sp3.bind("<Button-3>", make_context_menu)
        hdr3 = tk.Label(legend_frame, text=t("legend.section.outline"),
                        font=("Arial", 9, "bold"))
        hdr3.pack(anchor="w")
        cfg.register_themed_widget(hdr3, bg="panel_bg", fg="panel_fg")
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
        text = t("legend.row.outline", diameter=outline_d, n_tabs=n_tabs)
        _build_row(legend_frame, 'outline', outline_data,
                   "#444444", "▭", text, 'outline')
        # Запоминаем созданную переменную для toggle_tool_visibility
        _outline_var = outline_data['var']

    if cfg.current_tools or cfg.slot_tools or cfg.board_outline:
        sp2 = tk.Label(legend_frame, text="")
        sp2.pack()
        cfg.register_themed_widget(sp2, bg="panel_bg")
        sp2.bind("<Button-3>", make_context_menu)
        total_holes = sum(len(d['holes']) for d in cfg.current_tools.values()) if cfg.current_tools else 0
        total_slots = sum(len(d['slots']) for d in cfg.slot_tools.values()) if cfg.slot_tools else 0
        ft = tk.Label(legend_frame,
                      text=t("legend.total", holes=total_holes, slots=total_slots),
                      font=("Arial", 9, "bold"))
        ft.pack(anchor="w")
        cfg.register_themed_widget(ft, bg="panel_bg", fg="panel_fg")
        ft.bind("<Button-3>", make_context_menu)

    def _refresh_legend_highlight():
        for key, frame in legend_rows.items():
            is_solo_active = cfg.solo_tool is not None
            is_this_solo = (cfg.solo_tool == key)
            is_hovered = (cfg.hovered_tool == key)

            if is_hovered and not is_solo_active:
                bg = cfg.get_color("highlight_hover")
            elif is_this_solo:
                bg = cfg.get_color("highlight_solo")
            elif is_solo_active and not is_this_solo:
                bg = cfg.get_color("highlight_inactive")
            else:
                bg = frame.master.cget("bg") if frame.master else cfg.get_color("panel_bg")

            frame.config(bg=bg)
            for w in frame.winfo_children():
                try:
                    w.config(bg=bg)
                except Exception as e:
                    logger.exception("Failed to update legend widget background: %s", e)

    # Применить начальную подсветку
    _refresh_legend_highlight()
    
    # Привязка прокрутки
    legend_canvas = cfg.get_widget("legend_canvas")
    if legend_canvas:
        bind_mousewheel_to_children(legend_frame)
