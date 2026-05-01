"""
Окно справки с поиском и навигацией.
"""
import tkinter as tk
from tkinter import ttk
from ui import themed_messagebox as messagebox
from docs.help_content import HELP_SECTIONS
from core.i18n import t, register_listener, unregister_listener
import core.config as cfg


def _unregister_widget_recursive(widget):
    """Рекурсивно отменить регистрацию виджета и всех его дочерних виджетов."""
    # Сначала обработать дочерние виджеты
    for child in widget.winfo_children():
        _unregister_widget_recursive(child)
    # Затем отменить регистрацию самого виджета
    cfg.unregister_themed_widget(widget)


class HelpWindow:
    """Окно справки с древовидной навигацией и форматированным содержимым."""
    
    def __init__(self, parent, initial_section=None):
        self.window = tk.Toplevel(parent)
        self.window.title(t("help.title"))
        self.window.geometry("950x700")
        self.window.minsize(800, 600)
        
        # Применить тему к окну
        cfg.register_themed_widget(self.window, bg="panel_bg")
        
        # История навигации
        self.history = []
        self.history_pos = -1
        
        # Создание UI
        self._create_ui()
        self._populate_tree()
        
        # Открыть начальный раздел
        if initial_section and initial_section in HELP_SECTIONS:
            self._show_section(initial_section)
        else:
            self._show_section("quick_start")
        
        # Регистрация обработчика смены языка
        self._on_lang_change = self._rebuild_on_language_change
        register_listener(self._on_lang_change)
        self.window.protocol("WM_DELETE_WINDOW", self._on_close)
        
        # Центрирование окна
        self.window.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() - self.window.winfo_width()) // 2
        y = parent.winfo_y() + (parent.winfo_height() - self.window.winfo_height()) // 2
        self.window.geometry(f"+{x}+{y}")
        
        # Применить темную тему к заголовку окна (Windows)
        self.window.after(10, lambda: cfg.apply_window_theme(self.window))
    
    def _create_ui(self):
        """Создание интерфейса окна справки."""
        # Toolbar
        toolbar = tk.Frame(self.window, relief="raised", bd=1)
        cfg.register_themed_widget(toolbar, bg="panel_bg")
        toolbar.pack(fill="x", padx=2, pady=2)
        
        self.btn_back = tk.Button(toolbar, text=t("help.btn.back"), 
                                   command=self.go_back, state="disabled", width=8)
        cfg.register_themed_widget(self.btn_back, bg="btn_bg", fg="btn_fg")
        self.btn_back.pack(side="left", padx=2)
        
        self.btn_forward = tk.Button(toolbar, text=t("help.btn.forward"),
                                      command=self.go_forward, state="disabled", width=8)
        cfg.register_themed_widget(self.btn_forward, bg="btn_bg", fg="btn_fg")
        self.btn_forward.pack(side="left", padx=2)
        
        self.lbl_search = tk.Label(toolbar, text=t("help.lbl.search"))
        cfg.register_themed_widget(self.lbl_search, bg="panel_bg", fg="panel_fg")
        self.lbl_search.pack(side="left", padx=(20, 5))
        self.search_var = tk.StringVar()
        self.search_entry = tk.Entry(toolbar, textvariable=self.search_var, width=30)
        cfg.register_themed_widget(self.search_entry, bg="entry_bg", fg="entry_fg", insertbackground="entry_fg")
        self.search_entry.pack(side="left")
        self.search_entry.bind("<Return>", lambda e: self.search())
        
        btn_search = tk.Button(toolbar, text="🔍", command=self.search, width=3)
        cfg.register_themed_widget(btn_search, bg="btn_bg", fg="btn_fg")
        btn_search.pack(side="left", padx=2)
        
        # Main container
        main_paned = tk.PanedWindow(self.window, orient="horizontal", sashwidth=5)
        main_paned.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Left panel - tree
        left_frame = tk.Frame(main_paned, width=250)
        cfg.register_themed_widget(left_frame, bg="panel_bg")
        
        self.lbl_sections = tk.Label(left_frame, text=t("help.lbl.sections"), font=("Arial", 10, "bold"))
        cfg.register_themed_widget(self.lbl_sections, bg="panel_bg", fg="panel_fg")
        self.lbl_sections.pack(pady=5)
        
        tree_frame = tk.Frame(left_frame)
        cfg.register_themed_widget(tree_frame, bg="panel_bg")
        tree_frame.pack(fill="both", expand=True)
        
        # Настройка стиля для Treeview
        tree_style = ttk.Style()
        if cfg.current_theme() == "dark":
            tree_style.configure("Help.Treeview",
                                background="#2D2D2D",
                                foreground="#E0E0E0",
                                fieldbackground="#2D2D2D")
            tree_style.map("Help.Treeview",
                          background=[("selected", "#264F78")],
                          foreground=[("selected", "#E0E0E0")])
        else:
            tree_style.configure("Help.Treeview",
                                background="#FFFFFF",
                                foreground="#1A1A1A",
                                fieldbackground="#FFFFFF")
            tree_style.map("Help.Treeview",
                          background=[("selected", "#B3CCE8")],
                          foreground=[("selected", "#1A1A1A")])
        
        self.tree = ttk.Treeview(tree_frame, show="tree", style="Help.Treeview")
        tree_scroll = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=tree_scroll.set)
        self.tree.pack(side="left", fill="both", expand=True)
        tree_scroll.pack(side="right", fill="y")
        
        self.tree.bind("<<TreeviewSelect>>", self._on_tree_select)
        
        # Right panel - content
        right_frame = tk.Frame(main_paned)
        cfg.register_themed_widget(right_frame, bg="panel_bg")
        
        self.content_text = tk.Text(right_frame, wrap="word", padx=15, pady=15,
                                    font=("Arial", 10), state="disabled")
        cfg.register_themed_widget(self.content_text, bg="entry_bg", fg="entry_fg")
        content_scroll = ttk.Scrollbar(right_frame, orient="vertical", command=self.content_text.yview)
        self.content_text.configure(yscrollcommand=content_scroll.set)
        self.content_text.pack(side="left", fill="both", expand=True)
        content_scroll.pack(side="right", fill="y")
        
        # Настройка тегов форматирования
        self._configure_text_tags()
        
        main_paned.add(left_frame)
        main_paned.add(right_frame)
        
        # Bottom buttons
        bottom_frame = tk.Frame(self.window)
        cfg.register_themed_widget(bottom_frame, bg="panel_bg")
        bottom_frame.pack(fill="x", padx=5, pady=5)
        
        self.btn_close = tk.Button(bottom_frame, text=t("help.btn.close"), width=12,
                                    command=self.window.destroy)
        cfg.register_themed_widget(self.btn_close, bg="btn_bg", fg="btn_fg")
        self.btn_close.pack(side="right")
    
    def _configure_text_tags(self):
        """Настройка стилей текста."""
        # Цвета зависят от темы
        if cfg.current_theme() == "dark":
            title_fg = "#5B9BD5"
            h2_fg = "#4A8BC2"
            h3_fg = "#3D7AB3"
            code_bg = "#2D2D2D"
            code_fg = "#E06C75"
            important_fg = "#E74C3C"
            tip_fg = "#5B9BD5"
            tip_bg = "#1E3A5F"
            warning_fg = "#E67E22"
            warning_bg = "#3A2F1F"
        else:
            title_fg = "#1a5490"
            h2_fg = "#2c5f8d"
            h3_fg = "#3d6fa3"
            code_bg = "#f5f5f5"
            code_fg = "#d63384"
            important_fg = "#dc3545"
            tip_fg = "#0d6efd"
            tip_bg = "#e7f3ff"
            warning_fg = "#856404"
            warning_bg = "#fff3cd"
        
        self.content_text.tag_configure("title", 
            font=("Arial", 18, "bold"), foreground=title_fg, spacing1=5, spacing3=10)
        self.content_text.tag_configure("h2",
            font=("Arial", 14, "bold"), foreground=h2_fg, spacing1=15, spacing3=5)
        self.content_text.tag_configure("h3",
            font=("Arial", 12, "bold"), foreground=h3_fg, spacing1=10, spacing3=3)
        self.content_text.tag_configure("code",
            font=("Courier New", 9), background=code_bg, foreground=code_fg)
        self.content_text.tag_configure("important",
            font=("Arial", 10, "bold"), foreground=important_fg)
        self.content_text.tag_configure("tip",
            font=("Arial", 10), foreground=tip_fg, background=tip_bg,
            lmargin1=10, lmargin2=10, rmargin=10, spacing1=5, spacing3=5)
        self.content_text.tag_configure("warning",
            font=("Arial", 10), foreground=warning_fg, background=warning_bg,
            lmargin1=10, lmargin2=10, rmargin=10, spacing1=5, spacing3=5)
        self.content_text.tag_configure("bullet",
            lmargin1=20, lmargin2=35)
    
    def _populate_tree(self):
        """Заполнение дерева разделов."""
        # Группировка разделов по категориям
        categories = {
            t("help.cat.start"): ["quick_start"],
            t("help.cat.formats"): ["excellon_format", "slot_format", "gerber_format", "coord_formats"],
            t("help.cat.params"): ["param_safe_z", "param_drill_z", "param_feed_rate", 
                                   "param_mill_feed", "param_rapid_rate", "param_park_z"],
            t("help.cat.modes"): ["mode_simple", "mode_pro", "tool_database"],
            t("help.cat.outline"): ["outline_loading", "outline_params", "outline_tabs", "outline_direction"],
            t("help.cat.viz"): ["viz_overview", "viz_player", "viz_legend", "viz_filters", "viz_statistics", "viz_themes", "viz_localization"],
            t("help.cat.controls"): ["ui_navigation", "ui_zoom", "ui_tooltips", "ui_hotkeys"],
            t("help.cat.gen"): ["gen_drilling", "gen_milling", "gen_outline", "gen_combined"],
            t("help.cat.opt"): ["opt_tsp", "opt_nearest", "opt_2opt"],
            t("help.cat.trouble"): ["trouble_file", "trouble_format", "trouble_gcode", "trouble_outline"],
            t("help.cat.tips"): ["tips_materials", "tips_time"],
            t("help.cat.about"): ["about_version", "about_author", "about_requirements"],
        }
        
        for category, section_ids in categories.items():
            parent_id = self.tree.insert("", "end", text=f"▼ {category}", open=True)
            
            for section_id in section_ids:
                if section_id in HELP_SECTIONS:
                    section_data = HELP_SECTIONS[section_id]
                    self.tree.insert(parent_id, "end",
                        text=f"  {section_data['title']}", values=(section_id,))
    
    def _on_tree_select(self, event):
        """Обработка выбора раздела в дереве."""
        selection = self.tree.selection()
        if not selection:
            return
        
        item = selection[0]
        values = self.tree.item(item, "values")
        if values:
            section_id = values[0]
            self._show_section(section_id)
    
    def _show_section(self, section_id):
        """Отображение содержимого раздела."""
        if section_id not in HELP_SECTIONS:
            return
        
        # Добавить в историю
        if self.history_pos < len(self.history) - 1:
            self.history = self.history[:self.history_pos + 1]
        
        # Не добавлять дубликаты подряд
        if not self.history or self.history[-1] != section_id:
            self.history.append(section_id)
            self.history_pos = len(self.history) - 1
        
        self._update_nav_buttons()
        
        # Отобразить содержимое
        section = HELP_SECTIONS[section_id]
        self.content_text.configure(state="normal")
        self.content_text.delete("1.0", "end")
        
        # Рендеринг содержимого
        if section["content"]:
            self._render_content(section["content"])
        else:
            self.content_text.insert("end", section["title"] + "\n\n", "title")
            self.content_text.insert("end", t("help.placeholder.in_progress"))
            self.content_text.insert("end", t("help.placeholder.see_readme"), "tip")
        
        self.content_text.configure(state="disabled")
        self.content_text.see("1.0")
    
    def _show_section_no_history(self, section_id):
        """Показать раздел без добавления в историю (для навигации назад/вперёд)."""
        if section_id not in HELP_SECTIONS:
            return
        
        section = HELP_SECTIONS[section_id]
        self.content_text.configure(state="normal")
        self.content_text.delete("1.0", "end")
        
        if section["content"]:
            self._render_content(section["content"])
        else:
            self.content_text.insert("end", section["title"] + "\n\n", "title")
            self.content_text.insert("end", t("help.placeholder.in_progress_short"))
        
        self.content_text.configure(state="disabled")
        self.content_text.see("1.0")
    
    def _render_content(self, content):
        """Рендеринг форматированного содержимого."""
        for block in content:
            block_type = block["type"]
            text = block["text"]
            
            if block_type == "title":
                self.content_text.insert("end", text + "\n", "title")
            elif block_type == "h2":
                self.content_text.insert("end", text + "\n", "h2")
            elif block_type == "h3":
                self.content_text.insert("end", text + "\n", "h3")
            elif block_type == "paragraph":
                self.content_text.insert("end", text + "\n\n")
            elif block_type == "code":
                self.content_text.insert("end", "  " + text + "\n\n", "code")
            elif block_type == "tip":
                self.content_text.insert("end", f"💡 {text}\n\n", "tip")
            elif block_type == "warning":
                self.content_text.insert("end", f"⚠️ {text}\n\n", "warning")
            elif block_type == "bullet":
                self.content_text.insert("end", f"• {text}\n", "bullet")
    
    def go_back(self):
        """Назад по истории."""
        if self.history_pos > 0:
            self.history_pos -= 1
            section_id = self.history[self.history_pos]
            self._show_section_no_history(section_id)
            self._update_nav_buttons()
    
    def go_forward(self):
        """Вперёд по истории."""
        if self.history_pos < len(self.history) - 1:
            self.history_pos += 1
            section_id = self.history[self.history_pos]
            self._show_section_no_history(section_id)
            self._update_nav_buttons()
    
    def _update_nav_buttons(self):
        """Обновление состояния кнопок навигации."""
        self.btn_back.configure(
            state="normal" if self.history_pos > 0 else "disabled")
        self.btn_forward.configure(
            state="normal" if self.history_pos < len(self.history) - 1 else "disabled")
    
    def search(self):
        """Поиск по содержимому справки."""
        query = self.search_var.get().strip().lower()
        if not query:
            messagebox.showinfo(t("help.search.found.title"), t("help.search.empty"), parent=self.window)
            return
        
        # Поиск по всем разделам
        results = []
        for section_id, section_data in HELP_SECTIONS.items():
            # Поиск в заголовке
            if query in section_data["title"].lower():
                results.append((section_id, section_data["title"]))
                continue

            # Поиск в содержимом
            for block in section_data["content"]:
                if query in block["text"].lower():
                    results.append((section_id, section_data["title"]))
                    break
        
        if results:
            # Показать первый результат
            self._show_section(results[0][0])
            
            # Сообщение о количестве результатов
            if len(results) > 1:
                messagebox.showinfo(t("help.search.found.title"), 
                    t("help.search.found.msg", count=len(results), title=results[0][1]),
                    parent=self.window)
        else:
            messagebox.showinfo(t("help.search.found.title"), 
                t("help.search.not_found", query=query),
                parent=self.window)
    
    def _rebuild_on_language_change(self):
        """При смене языка перестроить дерево и перерендерить текущий раздел."""
        if not self.window.winfo_exists():
            return
        
        # Обновить заголовок окна
        self.window.title(t("help.title"))
        
        # Обновить UI-элементы
        self.btn_back.configure(text=t("help.btn.back"))
        self.btn_forward.configure(text=t("help.btn.forward"))
        self.lbl_search.configure(text=t("help.lbl.search"))
        self.lbl_sections.configure(text=t("help.lbl.sections"))
        self.btn_close.configure(text=t("help.btn.close"))
        
        # Перестроить дерево с новыми именами категорий
        for item in self.tree.get_children():
            self.tree.delete(item)
        self._populate_tree()
        
        # Перерендерить текущий раздел (HELP_SECTIONS вернёт уже на новом языке)
        if self.history and 0 <= self.history_pos < len(self.history):
            self._show_section_no_history(self.history[self.history_pos])
    
    def _on_close(self):
        """Обработчик закрытия окна."""
        unregister_listener(self._on_lang_change)
        _unregister_widget_recursive(self.window)
        self.window.destroy()


def open_help_window(parent, section=None):
    """Открыть окно справки."""
    HelpWindow(parent, section)
