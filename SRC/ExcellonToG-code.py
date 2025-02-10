# Импорт необходимых библиотек
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import re
import math
import itertools
import webbrowser

# Глобальные переменные для управления отображением
offset_x = 0          # Горизонтальное смещение (центр вида)
offset_y = 0          # Вертикальное смещение (центр вида)
scale_factor = 1.5    # Начальный коэффициент масштабирования (весь рабочий стол)
drag_start_real_x = 0 # Начальная позиция X при перетаскивании (реальные координаты)
drag_start_real_y = 0 # Начальная позиция Y при перетаскивании (реальные координаты)
initial_offset_x = 0  # Начальное смещение X перед перетаскиванием
initial_offset_y = 0  # Начальное смещение Y перед перетаскиванием
current_tools = None  # Словарь с данными о инструментах и отверстиях
coordinate_format = "4.2"  # Формат координат по умолчанию
current_filename = None    # Путь к текущему файлу
show_paths_var = None      # Переменная для чекбокса отображения путей

# Константы интерфейса
CANVAS_WIDTH = 980     # Ширина холста
CANVAS_HEIGHT = 620    # Высота холста
WORKAREA_WIDTH = 900   # Ширина рабочей области
WORKAREA_HEIGHT = 600  # Высота рабочей области
WORKAREA_OFFSET_X = 60 # Смещение рабочей области по X
WORKAREA_OFFSET_Y = 20 # Смещение рабочей области по Y
X_MIN, X_MAX = -300, 300  # Границы рабочей зоны по X (мм)
Y_MIN, Y_MAX = -200, 200  # Границы рабочей зоны по Y (мм)
MIN_SCALE = 1.5        # Минимальный масштаб (весь рабочий стол)

# Функции преобразования координат
def to_real_x(virtual_x):
    """Преобразование виртуальной X координаты в реальную координату холста"""
    center_x = WORKAREA_OFFSET_X + WORKAREA_WIDTH / 2
    return center_x + (virtual_x - offset_x) * scale_factor

def to_real_y(virtual_y):
    """Преобразование виртуальной Y координаты в реальную координату холста"""
    center_y = WORKAREA_OFFSET_Y + WORKAREA_HEIGHT / 2
    return center_y - (virtual_y - offset_y) * scale_factor

def to_virtual_x(real_x):
    """Преобразование реальной X координаты холста в виртуальную координату"""
    center_x = WORKAREA_OFFSET_X + WORKAREA_WIDTH / 2
    return offset_x + (real_x - center_x) / scale_factor

def to_virtual_y(real_y):
    """Преобразование реальной Y координаты холста в виртуальную координату"""
    center_y = WORKAREA_OFFSET_Y + WORKAREA_HEIGHT / 2
    return offset_y + (center_y - real_y) / scale_factor

def is_excellon_file(filename):
    """Проверка формата файла Excellon"""
    try:
        with open(filename, 'r') as f:
            for _ in range(3):
                line = f.readline().strip()
                if line.startswith('M48') or line.startswith('%') or 'METRIC' in line or 'G90' in line:
                    return True
        return False
    except Exception:
        return False

def nearest_neighbor_tsp(points):
    """Алгоритм ближайшего соседа для оптимизации маршрута сверления"""
    if not points:
        return []
    visited = [False] * len(points)
    path = [0]
    visited[0] = True
    for _ in range(1, len(points)):
        last_point = path[-1]
        nearest_point = None
        nearest_distance = float('inf')
        for j in range(len(points)):
            if not visited[j]:
                distance = ((points[last_point][0] - points[j][0]) ** 2 +
                            (points[last_point][1] - points[j][1]) ** 2) ** 0.5
                if distance < nearest_distance:
                    nearest_distance = distance
                    nearest_point = j
        if nearest_point is not None:
            path.append(nearest_point)
            visited[nearest_point] = True
    return [points[i] for i in path]

