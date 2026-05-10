"""
Обработчики событий для генерации G-code.
"""
import logging
from tkinter import filedialog
from ui import themed_messagebox as messagebox
from core.i18n import t, get_language
from core.path_validator import validate_save_path
import core.config as cfg

logger = logging.getLogger(__name__)


def get_app_context():
    """Получить контекст приложения."""
    from ui.app import get_app_context as _get_app_context
    return _get_app_context()


def check_missing_tools(tool_type: str, tools_dict: dict) -> list:
    """В pro-режиме проверить, какие инструменты отсутствуют в базе.
    Возвращает список строк вида 'T1 D=1.00мм'."""
    context = get_app_context()
    if context.mode_engine.is_simple:
        return []
    missing = []
    if not tools_dict:
        return missing
    for tool_num, data in tools_dict.items():
        if not data['visible'] or not (data.get('holes') or data.get('slots')):
            continue
        if tool_type == "drill":
            if context.tool_db.find_drill(data['diameter']) is None:
                missing.append(f"T{tool_num} D={data['diameter']:.2f}{t('unit.mm')}")
        elif tool_type == "endmill":
            db = context.tool_db
            if (db.find_endmill(data['diameter']) is None and
                    db.find_endmill_smaller_than(data['diameter']) is None):
                missing.append(f"T{tool_num} D={data['diameter']:.2f}{t('unit.mm')}")
    return missing


def show_missing_tools_warning(missing_tools: list) -> bool:
    """Показать предупреждение о недостающих инструментах.
    Возвращает True если пользователь согласился продолжить."""
    if not missing_tools:
        return True
    tool_list = "\n".join(f"  • {tool}" for tool in missing_tools)
    msg = t("app.dlg.missing_tools.msg", tool_list=tool_list)
    return messagebox.askyesno(t("app.dlg.missing_tools.title"), msg)


def check_endmill_multipass(tools_dict) -> list:
    """В pro-режиме найти слоты, которые будут обработаны меньшей фрезой.
    Возвращает список строк для отображения пользователю."""
    context = get_app_context()
    if context.mode_engine.is_simple or not tools_dict:
        return []
    from core.gcode_generator import _calc_multipass_offsets
    result = []
    for tool_num, data in tools_dict.items():
        if not data['visible'] or not data['slots']:
            continue
        slot_d = data['diameter']
        db = context.tool_db
        if db.find_endmill(slot_d) is not None:
            continue  # точное совпадение — не multi-pass
        smaller = db.find_endmill_smaller_than(slot_d)
        if smaller is None:
            continue  # нет ничего — попадёт в missing
        tool_d = float(smaller["diameter"])
        stepover = smaller.get("stepover", 0)
        offsets = _calc_multipass_offsets(slot_d, tool_d, stepover)
        n = len(offsets)
        
        # Локализация: единицы измерения, тип инструмента и количество проходов
        unit_mm = t('unit.mm')
        tool_type = t('stats.tool.endmill')  # "Фреза" / "Mill"
        
        # Локализация множественного числа для "проход"
        if get_language() == 'ru':
            passes_word = 'проход' if n == 1 else ('прохода' if 2 <= n <= 4 else 'проходов')
        else:
            passes_word = 'pass' if n == 1 else 'passes'
        
        result.append(
            f"T{tool_num} ⌀{slot_d:.2f}{unit_mm} → {tool_type} ⌀{tool_d:.2f}{unit_mm}, {n} {passes_word}"
        )
    return result


def show_multipass_warning(multipass_list: list) -> bool:
    """Предупредить пользователя о генерации multi-pass кода и спросить подтверждение."""
    if not multipass_list:
        return True
    tool_list = "\n".join(f"  • {tool}" for tool in multipass_list)
    msg = t("app.dlg.multipass.msg", tool_list=tool_list)
    return messagebox.askyesno(t("app.dlg.multipass.title"), msg)


