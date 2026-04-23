"""
Вспомогательные диалоги: результат, статистика, помощь.
"""
import os
import math
import tkinter as tk
from tkinter import messagebox
import core.config as cfg


def show_result_dialog(filename):
    """Диалог подтверждения сохранения G-code."""
    dlg = tk.Toplevel(cfg.get_widget("root"))
    dlg.title("Готово")
    dlg.resizable(False, False)
    dlg.transient(cfg.get_widget("root"))
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
    root_x = cfg.get_widget("root").winfo_x()
    root_y = cfg.get_widget("root").winfo_y()
    root_w = cfg.get_widget("root").winfo_width()
    root_h = cfg.get_widget("root").winfo_height()
    x = root_x + (root_w - dlg_w) // 2
    y = root_y + (root_h - dlg_h) // 2
    dlg.geometry(f"+{x}+{y}")


def show_statistics():
    """Расчёт и показ статистики."""
    if not cfg.current_tools and not cfg.slot_tools:
        messagebox.showinfo("Статистика", "Нет загруженных данных.")
        return

    all_points = []
    total_holes = 0
    total_slots = 0
    drill_tools_count = 0
    mill_tools_count = 0
    tool_lines = []

    if cfg.current_tools:
        for tool, data in cfg.current_tools.items():
            count = len(data['holes'])
            total_holes += count
            drill_tools_count += 1
            tool_lines.append(f"  T{tool}  D={data['diameter']:.2f}мм  {count} отв.")
            all_points.extend(data['holes'])

    if cfg.slot_tools:
        for tool, data in cfg.slot_tools.items():
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
        rapid_rate = cfg.get_param("rapid_rate")
        feed_rate = cfg.get_param("feed_rate")
        mill_feed = cfg.get_param("mill_feed")
        safe_z = cfg.get_param("safe_z")
        drill_z = cfg.get_param("drill_z")
    except ValueError:
        rapid_rate = feed_rate = mill_feed = safe_z = drill_z = 0

    total_rapid = 0.0
    total_feed = 0.0
    z_travel_per_hole = abs(safe_z) + abs(drill_z)

    if cfg.current_tools:
        for tool, data in cfg.current_tools.items():
            holes = data['holes']
            if not holes:
                continue
            total_rapid += math.sqrt(holes[0][0]**2 + holes[0][1]**2)
            for i in range(1, len(holes)):
                dx = holes[i][0] - holes[i-1][0]
                dy = holes[i][1] - holes[i-1][1]
                total_rapid += math.sqrt(dx**2 + dy**2)
            total_feed += z_travel_per_hole * 2 * len(holes)

    slot_feed_dist = 0.0
    if cfg.slot_tools:
        for tool, data in cfg.slot_tools.items():
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
    """Справочное окно."""
    from ui.help_window import open_help_window
    open_help_window(cfg.get_widget("root"))
