# Импорт необходимых библиотек
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import os
import re
import math
import webbrowser
import io

# Глобальные переменные для управления отображением
offset_x = 0
offset_y = 0
scale_factor = 1.5
drag_start_real_x = 0
drag_start_real_y = 0
initial_offset_x = 0
initial_offset_y = 0
current_tools = None
coordinate_format = "4.2"
current_filename = None
show_paths_var = None
slot_tools = None
slot_filename = None

# Состояние интерактивной легенды
hovered_tool = None   # (tool_key, tool_type) или None
solo_tool = None      # (tool_key, tool_type) или None — изолированный инструмент

# Состояние визуализатора G-code
viz_mode = False           # True = режим визуализации
viz_gcode_lines = []       # Распарсенные сегменты G-code
viz_play_index = 0         # Текущая позиция плеера
viz_playing = False        # Анимация запущена
viz_after_id = None        # ID after()-таймера
viz_last_gcode = None      # Последний сгенерированный G-code (строка)
viz_sf = 1.0               # Масштаб визуализатора (свой, независимый)
viz_ox = 0.0               # Смещение X визуализатора (мм)
viz_oy = 0.0               # Смещение Y визуализатора (мм)

# Константы интерфейса
CANVAS_WIDTH = 980
CANVAS_HEIGHT = 620
WORKAREA_WIDTH = 900
WORKAREA_HEIGHT = 560
WORKAREA_OFFSET_X = 60
WORKAREA_OFFSET_Y = 10
X_MIN, X_MAX = -300, 300
Y_MIN, Y_MAX = -200, 200
MIN_SCALE = 1.5

SIMULATOR_URL = "https://ncviewer.com/"


def to_real_x(virtual_x):
    center_x = WORKAREA_OFFSET_X + WORKAREA_WIDTH / 2
    return center_x + (virtual_x - offset_x) * scale_factor


def to_real_y(virtual_y):
    center_y = WORKAREA_OFFSET_Y + WORKAREA_HEIGHT / 2
    return center_y - (virtual_y - offset_y) * scale_factor


def to_virtual_x(real_x):
    center_x = WORKAREA_OFFSET_X + WORKAREA_WIDTH / 2
    return offset_x + (real_x - center_x) / scale_factor


def to_virtual_y(real_y):
    center_y = WORKAREA_OFFSET_Y + WORKAREA_HEIGHT / 2
    return offset_y + (center_y - real_y) / scale_factor


def detect_coordinate_format(filename):
    """Автоопределение формата координат из заголовка Excellon файла.
    Ищет слово 'format' (без учёта регистра) и извлекает формат вида N.N или N:N.
    Возвращает строку формата (например '3.3') или None если не найден."""
    try:
        with open(filename, 'r') as f:
            for _ in range(20):
                line = f.readline()
                if not line:
                    break
                if re.search(r'format', line, re.IGNORECASE):
                    m = re.search(r'(\d)[.:,](\d)', line)
                    if m:
                        return f"{m.group(1)}.{m.group(2)}"
    except Exception:
        pass
    return None


def is_excellon_file(filename):
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


def nearest_neighbor_tsp_slots(slots):
    if not slots:
        return []
    if len(slots) == 1:
        return slots
    visited = [False] * len(slots)
    path = [0]
    visited[0] = True
    for _ in range(1, len(slots)):
        last_slot = slots[path[-1]]
        last_pos = last_slot[1]
        nearest_idx = None
        nearest_distance = float('inf')
        for j in range(len(slots)):
            if not visited[j]:
                sx, sy = slots[j][0]
                distance = ((last_pos[0] - sx) ** 2 + (last_pos[1] - sy) ** 2) ** 0.5
                if distance < nearest_distance:
                    nearest_distance = distance
                    nearest_idx = j
        if nearest_idx is not None:
            path.append(nearest_idx)
            visited[nearest_idx] = True
    return [slots[i] for i in path]


def parse_excellon_file(filename):
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
                    last_x = int(x_match.group(1))
                if y_match:
                    last_y = int(y_match.group(1))
                if last_x is not None or last_y is not None:
                    x_mm = (last_x or 0) / (10 ** format_y)
                    y_mm = (last_y or 0) / (10 ** format_y)
                    tools[current_tool]['holes'].append((x_mm, y_mm))
    sorted_tools = dict(sorted(tools.items(), key=lambda item: item[1]['diameter']))
    for tool, data in sorted_tools.items():
        data['holes'] = nearest_neighbor_tsp(data['holes'])
    return sorted_tools


def parse_slot_file(filename):
    tools = {}
    current_tool = None
    format_x, format_y = map(int, coordinate_format.split('.'))
    lines = []
    with open(filename, 'r') as f:
        lines = [l.strip() for l in f.readlines()]
    header_tools = {}
    in_header = True
    for line in lines:
        if line == '%':
            in_header = False
            continue
        if in_header:
            tool_match = re.match(r'T(\d+)', line)
            if tool_match:
                tool_number = tool_match.group(1)
                c_match = re.search(r'C([0-9.]+)', line)
                diameter = float(c_match.group(1)) if c_match else 0.0
                header_tools[tool_number] = diameter
    current_tool = None
    i = 0
    while i < len(lines):
        line = lines[i]
        tool_match = re.match(r'^T(\d+)$', line)
        if tool_match:
            tool_number = tool_match.group(1)
            current_tool = tool_number
            if current_tool not in tools:
                diameter = header_tools.get(current_tool, 0.0)
                tools[current_tool] = {
                    'diameter': diameter,
                    'slots': [],
                    'visible': True,
                    'var': None
                }
            i += 1
            continue
        if current_tool and line.startswith('G00'):
            x_match = re.search(r'X([+-]?\d+)', line)
            y_match = re.search(r'Y([+-]?\d+)', line)
            if x_match or y_match:
                g00_x = int(x_match.group(1)) if x_match else None
                g00_y = int(y_match.group(1)) if y_match else None
                if i + 1 < len(lines) and lines[i + 1] == 'M15':
                    if i + 2 < len(lines) and lines[i + 2].startswith('G01'):
                        g01_line = lines[i + 2]
                        g01_x_match = re.search(r'X([+-]?\d+)', g01_line)
                        g01_y_match = re.search(r'Y([+-]?\d+)', g01_line)
                        g01_x = int(g01_x_match.group(1)) if g01_x_match else g00_x
                        g01_y = int(g01_y_match.group(1)) if g01_y_match else g00_y
                        if i + 3 < len(lines) and lines[i + 3] == 'M16':
                            start_x = (g00_x or 0) / (10 ** format_y)
                            start_y = (g00_y or 0) / (10 ** format_y)
                            end_x = (g01_x or 0) / (10 ** format_y)
                            end_y = (g01_y or 0) / (10 ** format_y)
                            tools[current_tool]['slots'].append(
                                ((start_x, start_y), (end_x, end_y))
                            )
                            i += 4
                            continue
            i += 1
            continue
        i += 1
    for tool, data in tools.items():
        if data['slots']:
            data['slots'] = nearest_neighbor_tsp_slots(data['slots'])
    return tools


def choose_file():
    global current_tools, current_filename, coordinate_format
    filename = filedialog.askopenfilename(
        filetypes=[("Excellon files", "*.txt;*.drl"), ("All files", "*.*")]
    )
    if not filename:
        return
    current_filename = filename
    if not is_excellon_file(filename):
        messagebox.showerror("Ошибка", "Неверный формат файла.")
        return
    detected = detect_coordinate_format(filename)
    if detected:
        coordinate_format = detected
        format_combobox.set(detected)
    try:
        current_tools = parse_excellon_file(filename)
        holes_file_label.config(text=f"Отверстия: {os.path.basename(filename)}")
        auto_fit_scale()
        redraw_grid()
        update_legend()
        status_label.config(text=f"Загружен: {os.path.basename(filename)}")
    except Exception as e:
        messagebox.showerror("Ошибка", f"Ошибка при чтении файла: {str(e)}")


def choose_slot_file():
    global slot_tools, slot_filename, coordinate_format
    filename = filedialog.askopenfilename(
        filetypes=[("Excellon Slot files", "*.txt;*.drl"), ("All files", "*.*")]
    )
    if not filename:
        return
    slot_filename = filename
    if not is_excellon_file(filename):
        messagebox.showerror("Ошибка", "Неверный формат файла.")
        return
    detected = detect_coordinate_format(filename)
    if detected:
        coordinate_format = detected
        format_combobox.set(detected)
    try:
        slot_tools = parse_slot_file(filename)
        slot_file_label.config(text=f"Слоты: {os.path.basename(filename)}")
        auto_fit_scale()
        redraw_grid()
        update_legend()
        status_label.config(text=f"Слоты загружены: {os.path.basename(filename)}")
    except Exception as e:
        messagebox.showerror("Ошибка", f"Ошибка при чтении файла слотов: {str(e)}")


def on_format_change(event):
    global coordinate_format, current_tools, slot_tools
    coordinate_format = format_combobox.get()
    if current_filename:
        try:
            current_tools = parse_excellon_file(current_filename)
        except Exception as e:
            messagebox.showerror("Ошибка", f"Ошибка: {str(e)}")
    if slot_filename:
        try:
            slot_tools = parse_slot_file(slot_filename)
        except Exception as e:
            messagebox.showerror("Ошибка", f"Ошибка: {str(e)}")
    auto_fit_scale()
    redraw_grid()
    update_legend()


