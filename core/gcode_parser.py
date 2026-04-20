"""
Парсин G-code для визуализатора.
Разбирает текст G-code на сегменты движения для 2.5D визуализации.
"""
import re


def parse_gcode_for_viz(gcode_text):
    """
    Парсит текст G-code и возвращает список сегментов движения:
    {'type': 'rapid'|'feed'|'drill_down'|'drill_up'|'slot_h'|'outline',
     'x0','y0','z0','x1','y1','z1', 'tool', 'diameter'}
    """
    segments = []
    cx, cy, cz = 0.0, 0.0, 0.0
    cur_tool = '?'
    cur_diameter = 0.0
    tool_diameter_map = {}
    in_outline_section = False
    in_tab = False

    for raw in gcode_text.splitlines():
        line = raw.strip()
        if not line or line.startswith(';'):
            # Извлекаем диаметр из комментария: ; Tool T1 D=0.80mm
            m = re.match(r';\s*Tool\s+T(\d+)\s+D=([\d.]+)mm', line)
            if m:
                tool_diameter_map[m.group(1)] = float(m.group(2))
            # Определяем начало и конец секции outline milling
            if 'BOARD OUTLINE MILLING' in line:
                in_outline_section = True
            elif '=====' in line and in_outline_section and 'OUTLINE' not in line:
                in_outline_section = False
            # Маркеры tab-ов внутри outline-секции
            if 'TAB BEGIN' in line:
                in_tab = True
            elif 'TAB END' in line:
                in_tab = False
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
                # Для outline milling используем отдельный тип,
                # а участок над перемычкой отмечаем особым типом
                if in_outline_section:
                    seg_type = 'outline_tab' if in_tab else 'outline'
                else:
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
