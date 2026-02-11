# Импорт необходимых библиотек
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import re
import math
import webbrowser

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
    global current_tools, current_filename
    filename = filedialog.askopenfilename(
        filetypes=[("Excellon files", "*.txt;*.drl"), ("All files", "*.*")]
    )
    if not filename:
        return
    current_filename = filename
    if not is_excellon_file(filename):
        messagebox.showerror("Ошибка", "Неверный формат файла.")
        return
    try:
        current_tools = parse_excellon_file(filename)
        holes_file_label.config(text=f"Отверстия: {filename.split('/')[-1]}")
        auto_fit_scale()
        redraw_grid()
        update_legend()
        status_label.config(text=f"Загружен: {filename.split('/')[-1]}")
    except Exception as e:
        messagebox.showerror("Ошибка", f"Ошибка при чтении файла: {str(e)}")


def choose_slot_file():
    global slot_tools, slot_filename
    filename = filedialog.askopenfilename(
        filetypes=[("Excellon Slot files", "*.txt;*.drl"), ("All files", "*.*")]
    )
    if not filename:
        return
    slot_filename = filename
    if not is_excellon_file(filename):
        messagebox.showerror("Ошибка", "Неверный формат файла.")
        return
    try:
        slot_tools = parse_slot_file(filename)
        slot_file_label.config(text=f"Слоты: {filename.split('/')[-1]}")
        auto_fit_scale()
        redraw_grid()
        update_legend()
        status_label.config(text=f"Слоты загружены: {filename.split('/')[-1]}")
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
            for x_mm, y_mm in data['holes']:
                real_x = to_real_x(x_mm)
                real_y = to_real_y(y_mm)
                if is_in_workarea(real_x, real_y):
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

            for start, end in data['slots']:
                real_sx = to_real_x(start[0])
                real_sy = to_real_y(start[1])
                real_ex = to_real_x(end[0])
                real_ey = to_real_y(end[1])

                line_w = max(1, int(diameter * scale_factor))
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