def auto_fit_scale():
    global scale_factor, offset_x, offset_y
    all_points = []
    if current_tools:
        for tool_data in current_tools.values():
            if tool_data['visible']:
                all_points.extend(tool_data['holes'])
    if slot_tools:
        for tool_data in slot_tools.values():
            if tool_data['visible']:
                for start, end in tool_data['slots']:
                    all_points.append(start)
                    all_points.append(end)
    if not all_points:
        scale_factor = MIN_SCALE
        offset_x = 0
        offset_y = 0
        return
    min_x = min(h[0] for h in all_points)
    max_x = max(h[0] for h in all_points)
    min_y = min(h[1] for h in all_points)
    max_y = max(h[1] for h in all_points)
    width = max_x - min_x
    height = max_y - min_y
    if width <= 0:
        width = 1
    if height <= 0:
        height = 1
    scale_x = WORKAREA_WIDTH / width * 0.9
    scale_y = WORKAREA_HEIGHT / height * 0.9
    scale_factor = min(scale_x, scale_y)
    scale_factor = max(MIN_SCALE, scale_factor)
    offset_x = (min_x + max_x) / 2
    offset_y = (min_y + max_y) / 2
    view_width = WORKAREA_WIDTH / scale_factor
    view_height = WORKAREA_HEIGHT / scale_factor
    offset_x = max(X_MIN + view_width / 2, min(offset_x, X_MAX - view_width / 2))
    offset_y = max(Y_MIN + view_height / 2, min(offset_y, Y_MAX - view_height / 2))


def on_mousewheel(event):
    global scale_factor, offset_x, offset_y
    center_x = WORKAREA_OFFSET_X + WORKAREA_WIDTH / 2
    center_y = WORKAREA_OFFSET_Y + WORKAREA_HEIGHT / 2
    mx = offset_x + (event.x - center_x) / scale_factor
    my = offset_y + (center_y - event.y) / scale_factor
    new_scale = scale_factor * 1.1 if event.delta > 0 else scale_factor * 0.9
    new_scale = max(MIN_SCALE, min(new_scale, 1200.0))
    new_offset_x = mx - (event.x - center_x) / new_scale
    new_offset_y = my - (center_y - event.y) / new_scale
    view_width = WORKAREA_WIDTH / new_scale
    view_height = WORKAREA_HEIGHT / new_scale
    new_offset_x = max(X_MIN + view_width / 2, min(new_offset_x, X_MAX - view_width / 2))
    new_offset_y = max(Y_MIN + view_height / 2, min(new_offset_y, Y_MAX - view_height / 2))
    scale_factor = new_scale
    offset_x = new_offset_x
    offset_y = new_offset_y
    redraw_grid()


def start_drag(event):
    global drag_start_real_x, drag_start_real_y, initial_offset_x, initial_offset_y
    drag_start_real_x = event.x
    drag_start_real_y = event.y
    initial_offset_x = offset_x
    initial_offset_y = offset_y


def during_drag(event):
    global offset_x, offset_y
    dx_real = event.x - drag_start_real_x
    dy_real = event.y - drag_start_real_y
    new_offset_x = initial_offset_x - dx_real / scale_factor
    new_offset_y = initial_offset_y + dy_real / scale_factor
    view_width = WORKAREA_WIDTH / scale_factor
    view_height = WORKAREA_HEIGHT / scale_factor
    new_offset_x = max(X_MIN + view_width / 2, min(new_offset_x, X_MAX - view_width / 2))
    new_offset_y = max(Y_MIN + view_height / 2, min(new_offset_y, Y_MAX - view_height / 2))
    offset_x = new_offset_x
    offset_y = new_offset_y
    redraw_grid()


def get_grid_step_mm():
    if scale_factor >= 10:
        return 1
    elif scale_factor >= 5:
        return 5
    elif scale_factor >= 2:
        return 10
    return 20


def determine_ruler_step(visible_range_mm):
    min_pixel_step = 50
    min_mm_step = min_pixel_step / scale_factor
    step = 1
    while step < min_mm_step:
        if step * 5 >= min_mm_step:
            step *= 5
        elif step * 2 >= min_mm_step:
            step *= 2
        else:
            step *= 10
    return max(1, int(step))


def draw_rulers():
    wa_x1 = WORKAREA_OFFSET_X
    wa_y1 = WORKAREA_OFFSET_Y
    wa_x2 = WORKAREA_OFFSET_X + WORKAREA_WIDTH
    wa_y2 = WORKAREA_OFFSET_Y + WORKAREA_HEIGHT

    ruler_y = wa_y2 + 5
    visible_start_x = offset_x - (WORKAREA_WIDTH / (2 * scale_factor))
    visible_end_x = offset_x + (WORKAREA_WIDTH / (2 * scale_factor))
    step_x = determine_ruler_step(visible_end_x - visible_start_x)
    first_tick_x = step_x * math.floor(visible_start_x / step_x)
    last_tick_x = step_x * math.ceil(visible_end_x / step_x)
    for x_mm in range(first_tick_x, last_tick_x + 1, step_x):
        if x_mm < X_MIN or x_mm > X_MAX:
            continue
        real_x = to_real_x(x_mm)
        if wa_x1 <= real_x <= wa_x2:
            canvas.create_line(real_x, ruler_y, real_x, ruler_y + 10, fill="black")
            canvas.create_text(real_x, ruler_y + 15,
                               text=f"{x_mm:.0f}", anchor="n", font=("Arial", 8))

    visible_start_y = offset_y - (WORKAREA_HEIGHT / (2 * scale_factor))
    visible_end_y = offset_y + (WORKAREA_HEIGHT / (2 * scale_factor))
    step_y = determine_ruler_step(visible_end_y - visible_start_y)
    first_tick_y = step_y * math.floor(visible_start_y / step_y)
    last_tick_y = step_y * math.ceil(visible_end_y / step_y)
    for y_mm in range(first_tick_y, last_tick_y + 1, step_y):
        if y_mm < Y_MIN or y_mm > Y_MAX:
            continue
        real_y = to_real_y(y_mm)
        if wa_y1 <= real_y <= wa_y2:
            canvas.create_line(wa_x1 - 20, real_y, wa_x1 - 10, real_y, fill="black")
            canvas.create_text(wa_x1 - 25, real_y,
                               text=f"{y_mm:.0f}", anchor="e", font=("Arial", 8))


def clip_line(x1, y1, x2, y2, xmin, ymin, xmax, ymax):
    INSIDE, LEFT, RIGHT, BOTTOM, TOP = 0, 1, 2, 4, 8

    def compute_code(x, y):
        code = INSIDE
        if x < xmin:
            code |= LEFT
        elif x > xmax:
            code |= RIGHT
        if y < ymin:
            code |= TOP
        elif y > ymax:
            code |= BOTTOM
        return code

    code1 = compute_code(x1, y1)
    code2 = compute_code(x2, y2)
    while True:
        if not (code1 | code2):
            return (x1, y1, x2, y2)
        elif code1 & code2:
            return (None, None, None, None)
        else:
            code_out = code1 if code1 else code2
            if code_out & TOP:
                x = x1 + (x2 - x1) * (ymin - y1) / (y2 - y1) if y2 != y1 else x1
                y = ymin
            elif code_out & BOTTOM:
                x = x1 + (x2 - x1) * (ymax - y1) / (y2 - y1) if y2 != y1 else x1
                y = ymax
            elif code_out & RIGHT:
                y = y1 + (y2 - y1) * (xmax - x1) / (x2 - x1) if x2 != x1 else y1
                x = xmax
            elif code_out & LEFT:
                y = y1 + (y2 - y1) * (xmin - x1) / (x2 - x1) if x2 != x1 else y1
                x = xmin
            if code_out == code1:
                x1, y1 = x, y
                code1 = compute_code(x1, y1)
            else:
                x2, y2 = x, y
                code2 = compute_code(x2, y2)


def is_in_workarea(rx, ry):
    return (WORKAREA_OFFSET_X <= rx <= WORKAREA_OFFSET_X + WORKAREA_WIDTH and
            WORKAREA_OFFSET_Y <= ry <= WORKAREA_OFFSET_Y + WORKAREA_HEIGHT)