def parse_excellon_file(filename):
    """Парсинг Excellon файла и извлечение данных об инструментах и отверстиях"""
    tools = {}
    current_tool = None
    format_x, format_y = map(int, coordinate_format.split('.'))
    last_x = None
    last_y = None
    with open(filename, 'r') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            if line.startswith('T'):
                tool_number = None
                diameter = 0.0
                tool_match = re.match(r'T(\d+)', line)
                if tool_match:
                    tool_number = tool_match.group(1)
                c_match = re.search(r'C([0-9.]+)', line)
                if c_match:
                    diameter = float(c_match.group(1))
                if tool_number:
                    current_tool = tool_number
                    if current_tool not in tools:
                        tools[current_tool] = {
                            'diameter': diameter,
                            'holes': [],
                            'visible': True,
                            'var': None
                        }
                    last_x = None
                    last_y = None
            if current_tool and ('X' in line or 'Y' in line):
                x_match = re.search(r'X([+-]?\d+)', line)
                y_match = re.search(r'Y([+-]?\d+)', line)
                if x_match:
                    x_str = x_match.group(1)
                    last_x = int(x_str) if x_str else 0
                if y_match:
                    y_str = y_match.group(1)
                    last_y = int(y_str) if y_str else 0
                if last_x is not None or last_y is not None:
                    x_mm = (last_x or 0) / (10 ** format_y)
                    y_mm = (last_y or 0) / (10 ** format_y)
                    tools[current_tool]['holes'].append((x_mm, y_mm))
    sorted_tools = dict(sorted(tools.items(), key=lambda item: item[1]['diameter']))
    for tool, data in sorted_tools.items():
        data['holes'] = nearest_neighbor_tsp(data['holes'])
    return sorted_tools

def choose_file():
    """Обработчик выбора файла через диалоговое окно"""
    global current_tools, current_filename
    filename = filedialog.askopenfilename(
        filetypes=[("Excellon files", "*.txt;*.drl"),  ("All files", "*.*")]
    )
    if not filename:
        return
    current_filename = filename  # Сохраняем путь к текущему файлу
    # Проверка формата файла
    if not is_excellon_file(filename):
        messagebox.showerror("Ошибка", "Неверный формат файла. Выберите файл Excellon.")
        return
    try:
        # Парсинг файла и обновление интерфейса
        current_tools = parse_excellon_file(filename)
        auto_fit_scale()  # Автоматическая подстройка масштаба
        redraw_grid()     # Перерисовка холста
        update_legend()   # Обновление легенды с инструментами
    except Exception as e:
        messagebox.showerror("Ошибка", f"Ошибка при чтении файла: {str(e)}")
        
def on_format_change(event):
    """Обработчик изменения формата координат"""
    global coordinate_format, current_tools
    coordinate_format = format_combobox.get()  # Получаем новый формат из комбобокса
    if current_filename:
        try:
            # Перепарсим файл с новым форматом
            current_tools = parse_excellon_file(current_filename)
            auto_fit_scale()
            redraw_grid()
            update_legend()
        except Exception as e:
            messagebox.showerror("Ошибка", f"Ошибка при обновлении формата: {str(e)}")
    else:
        redraw_grid()  # Если файл не загружен, просто перерисовываем сетку

def auto_fit_scale():
    """Автоматическое масштабирование для отображения всех отверстий"""
    global scale_factor, offset_x, offset_y
    if not current_tools:
        scale_factor = MIN_SCALE
        offset_x = 0
        offset_y = 0
        return
    
    holes = []
    for tool_data in current_tools.values():
        if tool_data['visible']:
            holes.extend(tool_data['holes'])
    if not holes:
        return
    
    # Проверка на выход за границы рабочей зоны
    any_outside = False
    for x, y in holes:
        if x < X_MIN or x > X_MAX or y < Y_MIN or y > Y_MAX:
            any_outside = True
            break
    
    if any_outside:
        scale_factor = MIN_SCALE
        offset_x = 0
        offset_y = 0
    else:
        min_x = min(h[0] for h in holes)
        max_x = max(h[0] for h in holes)
        min_y = min(h[1] for h in holes)
        max_y = max(h[1] for h in holes)
        width = max_x - min_x
        height = max_y - min_y
        scale_x = WORKAREA_WIDTH / width if width > 0 else 1.0
        scale_y = WORKAREA_HEIGHT / height if height > 0 else 1.0
        scale_factor = min(scale_x, scale_y)
        offset_x = (min_x + max_x) / 2
        offset_y = (min_y + max_y) / 2
        
        # Проверка на превышение масштаба
        if (max_x - min_x) * scale_factor > WORKAREA_WIDTH or (max_y - min_y) * scale_factor > WORKAREA_HEIGHT:
            scale_factor = min(WORKAREA_WIDTH / (max_x - min_x), WORKAREA_HEIGHT / (max_y - min_y))
            offset_x = (min_x + max_x) / 2
            offset_y = (min_y + max_y) / 2
    
    # Ограничение смещений
    view_width = WORKAREA_WIDTH / scale_factor
    view_height = WORKAREA_HEIGHT / scale_factor
    offset_x = max(X_MIN + view_width/2, min(offset_x, X_MAX - view_width/2))
    offset_y = max(Y_MIN + view_height/2, min(offset_y, Y_MAX - view_height/2))

