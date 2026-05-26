"""
Объединение drill-инструментов из Excellon-файла по округлению к ближайшим
диаметрам из базы инструментов.

Сценарий: после конвертации из дюймов Excellon содержит инструменты с
нестандартными диаметрами (0.711, 0.728, …), которыми никто не сверлит.
Пользователь выбирает несколько таких инструментов в легенде, нажимает
«Объединить» — их диаметры округляются к ближайшим из tool_db, и все
отверстия мигрируют на округлённые инструменты.

Чистая функция без побочных эффектов: на вход — словари, на выход — новый
словарь tools. Не читает и не пишет cfg, не вызывает UI.
"""
from typing import Dict, Iterable, List, Optional, Tuple

from core.tsp_optimizer import nearest_neighbor_tsp


def _round_to_db(diameter: float, db_diameters: List[float]) -> float:
    """Ближайший диаметр в db по математическому округлению (min |Δ|).
    При равных расстояниях возвращает меньший — это совпадает с поведением
    sorted+min, стабильно и предсказуемо."""
    return min(db_diameters, key=lambda d: (abs(d - diameter), d))


def merge_drill_tools(
    current_tools: Dict[str, dict],
    selected_keys: Iterable[str],
    db_diameters: List[float],
) -> Tuple[Optional[Dict[str, dict]], Dict[str, float]]:
    """Округлить выбранные инструменты к ближайшим из db и объединить
    инструменты с одинаковым новым диаметром.

    Args:
        current_tools: текущий словарь инструментов из парсера Excellon —
            {tool_key: {"diameter": float, "holes": [...], ...}}.
        selected_keys: ключи инструментов, выбранных для объединения.
        db_diameters: диаметры из базы инструментов (drills).

    Returns:
        (new_tools, mapping_to_key):
          - new_tools: новый словарь инструментов или None, если db_diameters пуст;
          - mapping_to_key: {old_key: target_current_key} для каждого выбранного.
            Используется в ui.legend для обновления cfg.merge_groups
            (cur_key → set(original_keys)) — без этого «Разъединить выделенные»
            не смог бы понять, какие исходные инструменты слились в данный.
    """
    if not db_diameters:
        return None, {}

    selected = [k for k in selected_keys if k in current_tools]
    if not selected:
        # Нечего объединять — возвращаем копию current_tools без изменений.
        return _copy_tools(current_tools), {}

    db_sorted = sorted(db_diameters)

    # 1. Для каждого выбранного — вычисляем новый диаметр.
    new_diameter: Dict[str, float] = {}
    for key in selected:
        old_d = float(current_tools[key].get("diameter", 0.0))
        new_diameter[key] = _round_to_db(old_d, db_sorted)

    # 2. Невыделенные инструменты переходят как есть (с копией holes).
    new_tools: Dict[str, dict] = {}
    for key, data in current_tools.items():
        if key not in new_diameter:
            new_tools[key] = _copy_tool_record(data)

    # 3. Выделенные группируем по новому диаметру и сливаем.
    grouped: Dict[float, List[str]] = {}
    for old_key, new_d in new_diameter.items():
        grouped.setdefault(new_d, []).append(old_key)

    mapping_to_key: Dict[str, str] = {}
    for new_d, old_keys in grouped.items():
        # Собираем отверстия со всех выделенных, у которых одно и то же new_d.
        merged_holes = []
        for ok in old_keys:
            merged_holes.extend(current_tools[ok].get("holes", []))

        # Если в new_tools уже есть инструмент с этим диаметром
        # (не выделенный — например, T03=0.7 был в файле изначально),
        # дописываем отверстия к нему.
        existing_key = _find_key_by_diameter(new_tools, new_d)
        if existing_key is not None:
            # Парсер изначально оптимизировал порядок отверстий для каждого
            # инструмента отдельно (TSP nearest-neighbor + 2-opt). При простом
            # extend()/конкатенации швы между бывшими группами дают лишний
            # пробег инструмента. Реоптимизируем объединённый список целиком,
            # чтобы G-code остался эффективным.
            combined = new_tools[existing_key]["holes"] + merged_holes
            new_tools[existing_key]["holes"] = nearest_neighbor_tsp(combined)
            target = existing_key
        else:
            # Создаём новую запись. Ключ — первый из старых, чтобы при
            # отрисовке легенды было читаемо (T01, T02, ...).
            primary = old_keys[0]
            base = _copy_tool_record(current_tools[primary])
            base["diameter"] = new_d
            if len(old_keys) == 1:
                # Чистое переименование одиночного инструмента (например,
                # T03(0.711)→0.7 при отсутствии других слияющихся): порядок
                # отверстий уже оптимален, повторный прогон не нужен.
                base["holes"] = merged_holes
            else:
                # Несколько инструментов слились в новый: применяем TSP
                # к объединённому списку — см. комментарий выше.
                base["holes"] = nearest_neighbor_tsp(merged_holes)
            new_tools[primary] = base
            target = primary

        for ok in old_keys:
            mapping_to_key[ok] = target

    # Сортируем результирующий словарь по (diameter, int(tool_key)) —
    # тот же критерий, что использует core.parser.parse_excellon_file,
    # чтобы и легенда, и G-code шли от меньшего диаметра к большему.
    # int() с защитой от нечисловых ключей: для них tie-breaker = бесконечность,
    # они уйдут в конец своей группы, но не сломают сортировку.
    def _sort_key(item):
        k, v = item
        try:
            tie = int(k)
        except (TypeError, ValueError):
            tie = float("inf")
        return (v.get("diameter", 0.0), tie)

    sorted_tools = dict(sorted(new_tools.items(), key=_sort_key))
    return sorted_tools, mapping_to_key


def _copy_tool_record(data: dict) -> dict:
    """Скопировать запись инструмента так, чтобы holes стал независимым list."""
    out = dict(data)
    out["holes"] = list(data.get("holes", []))
    return out


def _copy_tools(current_tools: Dict[str, dict]) -> Dict[str, dict]:
    """Поверхностная копия словаря инструментов с глубокой копией holes."""
    return {k: _copy_tool_record(v) for k, v in current_tools.items()}


def _find_key_by_diameter(tools: Dict[str, dict], diameter: float,
                          tol: float = 1e-9) -> Optional[str]:
    """Вернуть ключ инструмента с заданным diameter (с допуском), либо None."""
    for k, v in tools.items():
        if abs(float(v.get("diameter", 0.0)) - diameter) < tol:
            return k
    return None