def redraw_grid(event=None):
    if viz_mode:
        redraw_viz(viz_play_index)
        return
    canvas.delete("all")

    wa_x1 = WORKAREA_OFFSET_X
    wa_y1 = WORKAREA_OFFSET_Y
    wa_x2 = WORKAREA_OFFSET_X + WORKAREA_WIDTH
    wa_y2 = WORKAREA_OFFSET_Y + WORKAREA_HEIGHT

    canvas.create_rectangle(0, 0, CANVAS_WIDTH + 500, CANVAS_HEIGHT + 500,
                            fill="#F0F0F0", outline="")
    canvas.create_rectangle(wa_x1, wa_y1, wa_x2, wa_y2, fill="white", outline="")

    grid_step_mm = get_grid_step_mm()
    visible_start_x = offset_x - (WORKAREA_WIDTH / (2 * scale_factor))
    visible_end_x = offset_x + (WORKAREA_WIDTH / (2 * scale_factor))
    first_line_x = grid_step_mm * math.floor(visible_start_x / grid_step_mm)
    last_line_x = grid_step_mm * math.ceil(visible_end_x / grid_step_mm)
    for x_mm in range(first_line_x, last_line_x + 1, grid_step_mm):
        real_x = to_real_x(x_mm)
        if wa_x1 <= real_x <= wa_x2:
            canvas.create_line(real_x, wa_y1, real_x, wa_y2, fill="lightgray")

    visible_start_y = offset_y - (WORKAREA_HEIGHT / (2 * scale_factor))
    visible_end_y = offset_y + (WORKAREA_HEIGHT / (2 * scale_factor))
    first_line_y = grid_step_mm * math.floor(visible_start_y / grid_step_mm)
    last_line_y = grid_step_mm * math.ceil(visible_end_y / grid_step_mm)
    for y_mm in range(first_line_y, last_line_y + 1, grid_step_mm):
        real_y = to_real_y(y_mm)
        if wa_y1 <= real_y <= wa_y2:
            canvas.create_line(wa_x1, real_y, wa_x2, real_y, fill="lightgray")

    colors = ['red', 'green', 'blue', 'orange', 'purple', 'cyan', 'magenta', 'yellow']
    slot_colors = ['#FF69B4', '#00CED1', '#FFD700', '#8B4513', '#DC143C', '#00FF7F']

    if current_tools:
        for i, (tool, data) in enumerate(current_tools.items()):
            if not data['visible']:
                continue
            color = colors[i % len(colors)]
            is_hovered = (hovered_tool == (tool, 'holes'))
            for x_mm, y_mm in data['holes']:
                real_x = to_real_x(x_mm)
                real_y = to_real_y(y_mm)
                if is_in_workarea(real_x, real_y):
                    if is_hovered:
                        # Ореол подсветки
                        canvas.create_oval(real_x - 6, real_y - 6,
                                           real_x + 6, real_y + 6,
                                           fill="", outline="white", width=3)
                        canvas.create_oval(real_x - 5, real_y - 5,
                                           real_x + 5, real_y + 5,
                                           fill=color, outline=color)
                    else:
                        canvas.create_oval(real_x - 2, real_y - 2,
                                           real_x + 2, real_y + 2,
                                           fill=color, outline=color)

        if show_paths_var and show_paths_var.get():
            for i, (tool, data) in enumerate(current_tools.items()):
                if not data['visible'] or len(data['holes']) < 2:
                    continue
                color = colors[i % len(colors)]
                holes = data['holes']
                for j in range(len(holes) - 1):
                    r_x1 = to_real_x(holes[j][0])
                    r_y1 = to_real_y(holes[j][1])
                    r_x2 = to_real_x(holes[j + 1][0])
                    r_y2 = to_real_y(holes[j + 1][1])
                    clipped = clip_line(r_x1, r_y1, r_x2, r_y2,
                                        wa_x1, wa_y1, wa_x2, wa_y2)
                    if clipped[0] is not None:
                        canvas.create_line(clipped[0], clipped[1],
                                           clipped[2], clipped[3],
                                           fill=color, width=1)

    if slot_tools:
        for i, (tool, data) in enumerate(slot_tools.items()):
            if not data['visible']:
                continue
            color = slot_colors[i % len(slot_colors)]
            diameter = data['diameter']
            r_px = max(2, (diameter / 2) * scale_factor)
            is_hovered = (hovered_tool == (tool, 'slots'))

            for start, end in data['slots']:
                real_sx = to_real_x(start[0])
                real_sy = to_real_y(start[1])
                real_ex = to_real_x(end[0])
                real_ey = to_real_y(end[1])

                line_w = max(1, int(diameter * scale_factor))
                if is_hovered:
                    # Обводка-ореол
                    clipped_h = clip_line(real_sx, real_sy, real_ex, real_ey,
                                          wa_x1, wa_y1, wa_x2, wa_y2)
                    if clipped_h[0] is not None:
                        canvas.create_line(clipped_h[0], clipped_h[1],
                                           clipped_h[2], clipped_h[3],
                                           fill="white", width=line_w + 4,
                                           capstyle=tk.ROUND)
                clipped = clip_line(real_sx, real_sy, real_ex, real_ey,
                                    wa_x1, wa_y1, wa_x2, wa_y2)
                if clipped[0] is not None:
                    canvas.create_line(clipped[0], clipped[1],
                                       clipped[2], clipped[3],
                                       fill=color, width=line_w,
                                       capstyle=tk.ROUND)

                if is_in_workarea(real_sx, real_sy):
                    canvas.create_oval(real_sx - r_px, real_sy - r_px,
                                       real_sx + r_px, real_sy + r_px,
                                       outline=color, width=1)
                    canvas.create_oval(real_sx - 2, real_sy - 2,
                                       real_sx + 2, real_sy + 2,
                                       fill=color, outline=color)
                if is_in_workarea(real_ex, real_ey):
                    canvas.create_oval(real_ex - r_px, real_ey - r_px,
                                       real_ex + r_px, real_ey + r_px,
                                       outline=color, width=1)
                    canvas.create_oval(real_ex - 2, real_ey - 2,
                                       real_ex + 2, real_ey + 2,
                                       fill=color, outline=color)

            if show_paths_var and show_paths_var.get() and len(data['slots']) > 1:
                for j in range(len(data['slots']) - 1):
                    _, prev_end = data['slots'][j]
                    next_start, _ = data['slots'][j + 1]
                    r_pe_x = to_real_x(prev_end[0])
                    r_pe_y = to_real_y(prev_end[1])
                    r_ns_x = to_real_x(next_start[0])
                    r_ns_y = to_real_y(next_start[1])
                    clipped = clip_line(r_pe_x, r_pe_y, r_ns_x, r_ns_y,
                                        wa_x1, wa_y1, wa_x2, wa_y2)
                    if clipped[0] is not None:
                        canvas.create_line(clipped[0], clipped[1],
                                           clipped[2], clipped[3],
                                           fill=color, width=1, dash=(4, 4))

    canvas.create_rectangle(wa_x1, wa_y1, wa_x2, wa_y2, outline="black", width=2)
    draw_rulers()


# ==========================================================
# G-code визуализатор — парсер и 2.5D рендер
# ==========================================================

def parse_gcode_for_viz(gcode_text):
    """
    Парсит текст G-code и возвращает список сегментов движения:
    {'type': 'rapid'|'feed'|'drill_down'|'drill_up'|'slot_h',
     'x0','y0','z0','x1','y1','z1', 'tool', 'diameter'}
    """
    segments = []
    cx, cy, cz = 0.0, 0.0, 0.0
    cur_tool = '?'
    cur_diameter = 0.0
    tool_diameter_map = {}

    for raw in gcode_text.splitlines():
        line = raw.strip()
        if not line or line.startswith(';'):
            # Извлекаем диаметр из комментария: ; Tool T1 D=0.80mm
            m = re.match(r';\s*Tool\s+T(\d+)\s+D=([\d.]+)mm', line)
            if m:
                tool_diameter_map[m.group(1)] = float(m.group(2))
            continue

        # Смена инструмента M00 — просто фиксируем
        if line == 'M00':
            continue

        # Распознаём T<n> в теле (если вдруг)
        tm = re.match(r'^T(\d+)', line)
        if tm:
            cur_tool = tm.group(1)
            cur_diameter = tool_diameter_map.get(cur_tool, 0.0)

        # Извлекаем X, Y, Z из строки
        xm = re.search(r'X([+-]?[\d.]+)', line)
        ym = re.search(r'Y([+-]?[\d.]+)', line)
        zm = re.search(r'Z([+-]?[\d.]+)', line)

        nx = float(xm.group(1)) if xm else cx
        ny = float(ym.group(1)) if ym else cy
        nz = float(zm.group(1)) if zm else cz

        # Определяем тип сегмента
        if line.startswith('G00'):
            if zm and not xm and not ym:
                seg_type = 'drill_up' if nz > cz else 'drill_down'
            else:
                seg_type = 'rapid'
        elif line.startswith('G01'):
            if zm and not xm and not ym:
                seg_type = 'drill_down' if nz < cz else 'drill_up'
            elif xm or ym:
                seg_type = 'slot_h'
            else:
                seg_type = 'feed'
        else:
            cx, cy, cz = nx, ny, nz
            continue

        # Ищем инструмент по последнему комментарию перед блоком
        segments.append({
            'type': seg_type,
            'x0': cx, 'y0': cy, 'z0': cz,
            'x1': nx, 'y1': ny, 'z1': nz,
            'tool': cur_tool,
            'diameter': cur_diameter,
        })
        cx, cy, cz = nx, ny, nz

    # Привязываем диаметры по инструментам ретроспективно
    # (комментарий идёт ДО блока, так что порядок уже верный)
    # Второй проход — уточнить cur_tool по блокам
    cur_tool = '?'
    cur_diameter = 0.0
    tool_comment_re = re.compile(r';\s*Tool\s+T(\d+)\s+D=([\d.]+)mm')
    change_re = re.compile(r';\s*Change to\s+T(\d+)')
    seg_idx = 0
    for raw in gcode_text.splitlines():
        line = raw.strip()
        m = tool_comment_re.match(line)
        if m:
            cur_tool = m.group(1)
            cur_diameter = float(m.group(2))
        mc = change_re.match(line)
        if mc:
            cur_tool = mc.group(1)
            cur_diameter = tool_diameter_map.get(cur_tool, cur_diameter)
        if line.startswith('G00') or line.startswith('G01'):
            if seg_idx < len(segments):
                segments[seg_idx]['tool'] = cur_tool
                segments[seg_idx]['diameter'] = cur_diameter
                seg_idx += 1

    return segments


# Цвета для инструментов в режиме визуализации
VIZ_TOOL_COLORS = [
    '#E74C3C', '#2ECC71', '#3498DB', '#F39C12',
    '#9B59B6', '#1ABC9C', '#E67E22', '#34495E',
]

def _viz_tool_color(tool_key, tool_color_map):
    if tool_key not in tool_color_map:
        idx = len(tool_color_map) % len(VIZ_TOOL_COLORS)
        tool_color_map[tool_key] = VIZ_TOOL_COLORS[idx]
    return tool_color_map[tool_key]


# Кабинетная проекция: (x,y,z) → (px, py) на канвасе
# Угол 30°, коэффициент глубины 0.5
_CAB_AX = math.cos(math.radians(30)) * 0.45
_CAB_AY = math.sin(math.radians(30)) * 0.45