def on_mousewheel(event):
    """Обработчик масштабирования колесом мыши"""
    global scale_factor, offset_x, offset_y
    center_x = WORKAREA_OFFSET_X + WORKAREA_WIDTH / 2
    center_y = WORKAREA_OFFSET_Y + WORKAREA_HEIGHT / 2
    
    # Получаем текущие виртуальные координаты мыши
    mx = offset_x + (event.x - center_x) / scale_factor
    my = offset_y + (center_y - event.y) / scale_factor
    
    # Рассчитываем новый масштаб
    new_scale = scale_factor * 1.1 if event.delta > 0 else scale_factor * 0.9
    new_scale = max(MIN_SCALE, min(new_scale, 1200.0))
    
    # Рассчитываем новые смещения для сохранения позиции мыши
    new_offset_x = mx - (event.x - center_x) / new_scale
    new_offset_y = my - (center_y - event.y) / new_scale
    
    # Ограничиваем смещения
    view_width = WORKAREA_WIDTH / new_scale
    view_height = WORKAREA_HEIGHT / new_scale
    new_offset_x = max(X_MIN + view_width/2, min(new_offset_x, X_MAX - view_width/2))
    new_offset_y = max(Y_MIN + view_height/2, min(new_offset_y, Y_MAX - view_height/2))
    
    scale_factor = new_scale
    offset_x = new_offset_x
    offset_y = new_offset_y
    redraw_grid()

def start_drag(event):
    """Начало перетаскивания холста"""
    global drag_start_real_x, drag_start_real_y, initial_offset_x, initial_offset_y
    drag_start_real_x = event.x
    drag_start_real_y = event.y
    initial_offset_x = offset_x
    initial_offset_y = offset_y

def during_drag(event):
    """Обработчик движения мыши при перетаскивании холста"""
    global offset_x, offset_y
    dx_real = event.x - drag_start_real_x
    dy_real = event.y - drag_start_real_y
    
    # Конвертация смещения в виртуальные координаты
    dx_virtual = dx_real / scale_factor
    dy_virtual = dy_real / scale_factor
    
    new_offset_x = initial_offset_x - dx_virtual
    new_offset_y = initial_offset_y + dy_virtual
    
    # Ограничение смещений
    view_width = WORKAREA_WIDTH / scale_factor
    view_height = WORKAREA_HEIGHT / scale_factor
    new_offset_x = max(X_MIN + view_width/2, min(new_offset_x, X_MAX - view_width/2))
    new_offset_y = max(Y_MIN + view_height/2, min(new_offset_y, Y_MAX - view_height/2))
    
    offset_x = new_offset_x
    offset_y = new_offset_y
    redraw_grid()

def get_grid_step_mm():
    """Определение шага сетки в зависимости от масштаба"""
    if scale_factor >= 10: return 1
    elif scale_factor >= 5: return 5
    elif scale_factor >= 2: return 10
    return 20

def determine_ruler_step(visible_range_mm):
    """Определение шага делений для линеек"""
    min_pixel_step = 50
    min_mm_step = min_pixel_step / scale_factor
    step = 1
    while step < min_mm_step:
        if step * 5 >= min_mm_step: step *= 5
        elif step * 2 >= min_mm_step: step *= 2
        else: step *= 10
    return max(1, int(step))

