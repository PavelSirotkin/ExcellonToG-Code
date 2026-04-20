"""
База данных инструментов для режима "Про".
Хранит параметры сверл и фрез в JSON-файле.
Ключ инструмента — диаметр (строка формата "X.XX").
Автосохранение при каждом изменении.
"""
import json
import os
from typing import Dict, Any, Optional, List


# ==========================================================
# Поля записей (без material)
# ==========================================================

DRILL_FIELDS = [
    "diameter",        # float — диаметр инструмента
    "spindle_speed",   # int — обороты шпинделя (RPM)
    "plunge_feed",     # float — скорость погружения Z (мм/мин)
    "retract_feed",    # float — скорость подъёма Z (мм/мин)
]

ENDMILL_FIELDS = [
    "diameter",        # float — диаметр инструмента
    "spindle_speed",   # int — обороты шпинделя (RPM)
    "cutting_feed",    # float — скорость реза XY (мм/мин)
    "stepover",        # float — ширина перекрытия (%)
]


def _make_drill(diameter: float, spindle_speed: int = 0, plunge_feed: float = 0,
                 retract_feed: float = 0) -> Dict[str, Any]:
    """Создать запись сверла с полями по умолчанию."""
    return {
        "diameter": diameter, "spindle_speed": spindle_speed,
        "plunge_feed": plunge_feed, "retract_feed": retract_feed,
    }


def _make_endmill(diameter: float, spindle_speed: int = 0, cutting_feed: float = 0,
                   stepover: float = 0) -> Dict[str, Any]:
    """Создать запись фрезы с полями по умолчанию."""
    return {
        "diameter": diameter, "spindle_speed": spindle_speed,
        "cutting_feed": cutting_feed, "stepover": stepover,
    }


def _fmt_key(diameter: float) -> str:
    """Форматировать диаметр как ключ словаря."""
    formatted = f"{diameter:.2f}".rstrip('0').rstrip('.')
    if '.' not in formatted:
        formatted += '.0'
    return formatted


# ==========================================================
# Класс базы инструментов с автосохранением
# ==========================================================