def viz_project(x_mm, y_mm, z_mm, sf, ox, oy):
    """
    Проекция точки в мм → пиксели канваса.
    sf — scale_factor, ox/oy — offset виртуального поля.
    """
    cx_c = WORKAREA_OFFSET_X + WORKAREA_WIDTH / 2
    cy_c = WORKAREA_OFFSET_Y + WORKAREA_HEIGHT / 2

    # Базовые 2D координаты (как в основном виде)
    px = cx_c + (x_mm - ox) * sf
    py = cy_c - (y_mm - oy) * sf

    # Сдвиг по Z через кабинетную проекцию
    px += z_mm * _CAB_AX * sf * 0.15
    py -= z_mm * _CAB_AY * sf * 0.15  # вверх = меньше py

    return px, py


def redraw_viz(play_idx=None):
    """Перерисовка канваса в режиме 2.5D визуализации."""
    canvas.delete("all")

    wa_x1 = WORKAREA_OFFSET_X
    wa_y1 = WORKAREA_OFFSET_Y
    wa_x2 = WORKAREA_OFFSET_X + WORKAREA_WIDTH
    wa_y2 = WORKAREA_OFFSET_Y + WORKAREA_HEIGHT

    # Единый фон на весь канвас
    canvas.create_rectangle(0, 0, CANVAS_WIDTH + 500, CANVAS_HEIGHT + 500,
                             fill="#1A1A2E", outline="")

    segs = viz_gcode_lines
    if not segs:
        canvas.create_text(CANVAS_WIDTH // 2, CANVAS_HEIGHT // 2,
                           text="Нет данных G-code", fill="gray",
                           font=("Arial", 14))
        return

    tool_color_map = {}
    n = len(segs)
    end_idx = play_idx if play_idx is not None else n

    # Используем глобальные viz_sf / viz_ox / viz_oy (устанавливаются при входе,
    # затем обновляются зумом и паном)
    sf = viz_sf
    ox = viz_ox
    oy = viz_oy

    def vp(x_mm, y_mm, z_mm=0.0):
        cx_c = WORKAREA_OFFSET_X + WORKAREA_WIDTH / 2
        cy_c = WORKAREA_OFFSET_Y + WORKAREA_HEIGHT / 2
        px = cx_c + (x_mm - ox) * sf
        py = cy_c - (y_mm - oy) * sf
        px += z_mm * _CAB_AX * sf * 0.15
        py -= z_mm * _CAB_AY * sf * 0.15
        return px, py

    # Bbox платы из всех сегментов
    xs = [s['x0'] for s in segs] + [s['x1'] for s in segs]
    ys = [s['y0'] for s in segs] + [s['y1'] for s in segs]
    bx0, bx1 = min(xs) - 3, max(xs) + 3
    by0, by1 = min(ys) - 3, max(ys) + 3

    # --- Плата ---
    board_z_top, board_z_bot = 0.0, -0.5
    corners_top = [vp(bx0, by0, board_z_top), vp(bx1, by0, board_z_top),
                   vp(bx1, by1, board_z_top), vp(bx0, by1, board_z_top)]
    corners_bot = [vp(bx0, by0, board_z_bot), vp(bx1, by0, board_z_bot),
                   vp(bx1, by1, board_z_bot), vp(bx0, by1, board_z_bot)]

    flat_top  = [c for pt in corners_top for c in pt]
    flat_sf_p = [c for pt in [corners_top[0], corners_top[1],
                               corners_bot[1], corners_bot[0]] for c in pt]
    flat_sr_p = [c for pt in [corners_top[1], corners_top[2],
                               corners_bot[2], corners_bot[1]] for c in pt]

    if len(flat_sf_p) >= 8:
        canvas.create_polygon(flat_sf_p, fill="#1B4332", outline="#2D6A4F", width=1)
    if len(flat_sr_p) >= 8:
        canvas.create_polygon(flat_sr_p, fill="#1B4332", outline="#2D6A4F", width=1)
    if len(flat_top) >= 8:
        canvas.create_polygon(flat_top, fill="#2D6A4F", outline="#40916C", width=1)

    # --- Траектории ---
    completed_slots = []
    pending_slot_start = None

    for i, seg in enumerate(segs):
        if i >= end_idx:
            break
        t = seg['type']
        col = _viz_tool_color(seg['tool'], tool_color_map)
        p0 = vp(seg['x0'], seg['y0'], seg['z0'])
        p1 = vp(seg['x1'], seg['y1'], seg['z1'])

        if t == 'rapid':
            canvas.create_line(p0[0], p0[1], p1[0], p1[1],
                                fill="#555577", width=1, dash=(4, 4))
            pending_slot_start = None
        elif t == 'drill_down':
            canvas.create_line(p0[0], p0[1], p1[0], p1[1], fill=col, width=2)
            d_px = max(2, seg['diameter'] * sf * 0.5)
            pending_slot_start = (seg['x1'], seg['y1'], seg['diameter'], col, p1, d_px)
        elif t == 'drill_up':
            canvas.create_line(p0[0], p0[1], p1[0], p1[1], fill="#888899", width=1)
            if pending_slot_start:
                _sx, _sy, _diam, _scol, _sp1, _sd_px = pending_slot_start
                canvas.create_oval(_sp1[0]-_sd_px, _sp1[1]-_sd_px,
                                    _sp1[0]+_sd_px, _sp1[1]+_sd_px,
                                    fill="#0D0D0D", outline=_scol, width=1)
                pending_slot_start = None
        elif t == 'slot_h':
            if pending_slot_start:
                sx, sy, diam, scol, _p, _d = pending_slot_start
                completed_slots.append((sx, sy, seg['x1'], seg['y1'], diam, scol))
                pending_slot_start = None
            else:
                lw = max(2, int(seg['diameter'] * sf * 0.4))
                canvas.create_line(p0[0], p0[1], p1[0], p1[1],
                                    fill=col, width=lw, capstyle=tk.ROUND)

    # Овальные прорези
    for sx, sy, ex, ey, diam, col in completed_slots:
        d_px = max(2, diam * sf * 0.5)
        ps = vp(sx, sy, 0.0)
        pe = vp(ex, ey, 0.0)
        length_px = math.hypot(pe[0]-ps[0], pe[1]-ps[1])
        if length_px < 1:
            canvas.create_oval(ps[0]-d_px, ps[1]-d_px, ps[0]+d_px, ps[1]+d_px,
                                fill="#0D0D0D", outline=col, width=1)
            continue
        lw = max(4, int(2 * d_px))
        # Контур (outline)
        canvas.create_line(ps[0], ps[1], pe[0], pe[1],
                            fill=col, width=lw+2, capstyle=tk.ROUND)
        # Заливка (fill)
        canvas.create_line(ps[0], ps[1], pe[0], pe[1],
                            fill="#0D0D0D", width=lw, capstyle=tk.ROUND)

    # --- Головка инструмента ---
    if end_idx > 0 and end_idx <= n:
        last = segs[end_idx - 1]
        hx, hy = vp(last['x1'], last['y1'], last['z1'])
        col = _viz_tool_color(last['tool'], tool_color_map)
        canvas.create_oval(hx-8, hy-8, hx+8, hy+8, fill="", outline="white", width=2)
        canvas.create_oval(hx-4, hy-4, hx+4, hy+4, fill=col, outline=col)
        canvas.create_text(hx+12, hy-10,
                            text=f"X{last['x1']:.2f} Y{last['y1']:.2f} Z{last['z1']:.2f}",
                            fill="white", font=("Arial", 8), anchor="w")

    if tool_color_map:
        lx, ly = CANVAS_WIDTH - 10, 10
        for tool_key, col in tool_color_map.items():
            canvas.create_rectangle(lx-60, ly, lx-48, ly+10, fill=col, outline="")
            canvas.create_text(lx-44, ly+5, text=f"T{tool_key}",
                                fill="white", font=("Arial", 8), anchor="w")
            ly += 14


# ---- Плеер ----

def viz_player_step():
    """Один шаг анимации."""
    global viz_play_index, viz_playing, viz_after_id
    if not viz_playing:
        return
    viz_play_index += 1
    n = len(viz_gcode_lines)
    if viz_play_index > n:
        viz_play_index = n
        viz_playing = False
        viz_btn_play.config(text="▶")
        _viz_slider_set(n)
        redraw_viz(n)
        return

    redraw_viz(viz_play_index)
    _viz_slider_set(viz_play_index)
    viz_pos_label.config(text=f"{viz_play_index} / {n}")

    # Скорость: ползунок viz_speed_var (1–20, default 5)
    delay = max(10, int(300 / viz_speed_var.get()))
    viz_after_id = canvas.after(delay, viz_player_step)


def viz_play_pause():
    global viz_playing, viz_after_id
    if viz_playing:
        viz_playing = False
        if viz_after_id:
            canvas.after_cancel(viz_after_id)
            viz_after_id = None
        viz_btn_play.config(text="▶")
    else:
        if viz_play_index >= len(viz_gcode_lines):
            viz_stop()
        viz_playing = True
        viz_btn_play.config(text="⏸")
        viz_player_step()


def viz_stop():
    global viz_playing, viz_play_index, viz_after_id
    viz_playing = False
    if viz_after_id:
        canvas.after_cancel(viz_after_id)
        viz_after_id = None
    viz_play_index = 0
    viz_btn_play.config(text="▶")
    _viz_slider_set(0)
    redraw_viz(0)


def _viz_slider_set(val):
    """Установить позицию слайдера из кода."""
    viz_slider.set(val)