def draw_rulers():
    """Отрисовка горизонтальной и вертикальной линеек"""
    # Горизонтальная линейка (X)
    visible_start_x = offset_x - (WORKAREA_WIDTH / (2 * scale_factor))
    visible_end_x = offset_x + (WORKAREA_WIDTH / (2 * scale_factor))
    step_x = determine_ruler_step(visible_end_x - visible_start_x)
    first_tick_x = step_x * math.floor(visible_start_x / step_x)
    last_tick_x = step_x * math.ceil(visible_end_x / step_x)
    
    for x_mm in range(first_tick_x, last_tick_x + 1, step_x):
        if x_mm < X_MIN or x_mm > X_MAX:
            continue
        real_x = to_real_x(x_mm)
        canvas.create_line(real_x, WORKAREA_OFFSET_Y + WORKAREA_HEIGHT + 10,
                         real_x, WORKAREA_OFFSET_Y + WORKAREA_HEIGHT + 20, 
                         fill="black")
        canvas.create_text(real_x, WORKAREA_OFFSET_Y + WORKAREA_HEIGHT + 25,
                         text=f"{x_mm:.0f}", anchor="n", font=("Arial", 8))
    
    # Вертикальная линейка (Y)
    visible_start_y = offset_y - (WORKAREA_HEIGHT / (2 * scale_factor))
    visible_end_y = offset_y + (WORKAREA_HEIGHT / (2 * scale_factor))
    step_y = determine_ruler_step(visible_end_y - visible_start_y)
    first_tick_y = step_y * math.floor(visible_start_y / step_y)
    last_tick_y = step_y * math.ceil(visible_end_y / step_y)
    
    for y_mm in range(first_tick_y, last_tick_y + 1, step_y):
        if y_mm < Y_MIN or y_mm > Y_MAX:
            continue
        real_y = to_real_y(y_mm)
        canvas.create_line(WORKAREA_OFFSET_X - 20, real_y,
                         WORKAREA_OFFSET_X - 10, real_y,
                         fill="black")
        canvas.create_text(WORKAREA_OFFSET_X - 25, real_y,
                         text=f"{y_mm:.0f}", anchor="e", font=("Arial", 8))