def build_drill_tool_params_dict():
    """В pro-режиме собрать {tool_number: params} из базы.
    Если инструмент не найден — параметры не добавляются (будет M03 без S)."""
    context = get_app_context()
    if context.mode_engine.is_simple:
        return None
    global_params = {
        'safe_z': cfg.get_param("safe_z"), 'drill_z': cfg.get_param("drill_z"),
        'feed_rate': cfg.get_param("feed_rate"), 'rapid_rate': cfg.get_param("rapid_rate"),
        'park_z': cfg.get_param("park_z"),
    }
    result = {}
    if not cfg.current_tools:
        return None
    for tool_num, data in cfg.current_tools.items():
        if not data['visible'] or not data['holes']:
            continue
        tp = context.mode_engine.get_drill_params(data['diameter'], global_params)
        if tp is not None:
            result[tool_num] = tp
        # Если None — инструмент не найден, генерируем без параметров
    return result


def build_endmill_tool_params_dict():
    """В pro-режиме собрать {tool_number: params} из базы для фрез."""
    context = get_app_context()
    if context.mode_engine.is_simple:
        return None
    global_params = {
        'safe_z': cfg.get_param("safe_z"), 'drill_z': cfg.get_param("drill_z"),
        'feed_rate': cfg.get_param("feed_rate"), 'mill_feed': cfg.get_param("mill_feed"),
        'rapid_rate': cfg.get_param("rapid_rate"), 'park_z': cfg.get_param("park_z"),
    }
    result = {}
    if not cfg.slot_tools:
        return None
    for tool_num, data in cfg.slot_tools.items():
        if not data['visible'] or not data['slots']:
            continue
        tp = context.mode_engine.get_endmill_params_for_slot(data['diameter'], global_params)
        if tp is not None:
            result[tool_num] = tp
    return result


def save_gcode_params_from_ui():
    """Сохранить текущие параметры G-code из Entry-виджетов."""
    context = get_app_context()
    context.gcode_params.read_from_ui(cfg.widgets)
    context.gcode_params.save()


def on_param_change(event=None):
    """Автосохранение параметров при потере фокуса / нажатии Enter / выборе в Combobox."""
    try:
        save_gcode_params_from_ui()
    except Exception as e:
        # Не ломаем UI из-за ошибки сохранения (например, временно невалидное значение)
        logger.warning("Failed to save G-code parameters: %s", e)


def enrich_outline_params_with_tool(outline_params: dict, global_params: dict) -> None:
    """Добавить в outline_params рабочую подачу и обороты шпинделя.

    Simple mode → подача берётся из "Подача фрезы" (mill_feed) глобальных параметров.
    Pro mode   → ищем фрезу по диаметру в базе и берём "cutting_feed" и "spindle_speed".
                 Если точной фрезы нет — пробуем меньшую.
                 Если не найдено ничего — откат на глобальные параметры.

    Изменяет outline_params in-place, добавляя ключи: mill_feed, plunge_feed, spindle_speed.
    """
    # Погружение по Z всегда от глобальной "Подача" (feed_rate)
    outline_params['plunge_feed'] = global_params.get('feed_rate', 100)

    diameter = outline_params.get('tool_diameter', 2.0)

    context = get_app_context()
    if context.mode_engine.is_simple:
        # Simple — единая «Подача фрезы»
        outline_params['mill_feed'] = global_params.get('mill_feed', 50)
        outline_params['spindle_speed'] = None
        return

    # Pro — ищем фрезу в базе
    db = context.tool_db
    tool = db.find_endmill(diameter)
    if tool is None:
        tool = db.find_endmill_smaller_than(diameter)

    if tool is not None:
        outline_params['mill_feed'] = float(tool.get('cutting_feed',
                                                     global_params.get('mill_feed', 50)))
        ss = tool.get('spindle_speed')
        outline_params['spindle_speed'] = int(ss) if ss else None
    else:
        # В базе нет — падаем на глобальные
        outline_params['mill_feed'] = global_params.get('mill_feed', 50)
        outline_params['spindle_speed'] = None