def enter_viz_mode():
    """Переключиться в режим 2.5D визуализации."""
    global viz_mode, viz_play_index, viz_playing, viz_sf, viz_ox, viz_oy
    viz_mode = True
    viz_play_index = 0
    viz_playing = False
    viz_btn_play.config(text="▶")

    # Автомасштаб — вписать плату в 85% рабочей области
    segs = viz_gcode_lines
    if segs:
        xs = [s['x0'] for s in segs] + [s['x1'] for s in segs]
        ys = [s['y0'] for s in segs] + [s['y1'] for s in segs]
        bx0, bx1 = min(xs) - 3, max(xs) + 3
        by0, by1 = min(ys) - 3, max(ys) + 3
        bw = max(bx1 - bx0, 1)
        bh = max(by1 - by0, 1)
        viz_sf = min(WORKAREA_WIDTH * 0.85 / bw, WORKAREA_HEIGHT * 0.85 / bh)
        viz_ox = (bx0 + bx1) / 2
        viz_oy = (by0 + by1) / 2

    n = len(viz_gcode_lines)
    viz_slider.config(to=max(1, n))
    _viz_slider_set(0)

    viz_player_frame.pack(side="bottom", fill="x", before=canvas)
    btn_visualize.config(text="◀ Назад")

    # Переключаем мышь на визуализатор
    canvas.bind("<ButtonPress-1>", on_viz_drag_start)
    canvas.bind("<B1-Motion>",     on_viz_drag)
    canvas.bind("<MouseWheel>",    on_viz_mousewheel)
    canvas.bind("<Button-4>",
                lambda e: on_viz_mousewheel(
                    type('Event', (), {'delta': 120, 'x': e.x, 'y': e.y})()))
    canvas.bind("<Button-5>",
                lambda e: on_viz_mousewheel(
                    type('Event', (), {'delta': -120, 'x': e.x, 'y': e.y})()))

    redraw_viz(n)
    status_label.config(text=f"Режим визуализации | {n} сегментов G-code")


def on_viz_mousewheel(event):
    """Зум в режиме визуализации — колесо мыши."""
    global viz_sf, viz_ox, viz_oy
    cx_c = WORKAREA_OFFSET_X + WORKAREA_WIDTH / 2
    cy_c = WORKAREA_OFFSET_Y + WORKAREA_HEIGHT / 2
    # Точка под курсором в мм
    mx = viz_ox + (event.x - cx_c) / viz_sf
    my = viz_oy - (event.y - cy_c) / viz_sf
    factor = 1.1 if event.delta > 0 else 0.9
    new_sf = max(0.5, min(viz_sf * factor, 2000.0))
    viz_ox = mx - (event.x - cx_c) / new_sf
    viz_oy = my + (event.y - cy_c) / new_sf
    viz_sf = new_sf
    redraw_viz(viz_play_index)


def on_viz_drag_start(event):
    global drag_start_real_x, drag_start_real_y, initial_offset_x, initial_offset_y
    drag_start_real_x = event.x
    drag_start_real_y = event.y
    initial_offset_x = viz_ox
    initial_offset_y = viz_oy


def on_viz_drag(event):
    global viz_ox, viz_oy
    viz_ox = initial_offset_x - (event.x - drag_start_real_x) / viz_sf
    viz_oy = initial_offset_y + (event.y - drag_start_real_y) / viz_sf
    redraw_viz(viz_play_index)


def exit_viz_mode():
    """Выйти из режима визуализации."""
    global viz_mode, viz_playing, viz_after_id
    viz_mode = False
    viz_playing = False
    if viz_after_id:
        canvas.after_cancel(viz_after_id)
        viz_after_id = None
    viz_player_frame.pack_forget()
    btn_visualize.config(text="🎬 Визуализация G-code")

    # Возвращаем стандартные биндинги мыши
    canvas.bind("<ButtonPress-1>", start_drag)
    canvas.bind("<B1-Motion>",     during_drag)
    canvas.bind("<MouseWheel>",    on_mousewheel)
    canvas.bind("<Button-4>",
                lambda e: on_mousewheel(
                    type('Event', (), {'delta': 120, 'x': e.x, 'y': e.y})()))
    canvas.bind("<Button-5>",
                lambda e: on_mousewheel(
                    type('Event', (), {'delta': -120, 'x': e.x, 'y': e.y})()))

    redraw_grid()
    status_label.config(text="Режим просмотра")


def toggle_viz_mode():
    if viz_mode:
        exit_viz_mode()
    else:
        if not viz_gcode_lines:
            messagebox.showwarning("Визуализация",
                                   "Сначала сгенерируйте G-код.")
            return
        enter_viz_mode()


def _store_gcode_for_viz(gcode_text):
    """Вызывается из генераторов — сохраняет G-code и активирует кнопку."""
    global viz_gcode_lines
    viz_gcode_lines = parse_gcode_for_viz(gcode_text)
    btn_visualize.config(state="normal")
    status_label.config(
        text=f"G-code готов ({len(viz_gcode_lines)} сег.). Нажмите «Визуализация».")


def update_legend():
    global hovered_tool, solo_tool
    hovered_tool = None
    solo_tool = None

    for widget in legend_frame.winfo_children():
        widget.destroy()
    colors = ['red', 'green', 'blue', 'orange', 'purple', 'cyan', 'magenta', 'yellow']
    slot_colors = ['#FF69B4', '#00CED1', '#FFD700', '#8B4513', '#DC143C', '#00FF7F']

    def make_context_menu(event):
        menu = tk.Menu(root, tearoff=0)
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
        if current_tools:
            for d in current_tools.values():
                d['visible'] = True
                if d['var']:
                    d['var'].set(True)
        if slot_tools:
            for d in slot_tools.values():
                d['visible'] = True
                if d['var']:
                    d['var'].set(True)
        _refresh_legend_highlight()
        redraw_grid()

    def legend_hide_all():
        if current_tools:
            for d in current_tools.values():
                d['visible'] = False
                if d['var']:
                    d['var'].set(False)
        if slot_tools:
            for d in slot_tools.values():
                d['visible'] = False
                if d['var']:
                    d['var'].set(False)
        _refresh_legend_highlight()
        redraw_grid()

    def legend_cancel_solo():
        global solo_tool
        solo_tool = None
        legend_show_all()

    def on_row_enter(event, tool, tool_type):
        global hovered_tool
        hovered_tool = (tool, tool_type)
        _refresh_legend_highlight()
        redraw_grid()

    def on_row_leave(event, tool, tool_type):
        global hovered_tool
        if hovered_tool == (tool, tool_type):
            hovered_tool = None
            _refresh_legend_highlight()
            redraw_grid()

    def on_solo_click(tool, tool_type):
        global solo_tool
        if solo_tool == (tool, tool_type):
            # Снять соло — вернуть всем видимость
            solo_tool = None
            if current_tools:
                for d in current_tools.values():
                    d['visible'] = True
                    if d['var']:
                        d['var'].set(True)
            if slot_tools:
                for d in slot_tools.values():
                    d['visible'] = True
                    if d['var']:
                        d['var'].set(True)
        else:
            solo_tool = (tool, tool_type)
            # Отключить всё кроме выбранного
            if current_tools:
                for t, d in current_tools.items():
                    vis = (tool_type == 'holes' and t == tool)
                    d['visible'] = vis
                    if d['var']:
                        d['var'].set(vis)
            if slot_tools:
                for t, d in slot_tools.items():
                    vis = (tool_type == 'slots' and t == tool)
                    d['visible'] = vis
                    if d['var']:
                        d['var'].set(vis)
        _refresh_legend_highlight()
        redraw_grid()

    # Хранилище строк легенды для последующей подсветки
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

        # Кнопка "соло" (👁)
        solo_btn = tk.Label(frame, text="👁", font=("Arial", 9), cursor="hand2",
                            relief="flat", padx=2)
        solo_btn.pack(side="left")
        solo_btn.bind("<Button-1>",
                      lambda e, t=tool, tt=tool_type: on_solo_click(t, tt))

        tk.Label(frame, text=icon_text, fg=color, font=("Arial", 12)).pack(side="left")
        lbl = tk.Label(frame, text=label_text, font=("Arial", 9))
        lbl.pack(side="left")

        # Hover-события на всех дочерних виджетах строки
        for w in [frame, cb, solo_btn, lbl]:
            w.bind("<Enter>", lambda e, t=tool, tt=tool_type: on_row_enter(e, t, tt))
            w.bind("<Leave>", lambda e, t=tool, tt=tool_type: on_row_leave(e, t, tt))
            w.bind("<Button-3>", make_context_menu)

        return frame

    # Привязка контекстного меню к самому legend_frame
    legend_frame.bind("<Button-3>", make_context_menu)

    if current_tools:
        hdr = tk.Label(legend_frame, text="Круглые отверстия:",
                       font=("Arial", 9, "bold"))
        hdr.pack(anchor="w")
        hdr.bind("<Button-3>", make_context_menu)
        for i, (tool, data) in enumerate(current_tools.items()):
            color = colors[i % len(colors)]
            text = f"T{tool} ⌀{data['diameter']:.2f}мм ({len(data['holes'])} отв.)"
            _build_row(legend_frame, tool, data, color, "●", text, 'holes')

    if slot_tools:
        sp = tk.Label(legend_frame, text="")
        sp.pack()
        sp.bind("<Button-3>", make_context_menu)
        hdr2 = tk.Label(legend_frame, text="Овальные отверстия (слоты):",
                        font=("Arial", 9, "bold"))
        hdr2.pack(anchor="w")
        hdr2.bind("<Button-3>", make_context_menu)
        for i, (tool, data) in enumerate(slot_tools.items()):
            color = slot_colors[i % len(slot_colors)]
            text = f"T{tool} ⌀{data['diameter']:.2f}мм ({len(data['slots'])} слот.)"
            _build_row(legend_frame, tool, data, color, "━", text, 'slots')

    if current_tools or slot_tools:
        sp2 = tk.Label(legend_frame, text="")
        sp2.pack()
        sp2.bind("<Button-3>", make_context_menu)
        total_holes = sum(len(d['holes']) for d in current_tools.values()) if current_tools else 0
        total_slots = sum(len(d['slots']) for d in slot_tools.values()) if slot_tools else 0
        ft = tk.Label(legend_frame,
                      text=f"Всего: {total_holes} отв. + {total_slots} слот.",
                      font=("Arial", 9, "bold"))
        ft.pack(anchor="w")
        ft.bind("<Button-3>", make_context_menu)

    # Функция подсветки строк (замыкание — знает legend_rows)
    def _refresh_legend_highlight():
        for key, frame in legend_rows.items():
            is_solo_active = solo_tool is not None
            is_this_solo = (solo_tool == key)
            is_hovered = (hovered_tool == key)

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

    # Делаем _refresh_legend_highlight доступной в замыканиях выше через nonlocal-трюк
    # Переопределяем on_row_enter/leave/solo через явное сохранение ссылки
    _stored_refresh = _refresh_legend_highlight
    legend_frame._refresh_highlight = _stored_refresh

    bind_mousewheel_to_children(legend_frame)