def redraw_grid(event=None):
    """Полная перерисовка всех элементов холста"""
    canvas.delete("all")
    
    # Отрисовка рабочей области
    canvas.create_rectangle(
        WORKAREA_OFFSET_X, WORKAREA_OFFSET_Y,
        WORKAREA_OFFSET_X + WORKAREA_WIDTH,
        WORKAREA_OFFSET_Y + WORKAREA_HEIGHT,
        fill="white"
    )
    
    # Отрисовка сетки
    grid_step_mm = get_grid_step_mm()
    visible_start_x = offset_x - (WORKAREA_WIDTH / (2 * scale_factor))
    visible_end_x = offset_x + (WORKAREA_WIDTH / (2 * scale_factor))
    first_line_x = grid_step_mm * math.floor(visible_start_x / grid_step_mm)
    last_line_x = grid_step_mm * math.ceil(visible_end_x / grid_step_mm)
    
    for x_mm in range(first_line_x, last_line_x + 1, grid_step_mm):
        real_x = to_real_x(x_mm)
        if WORKAREA_OFFSET_X <= real_x <= WORKAREA_OFFSET_X + WORKAREA_WIDTH:
            canvas.create_line(real_x, WORKAREA_OFFSET_Y,
                             real_x, WORKAREA_OFFSET_Y + WORKAREA_HEIGHT,
                             fill="lightgray")
    
    visible_start_y = offset_y - (WORKAREA_HEIGHT / (2 * scale_factor))
    visible_end_y = offset_y + (WORKAREA_HEIGHT / (2 * scale_factor))
    first_line_y = grid_step_mm * math.floor(visible_start_y / grid_step_mm)
    last_line_y = grid_step_mm * math.ceil(visible_end_y / grid_step_mm)
    
    for y_mm in range(first_line_y, last_line_y + 1, grid_step_mm):
        real_y = to_real_y(y_mm)
        if WORKAREA_OFFSET_Y <= real_y <= WORKAREA_OFFSET_Y + WORKAREA_HEIGHT:
            canvas.create_line(WORKAREA_OFFSET_X, real_y,
                             WORKAREA_OFFSET_X + WORKAREA_WIDTH, real_y,
                             fill="lightgray")
    
    draw_rulers()
    
    # Отрисовка отверстий и путей
    if current_tools:
        colors = ['red', 'green', 'blue', 'orange', 'purple', 'cyan', 'magenta', 'yellow']
        visible_min_x = offset_x - (WORKAREA_WIDTH / (2 * scale_factor))
        visible_max_x = offset_x + (WORKAREA_WIDTH / (2 * scale_factor))
        visible_min_y = offset_y - (WORKAREA_HEIGHT / (2 * scale_factor))
        visible_max_y = offset_y + (WORKAREA_HEIGHT / (2 * scale_factor))
        
        # Сначала отверстия
        for i, (tool, data) in enumerate(current_tools.items()):
            if not data['visible']:
                continue
            color = colors[i % len(colors)]
            for x_mm, y_mm in data['holes']:
                if not (visible_min_x <= x_mm <= visible_max_x and visible_min_y <= y_mm <= visible_max_y):
                    continue
                real_x = to_real_x(x_mm)
                real_y = to_real_y(y_mm)
                canvas.create_oval(real_x-2, real_y-2, real_x+2, real_y+2, fill=color, outline=color)

        # Затем пути с отсечением
        if show_paths_var and show_paths_var.get():
            for i, (tool, data) in enumerate(current_tools.items()):
                if not data['visible'] or len(data['holes']) < 2:
                    continue
                color = colors[i % len(colors)]
                holes = data['holes']
                
                for j in range(len(holes)-1):
                    # Получаем координаты отрезка в мм
                    x1_mm, y1_mm = holes[j]
                    x2_mm, y2_mm = holes[j+1]
                    
                    # Конвертируем в реальные координаты холста
                    real_x1 = to_real_x(x1_mm)
                    real_y1 = to_real_y(y1_mm)
                    real_x2 = to_real_x(x2_mm)
                    real_y2 = to_real_y(y2_mm)
                    
                    # Отсекаем отрезок по границам рабочей области
                    clipped = clip_line(
                        real_x1, real_y1, real_x2, real_y2,
                        WORKAREA_OFFSET_X, WORKAREA_OFFSET_Y,
                        WORKAREA_OFFSET_X + WORKAREA_WIDTH,
                        WORKAREA_OFFSET_Y + WORKAREA_HEIGHT
                    )
                    
                    if clipped[0] is not None:
                        canvas.create_line(
                            clipped[0], clipped[1],
                            clipped[2], clipped[3],
                            fill=color, width=1
                        )

def clip_line(x1, y1, x2, y2, x_min, y_min, x_max, y_max):
    """Алгоритм Коэна-Сазерленда для отсечения отрезков"""
    # Коды областей
    INSIDE = 0  # 0000
    LEFT = 1    # 0001
    RIGHT = 2   # 0010
    BOTTOM = 4  # 0100
    TOP = 8     # 1000

    def compute_code(x, y):
        code = INSIDE
        if x < x_min: code |= LEFT
        elif x > x_max: code |= RIGHT
        if y < y_min: code |= BOTTOM
        elif y > y_max: code |= TOP
        return code

    code1 = compute_code(x1, y1)
    code2 = compute_code(x2, y2)
    accept = False

    while True:
        if code1 == 0 and code2 == 0:
            accept = True
            break
        elif (code1 & code2) != 0:
            break
        else:
            x = 0
            y = 0
            code_out = code1 if code1 != 0 else code2

            if code_out & TOP:
                x = x1 + (x2 - x1) * (y_max - y1) / (y2 - y1)
                y = y_max
            elif code_out & BOTTOM:
                x = x1 + (x2 - x1) * (y_min - y1) / (y2 - y1)
                y = y_min
            elif code_out & RIGHT:
                y = y1 + (y2 - y1) * (x_max - x1) / (x2 - x1)
                x = x_max
            elif code_out & LEFT:
                y = y1 + (y2 - y1) * (x_min - x1) / (x2 - x1)
                x = x_min

            if code_out == code1:
                x1, y1 = x, y
                code1 = compute_code(x1, y1)
            else:
                x2, y2 = x, y
                code2 = compute_code(x2, y2)

    if accept:
        return x1, y1, x2, y2
    else:
        return (None, None, None, None)