def generate_drilling_gcode():
    """Генерация G-code для сверления отверстий."""
    from core.gcode_generator import _build_drilling_gcode
    from ui.gcode_viz import _store_gcode_for_viz
    from ui.dialogs import show_result_dialog

    # Блокировка кнопок генерации для предотвращения race conditions
    gcode_frame_buttons = [
        cfg.widgets.get("btn_gen_drill"),
        cfg.widgets.get("btn_gen_mill"),
        cfg.widgets.get("btn_gen_outline"),
        cfg.widgets.get("btn_gen_combined")
    ]
    for btn in gcode_frame_buttons:
        if btn:
            btn.config(state="disabled")
    
    try:
        save_gcode_params_from_ui()

        # Проверка недостающих инструментов в pro-режиме
        missing = check_missing_tools("drill", cfg.current_tools)
        if not show_missing_tools_warning(missing):
            return

        params = {
            'safe_z': cfg.get_param("safe_z"),
            'drill_z': cfg.get_param("drill_z"),
            'feed_rate': cfg.get_param("feed_rate"),
            'rapid_rate': cfg.get_param("rapid_rate"),
            'park_z': cfg.get_param("park_z"),
        }
        tool_params = build_drill_tool_params_dict()
        gcode_text, errors = _build_drilling_gcode(cfg.current_tools, cfg.current_filename, params, tool_params)
        if errors:
            messagebox.showwarning(t("app.dlg.warning"), "\n".join(errors))
            return
        filename = filedialog.asksaveasfilename(
            defaultextension=".tap",
            filetypes=[(t("app.filetype.tap"), "*.tap"), (t("app.filetype.gcode"), ("*.gcode", "*.nc", "*.ngc")),
                       (t("app.filetype.all"), "*.*")],
            title=t("app.dlg.save_drilling.title")
        )
        if not filename:
            return
        # Проверка безопасности пути
        is_valid, error_msg = validate_save_path(filename)
        if not is_valid:
            messagebox.showerror(t("app.err.write.title"), 
                               t("app.err.invalid_path", error=error_msg))
            return
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(gcode_text)
        except IOError as e:
            messagebox.showerror(t("app.err.write.title"), t("app.err.write.msg", error=str(e)))
            return
        _store_gcode_for_viz(gcode_text)
        show_result_dialog(filename)
    except Exception as e:
        # Перехват непредвиденных ошибок генератора G-code, чтобы они не
        # пробивались в Tkinter event loop сырым traceback'ом. Полный stack
        # уходит в лог через logger.exception, пользователю — локализованное
        # сообщение с str(e).
        logger.exception("G-code generation failed")
        messagebox.showerror(
            t("app.dlg.error"),
            t("app.err.gen_failed", error=str(e))
        )
    finally:
        # Разблокировка кнопок после завершения операции
        for btn in gcode_frame_buttons:
            if btn:
                btn.config(state="normal")