def _call_legend_refresh():
    """Вызвать подсветку легенды, если она ещё жива."""
    if hasattr(legend_frame, '_refresh_highlight'):
        legend_frame._refresh_highlight()


def toggle_tool_visibility(tool, tool_type):
    if tool_type == 'holes' and current_tools and tool in current_tools:
        current_tools[tool]['visible'] = current_tools[tool]['var'].get()
    elif tool_type == 'slots' and slot_tools and tool in slot_tools:
        slot_tools[tool]['visible'] = slot_tools[tool]['var'].get()
    redraw_grid()


def show_result_dialog(filename):
    dlg = tk.Toplevel(root)
    dlg.title("Готово")
    dlg.resizable(False, False)
    dlg.transient(root)
    dlg.grab_set()

    frm = tk.Frame(dlg, padx=20, pady=15)
    frm.pack()

    tk.Label(frm, text="G-код успешно сохранён:", font=("Arial", 10)).pack(pady=(0, 5))
    tk.Label(frm, text=os.path.basename(filename),
             font=("Arial", 10, "bold"), fg="darkgreen").pack()

    tk.Label(frm, text="Нажмите «🎬 Визуализация G-code» для просмотра.",
             font=("Arial", 9), fg="#555555").pack(pady=(8, 0))

    tk.Button(frm, text="OK", width=12, command=dlg.destroy).pack(pady=(10, 0))

    # Центрирование окна относительно главного окна
    dlg.update_idletasks()
    dlg_w = dlg.winfo_width()
    dlg_h = dlg.winfo_height()
    root_x = root.winfo_x()
    root_y = root.winfo_y()
    root_w = root.winfo_width()
    root_h = root.winfo_height()
    x = root_x + (root_w - dlg_w) // 2
    y = root_y + (root_h - dlg_h) // 2
    dlg.geometry(f"+{x}+{y}")


def write_tool_parking(f, park_z, rapid_rate):
    """Парковка после каждого инструмента для смены"""
    f.write("\n; Parking\n")
    f.write("; Spindle OFF\n")
    f.write("M05\n")
    f.write(f"G00 Z{park_z:.2f} F{rapid_rate:.0f}\n")
    f.write("G00 X0 Y0\n")


def write_tool_start(f, tool, diameter, count, unit, safe_z, rapid_rate):
    """Заголовок нового инструмента"""
    f.write(f"; Tool T{tool} D={diameter:.2f}mm ({count} {unit})\n")
    f.write(f"; Change to T{tool} D={diameter:.2f}mm\n")
    f.write("; Pause for tool change\n")
    f.write("M00\n")
    f.write("; Spindle ON\n")
    f.write("M03\n")
    f.write(f"G00 Z{safe_z:.2f} F{rapid_rate:.0f}\n")


def validate_gcode_params(safe_z, drill_z, feed_rate, rapid_rate, park_z):
    errors = []
    if safe_z <= 0:
        errors.append("Безопасная Z должна быть > 0")
    if drill_z >= 0:
        errors.append("Глубина сверления должна быть < 0")
    if feed_rate <= 0:
        errors.append("Подача должна быть > 0")
    if rapid_rate <= 0:
        errors.append("Быстрая подача должна быть > 0")
    if park_z < safe_z:
        errors.append("Парковка Z должна быть >= Безопасной Z")
    if errors:
        messagebox.showerror("Ошибка параметров", "\n".join(errors))
        return False
    return True


def generate_drilling_gcode():
    if not current_tools:
        messagebox.showwarning("Предупреждение", "Сначала загрузите файл Excellon с отверстиями.")
        return
    filename = filedialog.asksaveasfilename(
        defaultextension=".tap",
        filetypes=[("TAP files", "*.tap"), ("G-Code files", "*.gcode;*.nc;*.ngc"),
                   ("All files", "*.*")],
        title="Сохранить G-код сверления"
    )
    if not filename:
        return
    try:
        safe_z = float(safe_z_entry.get())
        drill_z = float(drill_z_entry.get())
        feed_rate = float(feed_rate_entry.get())
        rapid_rate = float(rapid_rate_entry.get())
        park_z = float(park_z_entry.get())
    except ValueError:
        messagebox.showerror("Ошибка", "Неверные параметры G-кода.")
        return
    if not validate_gcode_params(safe_z, drill_z, feed_rate, rapid_rate, park_z):
        return

    visible_tools = [(t, d) for t, d in current_tools.items()
                     if d['visible'] and d['holes']]
    if not visible_tools:
        messagebox.showwarning("Предупреждение", "Нет видимых отверстий для генерации.")
        return

    buf = io.StringIO()
    buf.write("; G-Code — Drilling only\n")
    buf.write(f"; Source: {os.path.basename(current_filename)}\n")
    buf.write("G21 ; Metric\n")
    buf.write("G90 ; Absolute coordinates\n\n")

    for idx, (tool, data) in enumerate(visible_tools):
        write_tool_start(buf, tool, data['diameter'], len(data['holes']),
                         "holes", safe_z, rapid_rate)
        for x_mm, y_mm in data['holes']:
            buf.write(f"G00 X{x_mm:.3f} Y{y_mm:.3f} F{rapid_rate:.0f}\n")
            buf.write(f"G01 Z{drill_z:.2f} F{feed_rate:.0f}\n")
            buf.write(f"G00 Z{safe_z:.2f} F{rapid_rate:.0f}\n")
        write_tool_parking(buf, park_z, rapid_rate)

    buf.write("M30\n")
    buf.write("; End program\n")

    gcode_text = buf.getvalue()
    with open(filename, 'w') as f:
        f.write(gcode_text)
    _store_gcode_for_viz(gcode_text)

    show_result_dialog(filename)


def generate_milling_gcode():
    if not slot_tools:
        messagebox.showwarning("Предупреждение", "Сначала загрузите файл SlotHoles.")
        return
    filename = filedialog.asksaveasfilename(
        defaultextension=".tap",
        filetypes=[("TAP files", "*.tap"), ("G-Code files", "*.gcode;*.nc;*.ngc"),
                   ("All files", "*.*")],
        title="Сохранить G-код фрезеровки слотов"
    )
    if not filename:
        return
    try:
        safe_z = float(safe_z_entry.get())
        drill_z = float(drill_z_entry.get())
        feed_rate = float(feed_rate_entry.get())
        mill_feed = float(mill_feed_entry.get())
        rapid_rate = float(rapid_rate_entry.get())
        park_z = float(park_z_entry.get())
    except ValueError:
        messagebox.showerror("Ошибка", "Неверные параметры G-кода.")
        return
    if not validate_gcode_params(safe_z, drill_z, feed_rate, rapid_rate, park_z):
        return

    visible_tools = [(t, d) for t, d in slot_tools.items()
                     if d['visible'] and d['slots']]
    if not visible_tools:
        messagebox.showwarning("Предупреждение", "Нет видимых слотов для генерации.")
        return

    buf = io.StringIO()
    buf.write("; G-Code — Slot milling only\n")
    buf.write(f"; Source: {os.path.basename(slot_filename)}\n")
    buf.write(f"; Milling feed: {mill_feed:.0f} mm/min\n")
    buf.write("G21 ; Metric\n")
    buf.write("G90 ; Absolute coordinates\n\n")

    for idx, (tool, data) in enumerate(visible_tools):
        write_tool_start(buf, tool, data['diameter'], len(data['slots']),
                         "slots", safe_z, rapid_rate)
        for slot_idx, (start, end) in enumerate(data['slots']):
            sx, sy = start
            ex, ey = end
            buf.write(f"; Slot {slot_idx + 1}\n")
            buf.write(f"G00 X{sx:.3f} Y{sy:.3f} F{rapid_rate:.0f}\n")
            buf.write(f"G01 Z{drill_z:.2f} F{feed_rate:.0f}\n")
            buf.write(f"G01 X{ex:.3f} Y{ey:.3f} F{mill_feed:.0f}\n")
            buf.write(f"G00 Z{safe_z:.2f} F{rapid_rate:.0f}\n")
        write_tool_parking(buf, park_z, rapid_rate)

    buf.write("M30\n")
    buf.write("; End program\n")

    gcode_text = buf.getvalue()
    with open(filename, 'w') as f:
        f.write(gcode_text)
    _store_gcode_for_viz(gcode_text)

    show_result_dialog(filename)