def toggle_visibility(tool):
    """Переключение видимости отверстий для конкретного инструмента"""
    current_tools[tool]['visible'] = current_tools[tool]['var'].get()
    redraw_grid()

def update_legend():
    """Обновление легенды с инструментами и настройками"""
    # Удаление старой легенды
    for widget in control_frame.winfo_children():
        if isinstance(widget, tk.Frame) and widget.winfo_name() == "legend_frame":
            widget.destroy()
    
    # Создание нового фрейма для легенды
    legend_frame = tk.Frame(control_frame, name="legend_frame")
    legend_frame.pack(pady=10, fill='x')
    
    tk.Label(legend_frame, text="Легенда", font='Arial 9 bold').pack(pady=(0, 5), fill='x')
    
    colors = ['red', 'green', 'blue', 'orange', 'purple', 'cyan', 'magenta', 'yellow']
    
    if current_tools:
        # Создаем фрейм для отверстий с возможностью прокрутки, если их больше 8
        if len(current_tools) > 8:
            scrollable_frame = tk.Frame(legend_frame)
            scrollable_frame.pack(side=tk.TOP, fill='x')
            
            scrollbar = tk.Scrollbar(scrollable_frame, orient="vertical")
            scrollbar.pack(side=tk.RIGHT, fill='y')
            
            canvas_scrollable = tk.Canvas(scrollable_frame, yscrollcommand=scrollbar.set)
            canvas_scrollable.pack(side=tk.LEFT, fill='x')
            
            scrollbar.config(command=canvas_scrollable.yview)
            
            inner_frame = tk.Frame(canvas_scrollable)
            canvas_scrollable.create_window((0, 0), window=inner_frame, anchor="nw")
            
            inner_frame.bind("<Configure>", lambda e: canvas_scrollable.configure(scrollregion=canvas_scrollable.bbox("all")))
            
            # Добавление элементов для каждого инструмента
            for i, (tool, data) in enumerate(current_tools.items()):
                color = colors[i % len(colors)]
                diameter = data['diameter']
                hole_count = len(data['holes'])
                
                # Создание переменной для чекбокса
                if not data['var']:
                    data['var'] = tk.BooleanVar(value=data['visible'])
                
                # Создание элемента легенды
                legend_item = tk.Frame(inner_frame)
                legend_item.pack(fill='x', pady=2)
                
                # Чекбокс видимости
                chk = tk.Checkbutton(
                    legend_item, 
                    variable=data['var'],
                    command=lambda t=tool: toggle_visibility(t)
                )
                chk.pack(side=tk.LEFT, padx=2)
                
                # Цвет инструмента
                color_label = tk.Label(legend_item, width=2, height=1, bg=color)
                color_label.pack(side=tk.LEFT, padx=5)
                
                # Информация об инструменте
                info_label = tk.Label(legend_item, text=f"{diameter:.2f} мм - {hole_count} шт")
                info_label.pack(side=tk.LEFT, padx=5)
        else:
            # Добавление элементов для каждого инструмента без прокрутки
            for i, (tool, data) in enumerate(current_tools.items()):
                color = colors[i % len(colors)]
                diameter = data['diameter']
                hole_count = len(data['holes'])
                
                # Создание переменной для чекбокса
                if not data['var']:
                    data['var'] = tk.BooleanVar(value=data['visible'])
                
                # Создание элемента легенды
                legend_item = tk.Frame(legend_frame)
                legend_item.pack(fill='x', pady=2)
                
                # Чекбокс видимости
                chk = tk.Checkbutton(
                    legend_item, 
                    variable=data['var'],
                    command=lambda t=tool: toggle_visibility(t)
                )
                chk.pack(side=tk.LEFT, padx=2)
                
                # Цвет инструмента
                color_label = tk.Label(legend_item, width=2, height=1, bg=color)
                color_label.pack(side=tk.LEFT, padx=5)
                
                # Информация об инструменте
                info_label = tk.Label(legend_item, text=f"{diameter:.2f} мм - {hole_count} шт")
                info_label.pack(side=tk.LEFT, padx=5)
    
    # Добавление чекбокса для отображения путей
    if current_tools:
        ttk.Separator(legend_frame).pack(fill='x', pady=5)
        paths_frame = tk.Frame(legend_frame)
        paths_frame.pack(fill='x', pady=2)
        chk_show_paths = tk.Checkbutton(
            paths_frame, 
            text="Отобразить пути",
            variable=show_paths_var,
            command=redraw_grid
        )
        chk_show_paths.pack(side=tk.LEFT, padx=5)