def generate_milling_gcode():
    """Генерация G-code для фрезерования слотов."""
    from core.gcode_generator import _build_milling_gcode
    from ui.gcode_viz import _store_gcode_for_viz
    from ui.dialogs import show_result_dialog

    # Блокировка кнопок генерации для предотвращения race conditions
    gcode_frame_buttons = [
        cfg.widgets.get("btn_gen_drill"),
        cfg.widgets.get("btn_gen_mill"),
        cfg.widgets.get("btn_gen_outline"),
        cfg.widgets.get("btn_gen_combined")
    ]
    for btn in gcode_frame_buttons:
        if btn:
            btn.config(state="disabled")
    
    try:
        save_gcode_params_from_ui()

        # Проверка недостающих инструментов и multi-pass в pro-режиме
        missing = check_missing_tools("endmill", cfg.slot_tools)
        if missing and not show_missing_tools_warning(missing):
            return
        multipass = check_endmill_multipass(cfg.slot_tools)
        if multipass and not show_multipass_warning(multipass):
            return

        params = {
            'safe_z': cfg.get_param("safe_z"),
            'drill_z': cfg.get_param("drill_z"),
            'feed_rate': cfg.get_param("feed_rate"),
            'mill_feed': cfg.get_param("mill_feed"),
            'rapid_rate': cfg.get_param("rapid_rate"),
            'park_z': cfg.get_param("park_z"),
        }
        tool_params = build_endmill_tool_params_dict()
        gcode_text, errors = _build_milling_gcode(cfg.slot_tools, cfg.slot_filename, params, tool_params)
        if errors:
            messagebox.showwarning(t("app.dlg.warning"), "\n".join(errors))
            return
        filename = filedialog.asksaveasfilename(
            defaultextension=".tap",
            filetypes=[(t("app.filetype.tap"), "*.tap"), (t("app.filetype.gcode"), ("*.gcode", "*.nc", "*.ngc")),
                       (t("app.filetype.all"), "*.*")],
            title=t("app.dlg.save_milling.title")
        )
        if not filename:
            return
        # Проверка безопасности пути
        is_valid, error_msg = validate_save_path(filename)
        if not is_valid:
            messagebox.showerror(t("app.err.write.title"), 
                               t("app.err.invalid_path", error=error_msg))
            return
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(gcode_text)
        except IOError as e:
            messagebox.showerror(t("app.err.write.title"), t("app.err.write.msg", error=str(e)))
            return
        _store_gcode_for_viz(gcode_text)
        show_result_dialog(filename)
    except Exception as e:
        # Перехват непредвиденных ошибок генератора G-code, чтобы они не
        # пробивались в Tkinter event loop сырым traceback'ом. Полный stack
        # уходит в лог через logger.exception, пользователю — локализованное
        # сообщение с str(e).
        logger.exception("G-code generation failed")
        messagebox.showerror(
            t("app.dlg.error"),
            t("app.err.gen_failed", error=str(e))
        )
    finally:
        # Разблокировка кнопок после завершения операции
        for btn in gcode_frame_buttons:
            if btn:
                btn.config(state="normal")