def generate_combined_gcode():
    if not current_tools and not slot_tools:
        messagebox.showwarning("Предупреждение", "Загрузите хотя бы один файл.")
        return
    filename = filedialog.asksaveasfilename(
        defaultextension=".tap",
        filetypes=[("TAP files", "*.tap"), ("G-Code files", "*.gcode;*.nc;*.ngc"),
                   ("All files", "*.*")],
        title="Сохранить объединённый G-код"
    )
    if not filename:
        return
    try:
        safe_z = float(safe_z_entry.get())
        drill_z = float(drill_z_entry.get())
        feed_rate = float(feed_rate_entry.get())
        mill_feed = float(mill_feed_entry.get())
        rapid_rate = float(rapid_rate_entry.get())
        park_z = float(park_z_entry.get())
    except ValueError:
        messagebox.showerror("Ошибка", "Неверные параметры G-кода.")
        return
    if not validate_gcode_params(safe_z, drill_z, feed_rate, rapid_rate, park_z):
        return

    buf = io.StringIO()
    buf.write("; G-Code — Combined: Drilling + Slot milling\n")
    if current_filename:
        buf.write(f"; Holes source: {os.path.basename(current_filename)}\n")
    if slot_filename:
        buf.write(f"; Slots source: {os.path.basename(slot_filename)}\n")
    buf.write(f"; Milling feed: {mill_feed:.0f} mm/min\n")
    buf.write("G21 ; Metric\n")
    buf.write("G90 ; Absolute coordinates\n\n")

    # Сверление
    if current_tools:
        buf.write("; ===== DRILLING SECTION =====\n\n")
        for tool, data in current_tools.items():
            if not data['visible'] or not data['holes']:
                continue
            write_tool_start(buf, tool, data['diameter'], len(data['holes']),
                             "holes", safe_z, rapid_rate)
            for x_mm, y_mm in data['holes']:
                buf.write(f"G00 X{x_mm:.3f} Y{y_mm:.3f} F{rapid_rate:.0f}\n")
                buf.write(f"G01 Z{drill_z:.2f} F{feed_rate:.0f}\n")
                buf.write(f"G00 Z{safe_z:.2f} F{rapid_rate:.0f}\n")
            write_tool_parking(buf, park_z, rapid_rate)

    # Фрезеровка слотов
    if slot_tools:
        buf.write("\n; ===== SLOT MILLING SECTION =====\n\n")
        for tool, data in slot_tools.items():
            if not data['visible'] or not data['slots']:
                continue
            write_tool_start(buf, tool, data['diameter'], len(data['slots']),
                             "slots", safe_z, rapid_rate)
            for slot_idx, (start, end) in enumerate(data['slots']):
                sx, sy = start
                ex, ey = end
                buf.write(f"; Slot {slot_idx + 1}\n")
                buf.write(f"G00 X{sx:.3f} Y{sy:.3f} F{rapid_rate:.0f}\n")
                buf.write(f"G01 Z{drill_z:.2f} F{feed_rate:.0f}\n")
                buf.write(f"G01 X{ex:.3f} Y{ey:.3f} F{mill_feed:.0f}\n")
                buf.write(f"G00 Z{safe_z:.2f} F{rapid_rate:.0f}\n")
            write_tool_parking(buf, park_z, rapid_rate)

    buf.write("M30\n")
    buf.write("; End program\n")

    gcode_text = buf.getvalue()
    with open(filename, 'w') as f:
        f.write(gcode_text)
    _store_gcode_for_viz(gcode_text)

    show_result_dialog(filename)


def on_show_paths_change():
    redraw_grid()