def generate_gcode():
    """Генерация G-кода на основе текущих параметров"""
    global current_tools
    # Проверка загруженного файла
    if not current_tools:
        messagebox.showerror("Ошибка", "Сначала загрузите файл Excellon.")
        return
    
    # Проверка и получение параметров
    try:
        z = float(z_entry.get())   # Глубина сверления
        r = float(r_entry.get())   # Безопасная высота
        fr = float(fr_entry.get()) # Скорость подачи
        p = float(p_entry.get())   # Высота парковки
    except ValueError:
        messagebox.showerror("Ошибка", "Проверьте правильность введенных параметров.")
        return
    
    # Фильтрация видимых инструментов с отверстиями
    visible_tools = []
    for tool, data in current_tools.items():
        if data['visible'] and len(data['holes']) > 0:
            visible_tools.append((tool, data))
    if not visible_tools:
        messagebox.showerror("Ошибка", "Не выбран ни один инструмент.")
        return
    
    # Диалог сохранения файла
    filename = filedialog.asksaveasfilename(
        defaultextension=".tap",
        filetypes=[("G-code Files", "*.tap"), ("All Files", "*.*")]
    )
    if not filename:
        return
    
    try:
        with open(filename, 'w') as f:
            # Заголовок программы
            f.write("G17 G21 G90\n\n;Parking\nM05\n")
            f.write(f"G0 X0 Y0 Z{p:.0f}\n")  # Начальная позиция
            
            for tool, data in visible_tools:
                diameter = data['diameter']
                holes = data['holes']
                
                # Блок инструмента
                f.write(f";Change Tool\n;Tool {tool}\n;{diameter:.2f} mm\n")
                f.write(f"T{tool} M06\n")  # Смена инструмента
                f.write(f"M03\n")           # Включение шпинделя
                f.write(f"\nG0 Z{r:.0f}\n") # Переход на безопасную высоту
                
                # Последовательность сверления
                for x, y in holes:
                    f.write(f"X{x:.2f} Y{y:.2f} \nZ0 \nG1 Z{z:.2f} F{fr:.0f} \nG0 Z{r:.0f}\n")
                
                # Возврат в парковку
                f.write("\n;Parking\nM05\n")
                f.write(f"G0 X0 Y0 Z{p:.0f}\n")
            
            f.write("\n;End of programm\nM30")  # Конец программы
        
        # Окно успешного сохранения с ссылкой
        success_window = tk.Toplevel(root)
        success_window.title("Готово")
        success_window.geometry("300x100")  # Сначала задаем размер

        # Вычисляем позицию относительно главного окна
        root.update_idletasks()  # Обновляем геометрические данные
        root_x = root.winfo_x()
        root_y = root.winfo_y()
        root_width = root.winfo_width()
        root_height = root.winfo_height()

        # Вычисляем координаты для центрирования
        x = root_x + (root_width - 300) // 2  # 300 - ширина окна
        y = root_y + (root_height - 100) // 2  # 100 - высота окна

        # Устанавливаем позицию
        success_window.geometry(f"+{x}+{y}")

        # Остальной код окна
        msg = "G-код успешно сохранен!\n\nСимулятор: "
        link = "https://ncviewer.com/"
        label = tk.Label(success_window, text=msg, pady=10)
        label.pack()
        link_label = tk.Label(success_window, text=link, fg="blue", cursor="hand2")
        link_label.pack()
        link_label.bind("<Button-1>", lambda e: webbrowser.open(link))
        
    except Exception as e:
        messagebox.showerror("Ошибка", f"Ошибка при сохранении: {str(e)}")

