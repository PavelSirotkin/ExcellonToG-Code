"""
Окно справки с навигацией по разделам.
"""
import tkinter as tk
from tkinter import ttk, messagebox
from docs.help_content import HELP_SECTIONS


class HelpWindow:
    """Окно справки с древовидной навигацией и форматированным содержимым."""
    
    def __init__(self, parent, initial_section=None):
        self.window = tk.Toplevel(parent)
        self.window.title("Справка — ExcellonToG-Code")
        self.window.geometry("950x700")
        self.window.minsize(800, 600)
        
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
        
        # Центрирование окна
        self.window.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() - self.window.winfo_width()) // 2
        y = parent.winfo_y() + (parent.winfo_height() - self.window.winfo_height()) // 2
        self.window.geometry(f"+{x}+{y}")
    
    def _create_ui(self):
        """Создание интерфейса окна справки."""
        # Toolbar
        toolbar = tk.Frame(self.window, relief="raised", bd=1)
        toolbar.pack(fill="x", padx=2, pady=2)
        
        self.btn_back = tk.Button(toolbar, text="◀ Назад", 
                                   command=self.go_back, state="disabled", width=8)
        self.btn_back.pack(side="left", padx=2)
        
        self.btn_forward = tk.Button(toolbar, text="▶ Вперёд",
                                      command=self.go_forward, state="disabled", width=8)
        self.btn_forward.pack(side="left", padx=2)
        
        tk.Label(toolbar, text="Поиск:").pack(side="left", padx=(20, 5))
        self.search_var = tk.StringVar()
        self.search_entry = tk.Entry(toolbar, textvariable=self.search_var, width=30)
        self.search_entry.pack(side="left")
        self.search_entry.bind("<Return>", lambda e: self.search())
        
        tk.Button(toolbar, text="🔍", command=self.search, width=3).pack(side="left", padx=2)
        
        # Main container
        main_paned = tk.PanedWindow(self.window, orient="horizontal", sashwidth=5)
        main_paned.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Left panel - tree
        left_frame = tk.Frame(main_paned, width=250)
        
        tk.Label(left_frame, text="📖 Разделы", font=("Arial", 10, "bold")).pack(pady=5)
        
        tree_frame = tk.Frame(left_frame)
        tree_frame.pack(fill="both", expand=True)
        
        self.tree = ttk.Treeview(tree_frame, show="tree")
        tree_scroll = tk.Scrollbar(tree_frame, command=self.tree.yview)
        self.tree.configure(yscrollcommand=tree_scroll.set)
        self.tree.pack(side="left", fill="both", expand=True)
        tree_scroll.pack(side="right", fill="y")
        
        self.tree.bind("<<TreeviewSelect>>", self._on_tree_select)
        
        # Right panel - content
        right_frame = tk.Frame(main_paned)
        
        self.content_text = tk.Text(right_frame, wrap="word", padx=15, pady=15,
                                    font=("Arial", 10), state="disabled")
        content_scroll = tk.Scrollbar(right_frame, command=self.content_text.yview)
        self.content_text.configure(yscrollcommand=content_scroll.set)
        self.content_text.pack(side="left", fill="both", expand=True)
        content_scroll.pack(side="right", fill="y")
        
        # Настройка тегов форматирования
        self._configure_text_tags()
        
        main_paned.add(left_frame)
        main_paned.add(right_frame)
        
        # Bottom buttons
        bottom_frame = tk.Frame(self.window)
        bottom_frame.pack(fill="x", padx=5, pady=5)
        
        tk.Button(bottom_frame, text="Закрыть", width=12,
                  command=self.window.destroy).pack(side="right")
    
    def _configure_text_tags(self):
        """Настройка стилей текста."""
        self.content_text.tag_configure("title", 
            font=("Arial", 18, "bold"), foreground="#1a5490", spacing1=5, spacing3=10)
        self.content_text.tag_configure("h2",
            font=("Arial", 14, "bold"), foreground="#2c5f8d", spacing1=15, spacing3=5)
        self.content_text.tag_configure("h3",
            font=("Arial", 12, "bold"), foreground="#3d6fa3", spacing1=10, spacing3=3)
        self.content_text.tag_configure("code",
            font=("Courier New", 9), background="#f5f5f5", foreground="#d63384")
        self.content_text.tag_configure("important",
            font=("Arial", 10, "bold"), foreground="#dc3545")
        self.content_text.tag_configure("tip",
            font=("Arial", 10), foreground="#0d6efd", background="#e7f3ff",
            lmargin1=10, lmargin2=10, rmargin=10, spacing1=5, spacing3=5)
        self.content_text.tag_configure("warning",
            font=("Arial", 10), foreground="#856404", background="#fff3cd",
            lmargin1=10, lmargin2=10, rmargin=10, spacing1=5, spacing3=5)
        self.content_text.tag_configure("bullet",
            lmargin1=20, lmargin2=35)
    
    def _populate_tree(self):
        """Заполнение дерева разделов."""
        # Группировка разделов по категориям
        categories = {
            "Начало работы": ["quick_start"],
            "Форматы файлов": ["excellon_format", "slot_format", "gerber_format", "coord_formats"],
            "Параметры G-code": ["param_safe_z", "param_drill_z", "param_feed_rate", 
                                 "param_mill_feed", "param_rapid_rate", "param_park_z"],
            "Режимы работы": ["mode_simple", "mode_pro", "tool_database"],
            "Обрезка по контуру": ["outline_loading", "outline_params", "outline_tabs", "outline_direction"],
            "Визуализация": ["viz_overview", "viz_player", "viz_legend", "viz_filters"],
            "Управление": ["ui_navigation", "ui_zoom", "ui_tooltips", "ui_hotkeys"],
            "Генерация G-code": ["gen_drilling", "gen_milling", "gen_outline", "gen_combined"],
            "Оптимизация": ["opt_tsp", "opt_nearest", "opt_2opt"],
            "Решение проблем": ["trouble_file", "trouble_format", "trouble_gcode", "trouble_outline"],
            "Советы": ["tips_materials", "tips_double", "tips_time"],
            "О программе": ["about_version", "about_author", "about_requirements"],
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
            self.content_text.insert("end", "Содержимое этого раздела находится в разработке.\n\n")
            self.content_text.insert("end", "Основная информация доступна в README.md проекта.", "tip")
        
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
            self.content_text.insert("end", "Содержимое этого раздела находится в разработке.")
        
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
            messagebox.showinfo("Поиск", "Введите текст для поиска", parent=self.window)
            return
        
        # Поиск по всем разделам
        results = []
        for section_id, section_data in HELP_SECTIONS.items():
            # Поиск в заголовке
            if query in section_data["title"].lower():
                results.append((section_id, section_data["title"], "в заголовке"))
                continue
            
            # Поиск в содержимом
            for block in section_data["content"]:
                if query in block["text"].lower():
                    results.append((section_id, section_data["title"], "в содержимом"))
                    break
        
        if results:
            # Показать первый результат
            self._show_section(results[0][0])
            
            # Сообщение о количестве результатов
            if len(results) > 1:
                messagebox.showinfo("Поиск", 
                    f"Найдено результатов: {len(results)}\n\nПоказан первый результат:\n{results[0][1]}",
                    parent=self.window)
        else:
            messagebox.showinfo("Поиск", 
                f"Ничего не найдено по запросу: {query}",
                parent=self.window)


def open_help_window(parent, section=None):
    """Открыть окно справки."""
    HelpWindow(parent, section)