def generate_combined_gcode():
    """Генерация комбинированного G-code (сверление + фрезерование + контур)."""
    from core.gcode_generator import _build_combined_gcode
    from ui.gcode_viz import _store_gcode_for_viz
    from ui.dialogs import show_result_dialog
    from core.validators import validate_holes_within_outline, validate_outline_params
    from core.polygon_ops import flatten
    from ui.renderer import redraw_grid

    # Блокировка кнопок генерации для предотвращения race conditions
    gcode_frame_buttons = [
        cfg.widgets.get("btn_gen_drill"),
        cfg.widgets.get("btn_gen_mill"),
        cfg.widgets.get("btn_gen_outline"),
        cfg.widgets.get("btn_gen_combined")
    ]
    for btn in gcode_frame_buttons:
        if btn:
            btn.config(state="disabled")
    
    try:
        save_gcode_params_from_ui()

        # Проверка недостающих инструментов и multi-pass в pro-режиме
        missing_drills = check_missing_tools("drill", cfg.current_tools)
        missing_endmills = check_missing_tools("endmill", cfg.slot_tools)
        all_missing = missing_drills + missing_endmills
        if all_missing and not show_missing_tools_warning(all_missing):
            return
        multipass = check_endmill_multipass(cfg.slot_tools)
        if multipass and not show_multipass_warning(multipass):
            return

        params = {
            'safe_z': cfg.get_param("safe_z"),
            'drill_z': cfg.get_param("drill_z"),
            'feed_rate': cfg.get_param("feed_rate"),
            'mill_feed': cfg.get_param("mill_feed"),
            'rapid_rate': cfg.get_param("rapid_rate"),
            'park_z': cfg.get_param("park_z"),
        }
        drill_tp = build_drill_tool_params_dict()
        endmill_tp = build_endmill_tool_params_dict()
        tool_params_dict = {}
        if drill_tp:
            tool_params_dict["drills"] = drill_tp
        if endmill_tp:
            tool_params_dict["endmills"] = endmill_tp

        # Параметры обрезки по контуру
        outline_params = None
        if cfg.board_outline:
            outline_params = {
                'tool_diameter': cfg.get_param("outline_tool_diameter"),
                'depth_per_pass': cfg.get_param("outline_depth_per_pass"),
                'n_tabs': int(cfg.get_param("outline_n_tabs")),
                'tab_width': cfg.get_param("outline_tab_width"),
                'tab_height': cfg.get_param("outline_tab_height"),
                'direction': cfg.get_widget("outline_direction_var").get(),
            }
            # Подача / шпиндель: из global mill_feed (simple) или базы (pro)
            enrich_outline_params_with_tool(outline_params, params)
            # Валидация параметров
            outline_errors = validate_outline_params(outline_params, params['drill_z'])
            if outline_errors:
                messagebox.showwarning(t("app.dlg.outline_params.title"), "\n".join(outline_errors))
                return

        # Валидация отверстий внутри контура
        if cfg.board_outline:
            outline_polygon = flatten(cfg.board_outline, tol_mm=0.5)
            violations = validate_holes_within_outline(
                cfg.current_tools, cfg.slot_tools, outline_polygon
            )
            cfg.outline_violations = [(desc, (x, y)) for desc, (x, y) in violations]
            redraw_grid()
            if violations:
                violation_list = "\n".join(f"  • {desc}" for desc, _ in violations[:10])
                if len(violations) > 10:
                    violation_list += "\n" + t("app.dlg.violations.more", count=len(violations) - 10)
                msg = t("app.dlg.violations.msg", violation_list=violation_list)
                if not messagebox.askyesno(t("app.dlg.violations.title"), msg):
                    return

        gcode_text, errors = _build_combined_gcode(
            cfg.current_tools, cfg.current_filename,
            cfg.slot_tools, cfg.slot_filename,
            params, tool_params_dict if tool_params_dict else None,
            board_outline=cfg.board_outline,
            board_outline_filename=cfg.board_outline_filename,
            outline_params=outline_params
        )
        if errors:
            messagebox.showwarning(t("app.dlg.warning"), "\n".join(errors))
            return
        filename = filedialog.asksaveasfilename(
            defaultextension=".tap",
            filetypes=[(t("app.filetype.tap"), "*.tap"), (t("app.filetype.gcode"), ("*.gcode", "*.nc", "*.ngc")),
                       (t("app.filetype.all"), "*.*")],
            title=t("app.dlg.save_combined.title")
        )
        if not filename:
            return
        # Проверка безопасности пути
        is_valid, error_msg = validate_save_path(filename)
        if not is_valid:
            messagebox.showerror(t("app.err.write.title"), 
                               t("app.err.invalid_path", error=error_msg))
            return
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(gcode_text)
        except IOError as e:
            messagebox.showerror(t("app.err.write.title"), t("app.err.write.msg", error=str(e)))
            return
        _store_gcode_for_viz(gcode_text)
        show_result_dialog(filename)
    except Exception as e:
        # Перехват непредвиденных ошибок генератора G-code, чтобы они не
        # пробивались в Tkinter event loop сырым traceback'ом. Полный stack
        # уходит в лог через logger.exception, пользователю — локализованное
        # сообщение с str(e).
        logger.exception("G-code generation failed")
        messagebox.showerror(
            t("app.dlg.error"),
            t("app.err.gen_failed", error=str(e))
        )
    finally:
        # Разблокировка кнопок после завершения операции
        for btn in gcode_frame_buttons:
            if btn:
                btn.config(state="normal")


