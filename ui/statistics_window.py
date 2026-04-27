"""
Улучшенное окно статистики с визуальным представлением данных.
"""
import logging
import math
import tkinter as tk
from tkinter import ttk, messagebox
import core.config as cfg
from core.polygon_ops import segment_length

logger = logging.getLogger(__name__)


class StatisticsWindow:
    """Окно статистики проекта."""
    
    def __init__(self, parent):
        self.window = tk.Toplevel(parent)
        self.window.title("📊 Статистика проекта")
        self.window.geometry("500x700")
        self.window.resizable(True, True)
        self.window.minsize(500, 500)
        self.window.transient(parent)
        self.window.grab_set()
        
        # Собираем данные
        self.collect_data()
        
        # Создаём canvas с прокруткой
        canvas = tk.Canvas(self.window, bg="#F5F5F5", highlightthickness=0)
        scrollbar = tk.Scrollbar(self.window, orient="vertical", command=canvas.yview)
        
        # Основной контейнер внутри canvas
        main_frame = tk.Frame(canvas, bg="#F5F5F5")
        
        # Создаём интерфейс
        self.create_header(main_frame)
        self.create_board_info(main_frame)
        self.create_tools_info(main_frame)
        self.create_path_info(main_frame)
        self.create_time_info(main_frame)
        self.create_buttons(main_frame)
        
        # Настройка прокрутки
        canvas.create_window((0, 0), window=main_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Обновление области прокрутки
        main_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        
        # Упаковка элементов
        canvas.pack(side="left", fill="both", expand=True, padx=10, pady=10)
        scrollbar.pack(side="right", fill="y", pady=10, padx=(0, 10))
        
        # Прокрутка колесом мыши
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        
        canvas.bind_all("<MouseWheel>", _on_mousewheel)
        self.window.protocol("WM_DELETE_WINDOW", lambda: self._on_close(canvas))
        
        # Центрирование окна
        self.center_window(parent)
    
    def _on_close(self, canvas):
        """Обработка закрытия окна."""
        canvas.unbind_all("<MouseWheel>")
        self.window.destroy()
    
    def collect_data(self):
        """Собрать все данные для статистики."""
        self.all_points = []
        self.total_holes = 0
        self.total_slots = 0
        self.drill_tools_count = 0
        self.slot_tools_count = 0
        self.outline_tools_count = 0
        self.total_board_outline = 0
        self.tool_data = []

        # Данные по отверстиям
        if cfg.current_tools:
            for tool, data in sorted(cfg.current_tools.items()):
                if not data['visible']:
                    continue
                count = len(data['holes'])
                self.total_holes += count
                self.drill_tools_count += 1
                self.tool_data.append({
                    'num': tool,
                    'type': 'Сверло',
                    'diameter': data['diameter'],
                    'count': count
                })
                self.all_points.extend(data['holes'])

        # Данные по слотам
        if cfg.slot_tools:
            for tool, data in sorted(cfg.slot_tools.items()):
                if not data['visible']:
                    continue
                count = 1  # Слот — это одно движение (фреза проходит один раз)
                self.total_slots += count
                self.slot_tools_count += 1
                self.tool_data.append({
                    'num': tool,
                    'type': 'Фреза',
                    'diameter': data['diameter'],
                    'count': count
                })
                for start, end in data['slots']:
                    self.all_points.append(start)
                    self.all_points.append(end)

        # Данные по контуру платы (ОДНА фреза для всего контура)
        if cfg.board_outline and cfg.board_outline_visible:
            try:
                # Получаем диаметр фрез для контура
                outline_diameter = cfg.get_param("outline_tool_diameter")
                # Контур — это один инструмент, который фрезерует весь путь
                if outline_diameter > 0:
                    self.outline_tools_count += 1
                    self.total_board_outline = 1
                    self.tool_data.append({
                        'num': 'контур',
                        'type': 'Фреза',
                        'diameter': outline_diameter,
                        'count': 1  # ОДНА фреза для всего контура
                    })
                    # Добавляем точки контура для расчёта размеров платы
                    # Gerber parser использует 'p1'/'p2' для линий и 'start'/'end' для дуг
                    for segment in cfg.board_outline:
                        # Линии: p1, p2; дуги: start, end
                        p1 = segment.get('p1') or segment.get('start')
                        p2 = segment.get('p2') or segment.get('end')
                        if p1:
                            self.all_points.append(p1)
                        if p2:
                            self.all_points.append(p2)
            except (ValueError, KeyError, TypeError) as e:
                # Параметр контура недоступен или повреждён — статистику считаем без него
                logger.warning("Не удалось обработать контур платы для статистики: %s", e)
        
        # Размеры платы
        if self.all_points:
            self.min_x = min(p[0] for p in self.all_points)
            self.max_x = max(p[0] for p in self.all_points)
            self.min_y = min(p[1] for p in self.all_points)
            self.max_y = max(p[1] for p in self.all_points)
            self.board_w = self.max_x - self.min_x
            self.board_h = self.max_y - self.min_y
            self.board_area = self.board_w * self.board_h / 100  # см²
        else:
            self.min_x = self.max_x = self.min_y = self.max_y = 0
            self.board_w = self.board_h = self.board_area = 0
        
        # Параметры обработки
        try:
            self.rapid_rate = cfg.get_param("rapid_rate")
            self.feed_rate = cfg.get_param("feed_rate")
            self.mill_feed = cfg.get_param("mill_feed")
            self.safe_z = cfg.get_param("safe_z")
            self.drill_z = cfg.get_param("drill_z")
        except ValueError:
            self.rapid_rate = self.feed_rate = self.mill_feed = 0
            self.safe_z = self.drill_z = 0
        
        # Расчёт путей и времени
        self.calculate_paths()
    
    def calculate_paths(self):
        """Рассчитать длины путей и время обработки.

        Модель rapid: после последнего отверстия/слота каждого инструмента
        головка возвращается в (0,0) при парковке (см. write_tool_parking
        в core/gcode_generator.py), поэтому добавляем "last_pos → (0,0)"
        в конце каждой группы.
        """
        self.total_rapid = 0.0
        self.total_feed = 0.0
        self.slot_feed_dist = 0.0
        z_travel_per_hole = abs(self.safe_z) + abs(self.drill_z)

        # Путь для отверстий
        if cfg.current_tools:
            for tool, data in cfg.current_tools.items():
                if not data['visible']:
                    continue
                holes = data['holes']
                if not holes:
                    continue
                # От начала координат до первого отверстия
                self.total_rapid += math.hypot(holes[0][0], holes[0][1])
                # Между отверстиями
                for i in range(1, len(holes)):
                    self.total_rapid += math.hypot(holes[i][0] - holes[i-1][0],
                                                   holes[i][1] - holes[i-1][1])
                # Возврат в (0,0) после последнего отверстия (парковка)
                self.total_rapid += math.hypot(holes[-1][0], holes[-1][1])
                # Движения по Z (вверх + вниз на каждое отверстие)
                self.total_feed += z_travel_per_hole * 2 * len(holes)

        # Путь для слотов
        if cfg.slot_tools:
            for tool, data in cfg.slot_tools.items():
                if not data['visible']:
                    continue
                slots = data['slots']
                if not slots:
                    continue
                # От начала до первого слота (start первого слота)
                self.total_rapid += math.hypot(slots[0][0][0], slots[0][0][1])
                # Между слотами: end предыдущего → start следующего
                for i in range(1, len(slots)):
                    self.total_rapid += math.hypot(slots[i][0][0] - slots[i-1][1][0],
                                                   slots[i][0][1] - slots[i-1][1][1])
                # Возврат в (0,0) после последнего слота (парковка)
                self.total_rapid += math.hypot(slots[-1][1][0], slots[-1][1][1])
                # Фрезеровка слотов (XY-резка)
                for start, end in slots:
                    self.slot_feed_dist += math.hypot(end[0] - start[0], end[1] - start[1])
                # Движения по Z (вверх + вниз на каждый слот)
                self.total_feed += z_travel_per_hole * 2 * len(slots)

        # Путь для контура платы
        self.outline_feed_dist = 0.0
        self.outline_rapid = 0.0  # Холостые перемещения между сегментами и до/после контура
        if cfg.board_outline and cfg.board_outline_visible:
            try:
                # Начальное перемещение к первому сегменту (от начала координат)
                first_seg = cfg.board_outline[0]
                first_start = (first_seg.get('p1') if first_seg.get('type') == 'line'
                               else first_seg.get('start')) or (0, 0)
                self.outline_rapid += math.hypot(first_start[0], first_start[1])

                prev_end = None
                for segment in cfg.board_outline:
                    seg_type = segment.get('type', 'line')
                    if seg_type == 'line':
                        start = segment.get('p1', (0, 0))
                        end = segment.get('p2', (0, 0))
                    else:  # arc
                        start = segment.get('start', (0, 0))
                        end = segment.get('end', (0, 0))

                    # Холостой переход с конца предыдущего сегмента к началу текущего
                    # (для замкнутого контура расстояние ≈ 0, но защищаемся от разрывов)
                    if prev_end is not None:
                        self.outline_rapid += math.hypot(start[0] - prev_end[0],
                                                         start[1] - prev_end[1])

                    # Длина фрезеровки — точная для линии и для дуги (через r и углы)
                    self.outline_feed_dist += segment_length(segment)
                    prev_end = end

                # Возврат в (0,0) после последнего сегмента контура (парковка)
                if prev_end is not None:
                    self.outline_rapid += math.hypot(prev_end[0], prev_end[1])

                # Учёт multi-pass и Z-движений для контура
                # Читаем параметры контура
                try:
                    depth_per_pass = cfg.get_param("outline_depth_per_pass")
                    n_tabs = int(cfg.get_param("outline_n_tabs"))
                    tab_height = cfg.get_param("outline_tab_height")
                except (ValueError, KeyError):
                    depth_per_pass = 0
                    n_tabs = 0
                    tab_height = 0

                # Вычисляем количество проходов (по формуле из outline_gcode.py:86-87)
                total_depth = abs(self.drill_z)
                n_passes = max(1, math.ceil(total_depth / depth_per_pass)) if depth_per_pass > 0 else 1

                # Сохраняем однопроходный периметр и умножаем на n_passes
                perimeter = self.outline_feed_dist
                self.outline_feed_dist = perimeter * n_passes

                # Считаем Z-движения для контура
                # Для каждого пасса k=1..n_passes фреза идёт от safe_z до working_z и обратно
                outline_plunge_z = 0.0  # Z вниз, plunge_feed
                outline_retract_z = 0.0  # Z вверх, rapid_rate
                for k in range(1, n_passes + 1):
                    working = min(k * depth_per_pass, total_depth)
                    outline_plunge_z += abs(self.safe_z) + working
                    outline_retract_z += abs(self.safe_z) + working

                # Tabs — только на последнем пассе, по 2 plunge'а на каждый tab
                outline_tab_z = 2 * n_tabs * tab_height

                # Распределяем по существующим бакетам времени
                self.total_feed += outline_plunge_z + outline_tab_z
                self.total_rapid += outline_retract_z

            except (KeyError, TypeError, IndexError) as e:
                # Битая структура сегментов — статистику контура считаем нулевой
                logger.warning("Не удалось рассчитать пути контура: %s", e)
                self.outline_feed_dist = 0.0
                self.outline_rapid = 0.0

        # Общая фрезеровка (слоты + контур)
        self.total_milling_dist = self.slot_feed_dist + self.outline_feed_dist

        # Объединяем rapid от контура с общим
        self.total_rapid += self.outline_rapid

        # Время обработки
        self.time_rapid = (self.total_rapid / self.rapid_rate * 60) if self.rapid_rate > 0 else 0
        self.time_drill_feed = (self.total_feed / self.feed_rate * 60) if self.feed_rate > 0 else 0
        self.time_slot_mill = (self.slot_feed_dist / self.mill_feed * 60) if self.mill_feed > 0 else 0
        self.time_outline_mill = (self.outline_feed_dist / self.mill_feed * 60) if self.mill_feed > 0 else 0
        self.time_mill_feed = self.time_slot_mill + self.time_outline_mill
        self.total_time_sec = self.time_rapid + self.time_drill_feed + self.time_mill_feed
    
    def create_header(self, parent):
        """Создать заголовок окна."""
        header = tk.Frame(parent, bg="#2C3E50", height=60)
        header.pack(fill="x", pady=(0, 10))
        header.pack_propagate(False)
        
        title = tk.Label(header, text="📊 Статистика проекта",
                        font=("Arial", 16, "bold"), fg="white", bg="#2C3E50")
        title.pack(pady=15)
    
    def create_board_info(self, parent):
        """Секция информации о плате."""
        frame = tk.LabelFrame(parent, text="  📐 Размеры платы  ",
                             font=("Arial", 10, "bold"), bg="#F5F5F5",
                             fg="#2C3E50", padx=10, pady=10)
        frame.pack(fill="x", pady=5)
        
        info_frame = tk.Frame(frame, bg="#F5F5F5")
        info_frame.pack(fill="x")
        
        # Размеры X
        self._create_info_row(info_frame, "X:", 
                             f"{self.min_x:.2f} ... {self.max_x:.2f} мм",
                             f"({self.board_w:.2f} мм)", "#3498DB")
        
        # Размеры Y
        self._create_info_row(info_frame, "Y:", 
                             f"{self.min_y:.2f} ... {self.max_y:.2f} мм",
                             f"({self.board_h:.2f} мм)", "#3498DB")
        
        # Площадь
        self._create_info_row(info_frame, "Площадь:", 
                             f"{self.board_area:.1f} см²", "", "#9B59B6")
    
    def create_tools_info(self, parent):
        """Секция информации об инструментах."""
        frame = tk.LabelFrame(parent, text="  🔧 Инструменты  ",
                             font=("Arial", 10, "bold"), bg="#F5F5F5",
                             fg="#2C3E50", padx=10, pady=10)
        frame.pack(fill="x", pady=5)
        
        # Сводка
        summary_frame = tk.Frame(frame, bg="#F5F5F5")
        summary_frame.pack(fill="x", pady=(0, 10))

        self._create_summary_box(summary_frame, "Отверстий",
                                self.total_holes, self.drill_tools_count, "#27AE60", 0)
        self._create_summary_box(summary_frame, "Слотов",
                                self.total_slots, self.slot_tools_count, "#E74C3C", 1)
        self._create_summary_box(summary_frame, "Обрезка",
                                self.total_board_outline, self.outline_tools_count, "#3498DB", 2)

        # Таблица инструментов
        if self.tool_data:
            table_frame = tk.Frame(frame, bg="white", relief="solid", borderwidth=1)
            table_frame.pack(fill="x", pady=(5, 0))
            
            # Заголовок таблицы
            header_frame = tk.Frame(table_frame, bg="#34495E")
            header_frame.pack(fill="x")
            
            tk.Label(header_frame, text="№", width=6, bg="#34495E", fg="white",
                    font=("Arial", 9, "bold")).pack(side="left", padx=2, pady=5)
            tk.Label(header_frame, text="Тип", width=10, bg="#34495E", fg="white",
                    font=("Arial", 9, "bold")).pack(side="left", padx=2, pady=5)
            tk.Label(header_frame, text="Диаметр", width=12, bg="#34495E", fg="white",
                    font=("Arial", 9, "bold")).pack(side="left", padx=2, pady=5)
            tk.Label(header_frame, text="Количество", width=12, bg="#34495E", fg="white",
                    font=("Arial", 9, "bold")).pack(side="left", padx=2, pady=5)
            
            # Строки таблицы
            for i, tool in enumerate(self.tool_data):
                bg_color = "#ECF0F1" if i % 2 == 0 else "white"
                row_frame = tk.Frame(table_frame, bg=bg_color)
                row_frame.pack(fill="x")
                
                tk.Label(row_frame, text=f"T{tool['num']}", width=6, bg=bg_color,
                        font=("Arial", 9), anchor="w").pack(side="left", padx=2, pady=3)
                tk.Label(row_frame, text=tool['type'], width=10, bg=bg_color,
                        font=("Arial", 9), anchor="w").pack(side="left", padx=2, pady=3)
                tk.Label(row_frame, text=f"⌀ {tool['diameter']:.2f} мм", width=12, bg=bg_color,
                        font=("Arial", 9), anchor="w").pack(side="left", padx=2, pady=3)
                tk.Label(row_frame, text=str(tool['count']), width=12, bg=bg_color,
                        font=("Arial", 9), anchor="w").pack(side="left", padx=2, pady=3)
    
    def create_path_info(self, parent):
        """Секция информации о путях."""
        frame = tk.LabelFrame(parent, text="  🛤️ Путь инструмента  ",
                             font=("Arial", 10, "bold"), bg="#F5F5F5",
                             fg="#2C3E50", padx=10, pady=10)
        frame.pack(fill="x", pady=5)
        
        info_frame = tk.Frame(frame, bg="#F5F5F5")
        info_frame.pack(fill="x")
        
        self._create_info_row(info_frame, "Быстрый ход (XY):",
                             f"{self.total_rapid:.1f} мм",
                             f"({self.total_rapid/1000:.2f} м)", "#3498DB")

        self._create_info_row(info_frame, "Рабочий ход (Z):",
                             f"{self.total_feed:.1f} мм",
                             f"({self.total_feed/1000:.2f} м)", "#27AE60")

        # Информация о фрезеровке (слоты + контур)
        if self.total_milling_dist > 0:
            if self.slot_feed_dist > 0:
                self._create_info_row(info_frame, "Фрезеровка слотов:",
                                     f"{self.slot_feed_dist:.1f} мм",
                                     f"({self.slot_feed_dist/1000:.2f} м)", "#E74C3C")

            if self.outline_feed_dist > 0:
                self._create_info_row(info_frame, "Фрезеровка по контуру:",
                                     f"{self.outline_feed_dist:.1f} мм",
                                     f"({self.outline_feed_dist/1000:.2f} м)", "#FF6B6B")

            # Сумма всех путей фрезеровки
            self._create_info_row(info_frame, "Фрезеровка (всего):",
                                 f"{self.total_milling_dist:.1f} мм",
                                 f"({self.total_milling_dist/1000:.2f} м)", "#E74C3C")

        total_path = self.total_rapid + self.total_feed + self.total_milling_dist
        self._create_info_row(info_frame, "Общий путь:", 
                             f"{total_path:.1f} мм",
                             f"({total_path/1000:.2f} м)", "#9B59B6")
    
    def create_time_info(self, parent):
        """Секция информации о времени."""
        frame = tk.LabelFrame(parent, text="  ⏱️ Время обработки  ",
                             font=("Arial", 10, "bold"), bg="#F5F5F5",
                             fg="#2C3E50", padx=10, pady=10)
        frame.pack(fill="x", pady=5)
        
        # Общее время
        minutes = int(self.total_time_sec // 60)
        seconds = int(self.total_time_sec % 60)
        
        total_frame = tk.Frame(frame, bg="#2C3E50", relief="solid", borderwidth=2)
        total_frame.pack(fill="x", pady=(0, 10))
        
        tk.Label(total_frame, text=f"⏱️ {minutes} мин {seconds} сек",
                font=("Arial", 14, "bold"), fg="white", bg="#2C3E50",
                pady=10).pack()
        
        # Детализация
        detail_frame = tk.Frame(frame, bg="#F5F5F5")
        detail_frame.pack(fill="x")
        
        if self.total_time_sec > 0:
            rapid_pct = (self.time_rapid / self.total_time_sec) * 100
            drill_pct = (self.time_drill_feed / self.total_time_sec) * 100
            mill_pct = (self.time_mill_feed / self.total_time_sec) * 100
            
            self._create_time_bar(detail_frame, "Быстрый ход:", 
                                 self.time_rapid, rapid_pct, "#3498DB")
            self._create_time_bar(detail_frame, "Сверление:", 
                                 self.time_drill_feed, drill_pct, "#27AE60")
            if self.time_mill_feed > 0:
                self._create_time_bar(detail_frame, "Фрезеровка:", 
                                     self.time_mill_feed, mill_pct, "#E74C3C")
    
    def create_buttons(self, parent):
        """Создать кнопки управления."""
        btn_frame = tk.Frame(parent, bg="#F5F5F5")
        btn_frame.pack(fill="x", pady=(10, 0))
        
        tk.Button(btn_frame, text="📋 Копировать", width=15,
                 command=self.copy_to_clipboard, bg="#3498DB", fg="white",
                 font=("Arial", 10, "bold"), relief="flat", cursor="hand2",
                 pady=8).pack(side="left", padx=5)
        
        tk.Button(btn_frame, text="✖ Закрыть", width=15,
                 command=self.window.destroy, bg="#95A5A6", fg="white",
                 font=("Arial", 10, "bold"), relief="flat", cursor="hand2",
                 pady=8).pack(side="right", padx=5)
    
    def _create_info_row(self, parent, label, value, extra, color):
        """Создать строку информации."""
        row = tk.Frame(parent, bg="#F5F5F5")
        row.pack(fill="x", pady=2)
        
        tk.Label(row, text=label, width=20, anchor="w", bg="#F5F5F5",
                font=("Arial", 9)).pack(side="left")
        tk.Label(row, text=value, anchor="w", bg="#F5F5F5",
                font=("Arial", 9, "bold"), fg=color).pack(side="left")
        if extra:
            tk.Label(row, text=f"  {extra}", anchor="w", bg="#F5F5F5",
                    font=("Arial", 8), fg="#7F8C8D").pack(side="left")
    
    def _create_summary_box(self, parent, title, count, tools, color, col):
        """Создать блок сводки."""
        box = tk.Frame(parent, bg=color, relief="solid", borderwidth=2)
        box.grid(row=0, column=col, padx=10, pady=5, sticky="ew")
        parent.grid_columnconfigure(col, weight=1)
        
        tk.Label(box, text=title, bg=color, fg="white",
                font=("Arial", 9)).pack(pady=(8, 2))
        tk.Label(box, text=str(count), bg=color, fg="white",
                font=("Arial", 18, "bold")).pack()
        tk.Label(box, text=f"({tools} инстр.)", bg=color, fg="white",
                font=("Arial", 8)).pack(pady=(2, 8))
    
    def _create_time_bar(self, parent, label, time_sec, percent, color):
        """Создать строку с прогресс-баром времени."""
        row = tk.Frame(parent, bg="#F5F5F5")
        row.pack(fill="x", pady=3)
        
        tk.Label(row, text=label, width=15, anchor="w", bg="#F5F5F5",
                font=("Arial", 9)).pack(side="left")
        
        # Прогресс-бар
        bar_frame = tk.Frame(row, bg="#E0E0E0", height=20, width=200)
        bar_frame.pack(side="left", padx=5)
        bar_frame.pack_propagate(False)
        
        bar_width = int(200 * percent / 100)
        if bar_width > 0:
            bar = tk.Frame(bar_frame, bg=color, height=20, width=bar_width)
            bar.pack(side="left")
        
        # Значение
        time_str = f"{int(time_sec)} сек ({percent:.1f}%)"
        tk.Label(row, text=time_str, anchor="w", bg="#F5F5F5",
                font=("Arial", 9), fg=color).pack(side="left", padx=5)
    
    def copy_to_clipboard(self):
        """Копировать статистику в буфер обмена."""
        text = self.generate_text_report()
        self.window.clipboard_clear()
        self.window.clipboard_append(text)
        messagebox.showinfo("Готово", "Статистика скопирована в буфер обмена!")
    
    def generate_text_report(self):
        """Сгенерировать текстовый отчёт."""
        lines = [
            "=" * 50,
            "СТАТИСТИКА ПРОЕКТА",
            "=" * 50,
            "",
            "РАЗМЕРЫ ПЛАТЫ:",
            f"  X: {self.min_x:.2f} ... {self.max_x:.2f} мм ({self.board_w:.2f} мм)",
            f"  Y: {self.min_y:.2f} ... {self.max_y:.2f} мм ({self.board_h:.2f} мм)",
            f"  Площадь: {self.board_area:.1f} см²",
            "",
            "ИНСТРУМЕНТЫ:",
            f"  Отверстий: {self.total_holes} ({self.drill_tools_count} инстр.)",
            f"  Слотов: {self.total_slots} ({self.slot_tools_count} инстр.)",
            f"  Обрезка: {self.total_board_outline} ({self.outline_tools_count} инстр.)",
            ""
        ]
        
        if self.tool_data:
            lines.append("  Детализация:")
            for tool in self.tool_data:
                lines.append(f"    T{tool['num']}  {tool['type']}  ⌀{tool['diameter']:.2f}мм  {tool['count']} шт.")
            lines.append("")
        
        lines.extend([
            "ПУТЬ ИНСТРУМЕНТА:",
            f"  Быстрый ход (XY): {self.total_rapid:.1f} мм ({self.total_rapid/1000:.2f} м)",
            f"  Рабочий ход (Z): {self.total_feed:.1f} мм ({self.total_feed/1000:.2f} м)",
        ])

        # Информация о фрезеровке
        if self.total_milling_dist > 0:
            if self.slot_feed_dist > 0:
                lines.append(f"  Фрезеровка слотов: {self.slot_feed_dist:.1f} мм ({self.slot_feed_dist/1000:.2f} м)")

            if self.outline_feed_dist > 0:
                lines.append(f"  Фрезеровка контура: {self.outline_feed_dist:.1f} мм ({self.outline_feed_dist/1000:.2f} м)")

            lines.append(f"  Фрезеровка (всего): {self.total_milling_dist:.1f} мм ({self.total_milling_dist/1000:.2f} м)")
        
        total_path = self.total_rapid + self.total_feed + self.total_milling_dist
        lines.append(f"  Общий путь: {total_path:.1f} мм ({total_path/1000:.2f} м)")
        lines.append("")
        
        minutes = int(self.total_time_sec // 60)
        seconds = int(self.total_time_sec % 60)
        lines.extend([
            "ВРЕМЯ ОБРАБОТКИ:",
            f"  Общее время: {minutes} мин {seconds} сек",
            f"  Быстрый ход: {int(self.time_rapid)} сек",
            f"  Сверление: {int(self.time_drill_feed)} сек",
        ])
        
        if self.time_mill_feed > 0:
            lines.append(f"  Фрезеровка: {int(self.time_mill_feed)} сек")
        
        lines.append("=" * 50)
        
        return "\n".join(lines)
    
    def center_window(self, parent):
        """Центрировать окно относительно родителя."""
        self.window.update_idletasks()
        w = self.window.winfo_width()
        h = self.window.winfo_height()
        x = parent.winfo_x() + (parent.winfo_width() - w) // 2
        y = parent.winfo_y() + (parent.winfo_height() - h) // 2
        self.window.geometry(f"+{x}+{y}")


def show_statistics_window(parent):
    """Показать окно статистики."""
    if not cfg.current_tools and not cfg.slot_tools and not cfg.board_outline:
        messagebox.showinfo("Статистика", "Нет загруженных данных.")
        return
    
    StatisticsWindow(parent)