# Инициализация GUI
root = tk.Tk()
root.title("Excellon to G-Code")
root.geometry("1220x700")
root.minsize(1160, 700)
root.resizable(False, False)
show_paths_var = tk.BooleanVar(value=False)

# Основные контейнеры
main_frame = tk.Frame(root)
main_frame.pack(fill='both', expand=True, padx=10, pady=10)

# Фрейм для холста (левая часть)
canvas_frame = tk.Frame(main_frame, width=920)
canvas_frame.pack(side='left', fill='y', padx=(0, 5))

# Холст для отрисовки
canvas = tk.Canvas(canvas_frame, width=CANVAS_WIDTH, height=CANVAS_HEIGHT, bg="lightgray")
canvas.pack(fill='both', expand=True)

# Фрейм элементов управления (правая часть)
control_frame = tk.Frame(main_frame)
control_frame.pack(side='right', fill='both', expand=True, padx=(5, 0))

# Элементы управления
choose_file_button = tk.Button(control_frame, text="Выбрать файл", command=choose_file)
choose_file_button.pack(pady=10, fill='x')

# Строка с выбором формата
format_frame = tk.Frame(control_frame)
format_frame.pack(fill='x', pady=5)
format_label = tk.Label(format_frame, text="Формат координат:", font='Arial 9 bold')
format_label.grid(row=0, column=0, sticky='ew', padx=(0, 5))
format_combobox = ttk.Combobox(format_frame, values=["3.2", "3.3", "4.2", "4.3", "4.4"], state="readonly", width=6)
format_combobox.set("4.2")
format_combobox.grid(row=0, column=1, sticky='ew')
format_combobox.bind("<<ComboboxSelected>>", on_format_change)
format_frame.columnconfigure(0, weight=1)
format_frame.columnconfigure(1, weight=0)

# Параметры G-кода
header_frame = tk.Frame(control_frame)
header_frame.pack(fill='x', pady=(10, 10))
tk.Label(header_frame, text="Параметры G-кода:", font='Arial 9 bold').pack(fill='x')

params_frame = tk.Frame(control_frame)
params_frame.pack(pady=(0, 10), fill='x')
params_frame.grid_columnconfigure(0, weight=0, minsize=150)
params_frame.grid_columnconfigure(1, weight=1)

# Поля ввода параметров
tk.Label(params_frame, text="Z (глубина сверл., мм):").grid(row=1, column=0, sticky='w', padx=5)
z_entry = tk.Entry(params_frame)
z_entry.grid(row=1, column=1, pady=2, sticky='ew')
z_entry.insert(0, "-2.0")

tk.Label(params_frame, text="R (безоп. высота, мм):").grid(row=2, column=0, sticky='w', padx=5)
r_entry = tk.Entry(params_frame)
r_entry.grid(row=2, column=1, pady=2, sticky='ew')
r_entry.insert(0, "5")

tk.Label(params_frame, text="F (подача, мм/мин):").grid(row=3, column=0, sticky='w', padx=5)
fr_entry = tk.Entry(params_frame)
fr_entry.grid(row=3, column=1, pady=2, sticky='ew')
fr_entry.insert(0, "100")

tk.Label(params_frame, text="P (парковка, мм):").grid(row=4, column=0, sticky='w', padx=5)
p_entry = tk.Entry(params_frame)
p_entry.grid(row=4, column=1, pady=2, sticky='ew')
p_entry.insert(0, "30")

# Кнопка генерации
generate_btn = tk.Button(control_frame, text="Создать G-code", command=generate_gcode, bg="#90EE90")
generate_btn.pack(side='bottom', pady=15, fill='x')

# Привязка событий
canvas.bind("<MouseWheel>", on_mousewheel)
canvas.bind("<Button-1>", start_drag)
canvas.bind("<B1-Motion>", during_drag)
canvas.bind("<Configure>", redraw_grid)

# Первоначальная отрисовка
redraw_grid()
root.mainloop()