def update_legend():
    for widget in legend_frame.winfo_children():
        widget.destroy()
    colors = ['red', 'green', 'blue', 'orange', 'purple', 'cyan', 'magenta', 'yellow']
    slot_colors = ['#FF69B4', '#00CED1', '#FFD700', '#8B4513', '#DC143C', '#00FF7F']

    if current_tools:
        tk.Label(legend_frame, text="Круглые отверстия:",
                 font=("Arial", 9, "bold")).pack(anchor="w")
        for i, (tool, data) in enumerate(current_tools.items()):
            color = colors[i % len(colors)]
            frame = tk.Frame(legend_frame)
            frame.pack(anchor="w", fill="x", padx=2)
            var = tk.BooleanVar(value=data['visible'])
            data['var'] = var
            cb = tk.Checkbutton(frame, variable=var,
                                command=lambda t=tool: toggle_tool_visibility(t, 'holes'))
            cb.pack(side="left")
            tk.Label(frame, text="●", fg=color, font=("Arial", 12)).pack(side="left")
            text = f"T{tool} ⌀{data['diameter']:.2f}мм ({len(data['holes'])} отв.)"
            tk.Label(frame, text=text, font=("Arial", 9)).pack(side="left")

    if slot_tools:
        tk.Label(legend_frame, text="").pack()
        tk.Label(legend_frame, text="Овальные отверстия (слоты):",
                 font=("Arial", 9, "bold")).pack(anchor="w")
        for i, (tool, data) in enumerate(slot_tools.items()):
            color = slot_colors[i % len(slot_colors)]
            frame = tk.Frame(legend_frame)
            frame.pack(anchor="w", fill="x", padx=2)
            var = tk.BooleanVar(value=data['visible'])
            data['var'] = var
            cb = tk.Checkbutton(frame, variable=var,
                                command=lambda t=tool: toggle_tool_visibility(t, 'slots'))
            cb.pack(side="left")
            tk.Label(frame, text="━", fg=color,
                     font=("Arial", 12, "bold")).pack(side="left")
            text = f"T{tool} ⌀{data['diameter']:.2f}мм ({len(data['slots'])} слот.)"
            tk.Label(frame, text=text, font=("Arial", 9)).pack(side="left")

    if current_tools or slot_tools:
        tk.Label(legend_frame, text="").pack()
        total_holes = sum(len(d['holes']) for d in current_tools.values()) if current_tools else 0
        total_slots = sum(len(d['slots']) for d in slot_tools.values()) if slot_tools else 0
        tk.Label(legend_frame, text=f"Всего: {total_holes} отв. + {total_slots} слот.",
                 font=("Arial", 9, "bold")).pack(anchor="w")

    bind_mousewheel_to_children(legend_frame)


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
    tk.Label(frm, text=filename.split('/')[-1],
             font=("Arial", 10, "bold"), fg="darkgreen").pack()

    link_frame = tk.Frame(frm)
    link_frame.pack(pady=10)
    tk.Label(link_frame, text="Проверить в симуляторе: ").pack(side="left")
    link = tk.Label(link_frame, text=SIMULATOR_URL, fg="blue", cursor="hand2",
                    font=("Arial", 10, "underline"))
    link.pack(side="left")
    link.bind("<Button-1>", lambda e: webbrowser.open(SIMULATOR_URL))

    tk.Button(frm, text="OK", width=12, command=dlg.destroy).pack(pady=(5, 0))

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

    visible_tools = [(t, d) for t, d in current_tools.items()
                     if d['visible'] and d['holes']]
    if not visible_tools:
        messagebox.showwarning("Предупреждение", "Нет видимых отверстий для генерации.")
        return

    with open(filename, 'w') as f:
        f.write("; G-Code — Drilling only\n")
        f.write(f"; Source: {current_filename.split('/')[-1]}\n")
        f.write("G21 ; Metric\n")
        f.write("G90 ; Absolute coordinates\n\n")

        for idx, (tool, data) in enumerate(visible_tools):
            write_tool_start(f, tool, data['diameter'], len(data['holes']),
                             "holes", safe_z, rapid_rate)
            for x_mm, y_mm in data['holes']:
                f.write(f"G00 X{x_mm:.3f} Y{y_mm:.3f} F{rapid_rate:.0f}\n")
                f.write(f"G01 Z{drill_z:.2f} F{feed_rate:.0f}\n")
                f.write(f"G00 Z{safe_z:.2f} F{rapid_rate:.0f}\n")

            # Парковка после каждого инструмента
            write_tool_parking(f, park_z, rapid_rate)

        f.write("M30\n")
        f.write("; End program\n")

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
        mill_feed = feed_rate / 2
        rapid_rate = float(rapid_rate_entry.get())
        park_z = float(park_z_entry.get())
    except ValueError:
        messagebox.showerror("Ошибка", "Неверные параметры G-кода.")
        return

    visible_tools = [(t, d) for t, d in slot_tools.items()
                     if d['visible'] and d['slots']]
    if not visible_tools:
        messagebox.showwarning("Предупреждение", "Нет видимых слотов для генерации.")
        return

    with open(filename, 'w') as f:
        f.write("; G-Code — Slot milling only\n")
        f.write(f"; Source: {slot_filename.split('/')[-1]}\n")
        f.write(f"; Milling feed: {mill_feed:.0f} mm/min (feed/2)\n")
        f.write("G21 ; Metric\n")
        f.write("G90 ; Absolute coordinates\n\n")

        for idx, (tool, data) in enumerate(visible_tools):
            write_tool_start(f, tool, data['diameter'], len(data['slots']),
                             "slots", safe_z, rapid_rate)
            for slot_idx, (start, end) in enumerate(data['slots']):
                sx, sy = start
                ex, ey = end
                f.write(f"; Slot {slot_idx + 1}\n")
                f.write(f"G00 X{sx:.3f} Y{sy:.3f} F{rapid_rate:.0f}\n")
                f.write(f"G01 Z{drill_z:.2f} F{feed_rate:.0f}\n")
                f.write(f"G01 X{ex:.3f} Y{ey:.3f} F{mill_feed:.0f}\n")
                f.write(f"G00 Z{safe_z:.2f} F{rapid_rate:.0f}\n")

            # Парковка после каждого инструмента
            write_tool_parking(f, park_z, rapid_rate)

        f.write("M30\n")
        f.write("; End program\n")

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
        mill_feed = feed_rate / 2
        rapid_rate = float(rapid_rate_entry.get())
        park_z = float(park_z_entry.get())
    except ValueError:
        messagebox.showerror("Ошибка", "Неверные параметры G-кода.")
        return

    with open(filename, 'w') as f:
        f.write("; G-Code — Combined: Drilling + Slot milling\n")
        if current_filename:
            f.write(f"; Holes source: {current_filename.split('/')[-1]}\n")
        if slot_filename:
            f.write(f"; Slots source: {slot_filename.split('/')[-1]}\n")
        f.write(f"; Milling feed: {mill_feed:.0f} mm/min (feed/2)\n")
        f.write("G21 ; Metric\n")
        f.write("G90 ; Absolute coordinates\n\n")

        # Сверление
        if current_tools:
            f.write("; ===== DRILLING SECTION =====\n\n")
            for tool, data in current_tools.items():
                if not data['visible'] or not data['holes']:
                    continue
                write_tool_start(f, tool, data['diameter'], len(data['holes']),
                                 "holes", safe_z, rapid_rate)
                for x_mm, y_mm in data['holes']:
                    f.write(f"G00 X{x_mm:.3f} Y{y_mm:.3f} F{rapid_rate:.0f}\n")
                    f.write(f"G01 Z{drill_z:.2f} F{feed_rate:.0f}\n")
                    f.write(f"G00 Z{safe_z:.2f} F{rapid_rate:.0f}\n")

                write_tool_parking(f, park_z, rapid_rate)

        # Фрезеровка слотов
        if slot_tools:
            f.write("\n; ===== SLOT MILLING SECTION =====\n\n")
            for tool, data in slot_tools.items():
                if not data['visible'] or not data['slots']:
                    continue
                write_tool_start(f, tool, data['diameter'], len(data['slots']),
                                 "slots", safe_z, rapid_rate)
                for slot_idx, (start, end) in enumerate(data['slots']):
                    sx, sy = start
                    ex, ey = end
                    f.write(f"; Slot {slot_idx + 1}\n")
                    f.write(f"G00 X{sx:.3f} Y{sy:.3f} F{rapid_rate:.0f}\n")
                    f.write(f"G01 Z{drill_z:.2f} F{feed_rate:.0f}\n")
                    f.write(f"G01 X{ex:.3f} Y{ey:.3f} F{mill_feed:.0f}\n")
                    f.write(f"G00 Z{safe_z:.2f} F{rapid_rate:.0f}\n")

                write_tool_parking(f, park_z, rapid_rate)

        f.write("M30\n")
        f.write("; End program\n")

    show_result_dialog(filename)


def on_show_paths_change():
    redraw_grid()


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
        "   горизонталь F=подача/2, подъём F=холостой\n\n"
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
root.title("Excellon To G-code: Сверление + Фрезеровка слотов")
root.geometry("1280x720")
root.minsize(1100, 650)

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

# Справка
tk.Button(right_frame, text="❓ Справка", command=open_help).pack(
    fill="x", padx=5, pady=2)

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