def show_statistics():
    if not current_tools and not slot_tools:
        messagebox.showinfo("Статистика", "Нет загруженных данных.")
        return

    all_points = []
    total_holes = 0
    total_slots = 0
    drill_tools_count = 0
    mill_tools_count = 0
    tool_lines = []

    if current_tools:
        for tool, data in current_tools.items():
            count = len(data['holes'])
            total_holes += count
            drill_tools_count += 1
            tool_lines.append(f"  T{tool}  D={data['diameter']:.2f}мм  {count} отв.")
            all_points.extend(data['holes'])

    if slot_tools:
        for tool, data in slot_tools.items():
            count = len(data['slots'])
            total_slots += count
            mill_tools_count += 1
            tool_lines.append(f"  T{tool}  D={data['diameter']:.2f}мм  {count} слот.")
            for start, end in data['slots']:
                all_points.append(start)
                all_points.append(end)

    if all_points:
        min_x = min(p[0] for p in all_points)
        max_x = max(p[0] for p in all_points)
        min_y = min(p[1] for p in all_points)
        max_y = max(p[1] for p in all_points)
        board_w = max_x - min_x
        board_h = max_y - min_y
    else:
        min_x = max_x = min_y = max_y = board_w = board_h = 0

    # Расчёт общего пути
    try:
        rapid_rate = float(rapid_rate_entry.get())
        feed_rate = float(feed_rate_entry.get())
        mill_feed = float(mill_feed_entry.get())
        safe_z = float(safe_z_entry.get())
        drill_z = float(drill_z_entry.get())
    except ValueError:
        rapid_rate = feed_rate = mill_feed = safe_z = drill_z = 0

    total_rapid = 0.0
    total_feed = 0.0
    z_travel_per_hole = abs(safe_z) + abs(drill_z)

    if current_tools:
        for tool, data in current_tools.items():
            holes = data['holes']
            if not holes:
                continue
            # Путь от 0,0 до первого отверстия
            total_rapid += math.sqrt(holes[0][0]**2 + holes[0][1]**2)
            for i in range(1, len(holes)):
                dx = holes[i][0] - holes[i-1][0]
                dy = holes[i][1] - holes[i-1][1]
                total_rapid += math.sqrt(dx**2 + dy**2)
            total_feed += z_travel_per_hole * 2 * len(holes)

    slot_feed_dist = 0.0
    if slot_tools:
        for tool, data in slot_tools.items():
            slots = data['slots']
            if not slots:
                continue
            total_rapid += math.sqrt(slots[0][0][0]**2 + slots[0][0][1]**2)
            for i in range(1, len(slots)):
                dx = slots[i][0][0] - slots[i-1][1][0]
                dy = slots[i][0][1] - slots[i-1][1][1]
                total_rapid += math.sqrt(dx**2 + dy**2)
            for start, end in slots:
                dx = end[0] - start[0]
                dy = end[1] - start[1]
                slot_feed_dist += math.sqrt(dx**2 + dy**2)
            total_feed += z_travel_per_hole * 2 * len(slots)

    # Время
    time_rapid = (total_rapid / rapid_rate * 60) if rapid_rate > 0 else 0
    time_drill_feed = (total_feed / feed_rate * 60) if feed_rate > 0 else 0
    time_mill_feed = (slot_feed_dist / mill_feed * 60) if mill_feed > 0 else 0
    total_time_sec = time_rapid + time_drill_feed + time_mill_feed
    minutes = int(total_time_sec // 60)
    seconds = int(total_time_sec % 60)

    text = (
        f"Размер платы:\n"
        f"  X: {min_x:.2f} ... {max_x:.2f} мм ({board_w:.2f} мм)\n"
        f"  Y: {min_y:.2f} ... {max_y:.2f} мм ({board_h:.2f} мм)\n\n"
        f"Отверстий: {total_holes} ({drill_tools_count} инстр.)\n"
        f"Слотов: {total_slots} ({mill_tools_count} инстр.)\n\n"
        f"Инструменты:\n" + "\n".join(tool_lines) + "\n\n"
        f"Путь инструмента:\n"
        f"  Быстрый ход (XY): {total_rapid:.1f} мм\n"
        f"  Рабочий ход (Z): {total_feed:.1f} мм\n"
        f"  Фрезеровка слотов: {slot_feed_dist:.1f} мм\n\n"
        f"Примерное время: {minutes} мин {seconds} сек"
    )
    messagebox.showinfo("Статистика", text)


def open_help():
    messagebox.showinfo("Справка",
        "Excellon To G-code с поддержкой слотов\n\n"
        "1. Загрузите Excellon файл с круглыми отверстиями\n"
        "2. Загрузите файл SlotHoles для овальных отверстий\n"
        "3. Настройте параметры G-кода\n"
        "4. Выберите нужную кнопку генерации\n\n"
        "Управление:\n"
        "   Колесо мыши — масштаб\n"
        "   Зажатая ЛКМ — перемещение поля\n"
        "   Чекбоксы — видимость инструментов\n\n"
        "Скорости в G-коде:\n"
        "   Сверление: опускание F=подача, подъём F=холостой\n"
        "   Фрезеровка: подвод F=холостой, опускание F=подача,\n"
        "   горизонталь F=подача фрезы, подъём F=холостой\n\n"
        "После каждого инструмента — парковка в (0, 0, Z парк)\n"
        "для смены инструмента.")


def bind_mousewheel_to_children(widget):
    widget.bind("<MouseWheel>", on_legend_mousewheel)
    widget.bind("<Button-4>", lambda e: legend_canvas.yview_scroll(-1, "units"))
    widget.bind("<Button-5>", lambda e: legend_canvas.yview_scroll(1, "units"))
    for child in widget.winfo_children():
        bind_mousewheel_to_children(child)


def on_legend_mousewheel(event):
    legend_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")


# ==========================================================
# Создание главного окна
# ==========================================================
root = tk.Tk()
root.title("Excellon To G-code: Сверление + Фрезеровка слотов 3.0")
root.geometry("1600x900")
root.minsize(1280, 800)

main_frame = tk.Frame(root)
main_frame.pack(fill="both", expand=True)

left_frame = tk.Frame(main_frame)
left_frame.pack(side="left", fill="both", expand=True)

canvas = tk.Canvas(left_frame, width=CANVAS_WIDTH, height=CANVAS_HEIGHT, bg="#F0F0F0")
canvas.pack(fill="both", expand=True, padx=5, pady=5)

right_frame = tk.Frame(main_frame, width=280)
right_frame.pack(side="right", fill="y", padx=5, pady=5)
right_frame.pack_propagate(False)

# --- Файлы ---
files_frame = tk.LabelFrame(right_frame, text="Файлы", padx=5, pady=5)
files_frame.pack(fill="x", padx=5, pady=2)

tk.Button(files_frame, text="📂 Открыть Excellon (отверстия)",
          command=choose_file).pack(fill="x", pady=2)
holes_file_label = tk.Label(files_frame, text="Отверстия: не загружены",
                            font=("Arial", 8), fg="gray")
holes_file_label.pack(anchor="w")

tk.Button(files_frame, text="📂 Открыть SlotHoles (слоты)",
          command=choose_slot_file).pack(fill="x", pady=2)
slot_file_label = tk.Label(files_frame, text="Слоты: не загружены",
                           font=("Arial", 8), fg="gray")
slot_file_label.pack(anchor="w")

format_frame = tk.Frame(files_frame)
format_frame.pack(fill="x", pady=2)
tk.Label(format_frame, text="Формат:").pack(side="left")
format_combobox = ttk.Combobox(format_frame, values=["2.4", "3.3", "4.2"], width=6)
format_combobox.set("4.2")
format_combobox.pack(side="left", padx=5)
format_combobox.bind("<<ComboboxSelected>>", on_format_change)

# --- Параметры G-кода ---
params_frame = tk.LabelFrame(right_frame, text="Параметры G-кода", padx=5, pady=5)
params_frame.pack(fill="x", padx=5, pady=2)

params = [
    ("Безопасная Z (мм):", "safe_z", "5.0"),
    ("Глубина (мм):", "drill_z", "-2.5"),
    ("Подача (мм/мин):", "feed_rate", "100"),
    ("Подача фрезы (мм/мин):", "mill_feed", "50"),
    ("Быстрая подача (мм/мин):", "rapid_rate", "500"),
    ("Парковка Z (мм):", "park_z", "30"),
]

param_entries = {}
for label_text, key, default in params:
    row = tk.Frame(params_frame)
    row.pack(fill="x", pady=1)
    tk.Label(row, text=label_text, width=22, anchor="w").pack(side="left")
    entry = tk.Entry(row, width=8)
    entry.insert(0, default)
    entry.pack(side="right")
    param_entries[key] = entry

safe_z_entry = param_entries["safe_z"]
drill_z_entry = param_entries["drill_z"]
feed_rate_entry = param_entries["feed_rate"]
mill_feed_entry = param_entries["mill_feed"]
rapid_rate_entry = param_entries["rapid_rate"]
park_z_entry = param_entries["park_z"]

# --- Отображение ---
options_frame = tk.LabelFrame(right_frame, text="Отображение", padx=5, pady=5)
options_frame.pack(fill="x", padx=5, pady=2)

show_paths_var = tk.BooleanVar(value=False)
tk.Checkbutton(options_frame, text="Отобразить пути",
               variable=show_paths_var, command=on_show_paths_change).pack(anchor="w")

# --- Кнопки генерации G-кода ---
gcode_frame = tk.LabelFrame(right_frame, text="Генерация G-кода", padx=5, pady=5)
gcode_frame.pack(fill="x", padx=5, pady=2)

tk.Button(gcode_frame, text="⚙ G-код сверления",
          command=generate_drilling_gcode, bg="#90EE90").pack(fill="x", pady=2)
tk.Button(gcode_frame, text="⚙ G-код фрезеровки слотов",
          command=generate_milling_gcode, bg="#87CEEB").pack(fill="x", pady=2)
tk.Button(gcode_frame, text="⚙ Объединённый G-код",
          command=generate_combined_gcode, bg="#FFD700").pack(fill="x", pady=2)

# Статистика и справка
tk.Button(right_frame, text="📊 Статистика", command=show_statistics).pack(
    fill="x", padx=5, pady=2)
tk.Button(right_frame, text="❓ Справка", command=open_help).pack(
    fill="x", padx=5, pady=2)

# --- Кнопка визуализации ---
btn_visualize = tk.Button(right_frame, text="🎬 Визуализация G-code",
                          command=toggle_viz_mode,
                          bg="#DDA0DD", state="disabled",
                          font=("Arial", 9, "bold"))
btn_visualize.pack(fill="x", padx=5, pady=4)

# --- Панель плеера (скрыта по умолчанию) ---
viz_player_frame = tk.Frame(left_frame, bg="#2C2C3E", pady=4)
# (пакуется/скрывается динамически в enter/exit_viz_mode)

viz_top_row = tk.Frame(viz_player_frame, bg="#2C2C3E")
viz_top_row.pack(fill="x", padx=6, pady=2)

viz_btn_stop = tk.Button(viz_top_row, text="⏹", width=3,
                          command=viz_stop, bg="#444466", fg="white",
                          relief="flat", font=("Arial", 11))
viz_btn_stop.pack(side="left", padx=2)

viz_btn_play = tk.Button(viz_top_row, text="▶", width=3,
                          command=viz_play_pause, bg="#444466", fg="white",
                          relief="flat", font=("Arial", 11))
viz_btn_play.pack(side="left", padx=2)

tk.Label(viz_top_row, text="Скорость:", bg="#2C2C3E",
         fg="#AAAACC", font=("Arial", 9)).pack(side="left", padx=(10, 2))
viz_speed_var = tk.IntVar(value=5)
viz_speed_scale = tk.Scale(viz_top_row, from_=1, to=20,
                            orient="horizontal", variable=viz_speed_var,
                            bg="#2C2C3E", fg="#AAAACC", highlightthickness=0,
                            troughcolor="#444466", length=100, showvalue=True)
viz_speed_scale.pack(side="left")

viz_pos_label = tk.Label(viz_top_row, text="0 / 0", bg="#2C2C3E",
                          fg="#AAAACC", font=("Arial", 9))
viz_pos_label.pack(side="right", padx=6)

viz_slider = tk.Scale(viz_player_frame, from_=0, to=1,
                       orient="horizontal",
                       bg="#2C2C3E", fg="#CCCCEE", highlightthickness=0,
                       troughcolor="#444466", showvalue=False)
viz_slider.pack(fill="x", padx=6, pady=(0, 2))

def _viz_slider_drag(event):
    """Пользователь тащит ползунок — обновляем кадр, но не трогаем автовоспроизведение."""
    global viz_play_index
    viz_play_index = int(viz_slider.get())
    viz_pos_label.config(text=f"{viz_play_index} / {len(viz_gcode_lines)}")
    redraw_viz(viz_play_index)

def _viz_slider_release(event):
    """Отпустили ползунок — останавливаем автовоспроизведение."""
    global viz_play_index, viz_playing, viz_after_id
    if viz_playing:
        viz_playing = False
        if viz_after_id:
            canvas.after_cancel(viz_after_id)
            viz_after_id = None
        viz_btn_play.config(text="▶")
    viz_play_index = int(viz_slider.get())
    viz_pos_label.config(text=f"{viz_play_index} / {len(viz_gcode_lines)}")
    redraw_viz(viz_play_index)

viz_slider.bind("<B1-Motion>", _viz_slider_drag)
viz_slider.bind("<ButtonRelease-1>", _viz_slider_release)

# --- Легенда с прокруткой ---
legend_outer_frame = tk.LabelFrame(right_frame, text="Инструменты", padx=5, pady=5)
legend_outer_frame.pack(fill="both", expand=True, padx=5, pady=2)

legend_canvas = tk.Canvas(legend_outer_frame, highlightthickness=0)
legend_scrollbar = tk.Scrollbar(legend_outer_frame, orient="vertical",
                                 command=legend_canvas.yview)
legend_frame = tk.Frame(legend_canvas)

legend_frame.bind("<Configure>",
                  lambda e: legend_canvas.configure(scrollregion=legend_canvas.bbox("all")))
legend_canvas.create_window((0, 0), window=legend_frame, anchor="nw")
legend_canvas.configure(yscrollcommand=legend_scrollbar.set)

legend_canvas.pack(side="left", fill="both", expand=True)
legend_scrollbar.pack(side="right", fill="y")

# --- События мыши ---
canvas.bind("<ButtonPress-1>", start_drag)
canvas.bind("<B1-Motion>", during_drag)
canvas.bind("<MouseWheel>", on_mousewheel)
canvas.bind("<Button-4>",
            lambda e: on_mousewheel(type('Event', (), {'delta': 120, 'x': e.x, 'y': e.y})()))
canvas.bind("<Button-5>",
            lambda e: on_mousewheel(type('Event', (), {'delta': -120, 'x': e.x, 'y': e.y})()))

# --- Строка состояния ---
status_frame = tk.Frame(root, bd=1, relief=tk.SUNKEN)
status_frame.pack(side="bottom", fill="x")
status_label = tk.Label(status_frame, text="Готово. Загрузите файл Excellon.",
                        anchor="w", font=("Arial", 9))
status_label.pack(side="left", padx=5)
coord_label = tk.Label(status_frame, text="X: --- Y: ---",
                        anchor="e", font=("Arial", 9))
coord_label.pack(side="right", padx=5)


def on_mouse_move(event):
    if (WORKAREA_OFFSET_X <= event.x <= WORKAREA_OFFSET_X + WORKAREA_WIDTH and
            WORKAREA_OFFSET_Y <= event.y <= WORKAREA_OFFSET_Y + WORKAREA_HEIGHT):
        vx = to_virtual_x(event.x)
        vy = to_virtual_y(event.y)
        coord_label.config(text=f"X: {vx:.2f} мм  Y: {vy:.2f} мм")
    else:
        coord_label.config(text="X: --- Y: ---")


canvas.bind("<Motion>", on_mouse_move)


def on_canvas_resize(event):
    global CANVAS_WIDTH, CANVAS_HEIGHT, WORKAREA_WIDTH, WORKAREA_HEIGHT
    CANVAS_WIDTH = event.width
    CANVAS_HEIGHT = event.height
    WORKAREA_WIDTH = max(100, CANVAS_WIDTH - 80)
    WORKAREA_HEIGHT = max(100, CANVAS_HEIGHT - 80)
    redraw_grid()


canvas.bind("<Configure>", on_canvas_resize)

redraw_grid()
root.mainloop()