def generate_outline_gcode():
    """Генерация G-code только для обрезки по контуру платы."""
    from core.gcode_generator import _build_outline_only_gcode
    from ui.gcode_viz import _store_gcode_for_viz
    from ui.dialogs import show_result_dialog
    from core.validators import validate_holes_within_outline, validate_outline_params
    from core.polygon_ops import flatten
    from ui.renderer import redraw_grid

    # Блокировка кнопок генерации для предотвращения race conditions
    gcode_frame_buttons = [
        cfg.widgets.get("btn_gen_drill"),
        cfg.widgets.get("btn_gen_mill"),
        cfg.widgets.get("btn_gen_outline"),
        cfg.widgets.get("btn_gen_combined")
    ]
    for btn in gcode_frame_buttons:
        if btn:
            btn.config(state="disabled")
    
    try:
        save_gcode_params_from_ui()

        if not cfg.board_outline:
            messagebox.showwarning(t("app.dlg.warning"), t("app.err.no_outline"))
            return

        params = {
            'safe_z': cfg.get_param("safe_z"),
            'drill_z': cfg.get_param("drill_z"),
            'feed_rate': cfg.get_param("feed_rate"),
            'mill_feed': cfg.get_param("mill_feed"),
            'rapid_rate': cfg.get_param("rapid_rate"),
            'park_z': cfg.get_param("park_z"),
        }
        outline_params = {
            'tool_diameter': cfg.get_param("outline_tool_diameter"),
            'depth_per_pass': cfg.get_param("outline_depth_per_pass"),
            'n_tabs': int(cfg.get_param("outline_n_tabs")),
            'tab_width': cfg.get_param("outline_tab_width"),
            'tab_height': cfg.get_param("outline_tab_height"),
            'direction': cfg.get_widget("outline_direction_var").get(),
        }
        # Подача / шпиндель: из global mill_feed (simple) или базы (pro)
        enrich_outline_params_with_tool(outline_params, params)

        # Валидация параметров обрезки
        outline_errors = validate_outline_params(outline_params, params['drill_z'])
        if outline_errors:
            messagebox.showwarning(t("app.dlg.outline_params.title"), "\n".join(outline_errors))
            return

        # Если есть отверстия/слоты — проверим, что они внутри контура
        if cfg.current_tools or cfg.slot_tools:
            outline_polygon = flatten(cfg.board_outline, tol_mm=0.5)
            violations = validate_holes_within_outline(
                cfg.current_tools, cfg.slot_tools, outline_polygon
            )
            cfg.outline_violations = [(desc, (x, y)) for desc, (x, y) in violations]
            redraw_grid()
            if violations:
                violation_list = "\n".join(f"  • {desc}" for desc, _ in violations[:10])
                if len(violations) > 10:
                    violation_list += "\n" + t("app.dlg.violations.more", count=len(violations) - 10)
                msg = t("app.dlg.violations.msg_outline", violation_list=violation_list)
                if not messagebox.askyesno(t("app.dlg.violations.title"), msg):
                    return

        gcode_text, errors = _build_outline_only_gcode(
            cfg.board_outline, cfg.board_outline_filename, params, outline_params
        )
        if errors:
            messagebox.showwarning(t("app.dlg.warning"), "\n".join(errors))
            return
        filename = filedialog.asksaveasfilename(
            defaultextension=".tap",
            filetypes=[(t("app.filetype.tap"), "*.tap"), (t("app.filetype.gcode"), ("*.gcode", "*.nc", "*.ngc")),
                       (t("app.filetype.all"), "*.*")],
            title=t("app.dlg.save_outline.title")
        )
        if not filename:
            return
        # Проверка безопасности пути
        is_valid, error_msg = validate_save_path(filename)
        if not is_valid:
            messagebox.showerror(t("app.err.write.title"), 
                               t("app.err.invalid_path", error=error_msg))
            return
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(gcode_text)
        except IOError as e:
            messagebox.showerror(t("app.err.write.title"), t("app.err.write.msg", error=str(e)))
            return
        _store_gcode_for_viz(gcode_text)
        show_result_dialog(filename)
    except Exception as e:
        # Перехват непредвиденных ошибок генератора G-code, чтобы они не
        # пробивались в Tkinter event loop сырым traceback'ом. Полный stack
        # уходит в лог через logger.exception, пользователю — локализованное
        # сообщение с str(e).
        logger.exception("G-code generation failed")
        messagebox.showerror(
            t("app.dlg.error"),
            t("app.err.gen_failed", error=str(e))
        )
    finally:
        # Разблокировка кнопок после завершения операции
        for btn in gcode_frame_buttons:
            if btn:
                btn.config(state="normal")