class ToolDatabase:
    """База данных инструментов. Автосохранение при каждом изменении."""

    def __init__(self, db_path: str = None):
        self._path = db_path
        self.drills: Dict[str, Dict[str, Any]] = {}
        self.endmills: Dict[str, Dict[str, Any]] = {}

    @property
    def path(self) -> Optional[str]:
        return self._path

    @path.setter
    def path(self, value: str):
        self._path = value

    # ---- Загрузка / Сохранение ----

    def load(self, path: str = None) -> bool:
        """Загрузить базу из JSON-файла. Создаёт пустую если нет."""
        p = path or self._path
        if not p:
            return False
        self._path = p
        if not os.path.isfile(p):
            # Создать пустую базу
            self.drills = {}
            self.endmills = {}
            self.save()
            return True
        try:
            with open(p, 'r', encoding='utf-8') as f:
                data = json.load(f)
            self.drills = data.get("drills", data.get("drill", {}))
            self.endmills = data.get("endmills", data.get("endmill", {}))
            return True
        except (json.JSONDecodeError, IOError, KeyError):
            self.drills = {}
            self.endmills = {}
            return False

    def save(self, path: str = None) -> bool:
        """Сохранить базу в JSON-файл."""
        p = path or self._path
        if not p:
            return False
        self._path = p
        try:
            data = {"drills": self.drills, "endmills": self.endmills}
            os.makedirs(os.path.dirname(os.path.abspath(p)), exist_ok=True)
            with open(p, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            return True
        except IOError:
            return False

    def _auto_save(self):
        """Автосохранение после изменений."""
        if self._path:
            self.save()

    # ---- Сверла ----

    def add_drill(self, diameter: float, **kwargs) -> Optional[Dict[str, Any]]:
        if diameter <= 0:
            return None
        key = _fmt_key(diameter)
        record = _make_drill(diameter, **kwargs)
        for field in DRILL_FIELDS:
            if field not in record:
                record[field] = 0
        record["diameter"] = diameter
        self.drills[key] = record
        self._auto_save()
        return record

    def update_drill(self, diameter: float, **kwargs) -> Optional[Dict[str, Any]]:
        key = _fmt_key(diameter)
        if key not in self.drills:
            return None
        self.drills[key].update(kwargs)
        self.drills[key]["diameter"] = diameter
        self._auto_save()
        return self.drills[key]

    def delete_drill(self, diameter: float) -> bool:
        key = _fmt_key(diameter)
        if key in self.drills:
            del self.drills[key]
            self._auto_save()
            return True
        return False

    def find_drill(self, diameter: float, tolerance: float = 0.001) -> Optional[Dict[str, Any]]:
        key = _fmt_key(diameter)
        if key in self.drills:
            return self.drills[key]
        # Поиск с допуском по диаметру
        for k, v in self.drills.items():
            try:
                if abs(float(v.get("diameter", 0)) - float(diameter)) <= tolerance:
                    return v
            except (ValueError, TypeError):
                pass
        return None

    # ---- Фрезы ----

    def add_endmill(self, diameter: float, **kwargs) -> Optional[Dict[str, Any]]:
        if diameter <= 0:
            return None
        key = _fmt_key(diameter)
        record = _make_endmill(diameter, **kwargs)
        for field in ENDMILL_FIELDS:
            if field not in record:
                record[field] = 0
        record["diameter"] = diameter
        self.endmills[key] = record
        self._auto_save()
        return record

    def update_endmill(self, diameter: float, **kwargs) -> Optional[Dict[str, Any]]:
        key = _fmt_key(diameter)
        if key not in self.endmills:
            return None
        self.endmills[key].update(kwargs)
        self.endmills[key]["diameter"] = diameter
        self._auto_save()
        return self.endmills[key]

    def delete_endmill(self, diameter: float) -> bool:
        key = _fmt_key(diameter)
        if key in self.endmills:
            del self.endmills[key]
            self._auto_save()
            return True
        return False

    def find_endmill_smaller_than(self, diameter: float) -> Optional[Dict[str, Any]]:
        """Найти наибольший инструмент с d < diameter (с зазором 0.001)."""
        candidates = [
            v for v in self.endmills.values()
            if float(v.get("diameter", 0)) < diameter - 0.001
        ]
        if not candidates:
            return None
        return max(candidates, key=lambda v: float(v["diameter"]))

    def find_endmill(self, diameter: float, tolerance: float = 0.001) -> Optional[Dict[str, Any]]:
        key = _fmt_key(diameter)
        if key in self.endmills:
            return self.endmills[key]
        # Поиск с допуском по диаметру
        for k, v in self.endmills.items():
            try:
                if abs(float(v.get("diameter", 0)) - float(diameter)) <= tolerance:
                    return v
            except (ValueError, TypeError):
                pass
        return None

    # ---- Общее ----

    def get_all_drills(self) -> List[Dict[str, Any]]:
        return sorted(self.drills.values(), key=lambda d: d["diameter"])

    def get_all_endmills(self) -> List[Dict[str, Any]]:
        return sorted(self.endmills.values(), key=lambda d: d["diameter"])

    def clear(self):
        self.drills.clear()
        self.endmills.clear()
        self._auto_save()

    def count(self) -> tuple:
        return len(self.drills), len(self.endmills)

    def export_json(self) -> str:
        return json.dumps({"drills": self.drills, "endmills": self.endmills},
                          indent=2, ensure_ascii=False)

    def import_json(self, json_str: str) -> bool:
        try:
            data = json.loads(json_str)
            self.drills = data.get("drills", {})
            self.endmills = data.get("endmills", {})
            self._auto_save()
            return True
        except (json.JSONDecodeError, KeyError):
            return False
