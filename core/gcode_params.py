"""
Менеджер параметров G-code.
Загружает/сохраняет параметры в JSON-файл.
При отсутствии создаёт файл со значениями по умолчанию.
"""
import json
import os
from typing import Dict, Any


DEFAULT_PARAMS = {
    "safe_z": 5.0,
    "drill_z": -2.5,
    "feed_rate": 100,
    "mill_feed": 50,
    "rapid_rate": 500,
    "park_z": 30,
}


class GCodeParams:
    """Параметры G-code с автосохранением."""

    def __init__(self):
        self._path: str = None
        self._data: Dict[str, Any] = dict(DEFAULT_PARAMS)

    @property
    def path(self) -> str:
        return self._path

    @path.setter
    def path(self, value: str):
        self._path = value

    def get(self, key: str, default=None):
        return self._data.get(key, default)

    def set(self, key: str, value):
        self._data[key] = value

    def get_all(self) -> Dict[str, Any]:
        return dict(self._data)

    def load(self, path: str = None) -> bool:
        """Загрузить параметры. Если файла нет — создать с default."""
        p = path or self._path
        if not p:
            return False
        self._path = p
        if not os.path.isfile(p):
            self._data = dict(DEFAULT_PARAMS)
            self.save()
            return True
        try:
            with open(p, 'r', encoding='utf-8') as f:
                data = json.load(f)
            # Merge с default на случай новых полей
            merged = dict(DEFAULT_PARAMS)
            merged.update(data)
            self._data = merged
            return True
        except (json.JSONDecodeError, IOError, KeyError):
            self._data = dict(DEFAULT_PARAMS)
            return False

    def save(self, path: str = None) -> bool:
        """Сохранить параметры."""
        p = path or self._path
        if not p:
            return False
        self._path = p
        try:
            os.makedirs(os.path.dirname(os.path.abspath(p)), exist_ok=True)
            with open(p, 'w', encoding='utf-8') as f:
                json.dump(self._data, f, indent=2, ensure_ascii=False)
            return True
        except IOError:
            return False

    def apply_to_ui(self, widgets: Dict[str, Any]):
        """Применить параметры к Entry-виджетам."""
        mapping = {
            "safe_z": "safe_z_entry",
            "drill_z": "drill_z_entry",
            "feed_rate": "feed_rate_entry",
            "mill_feed": "mill_feed_entry",
            "rapid_rate": "rapid_rate_entry",
            "park_z": "park_z_entry",
        }
        for key, widget_key in mapping.items():
            w = widgets.get(widget_key)
            if w is not None:
                w.delete(0, "end")
                val = self._data.get(key, DEFAULT_PARAMS[key])
                w.insert(0, str(val))

    def read_from_ui(self, widgets: Dict[str, Any]):
        """Прочитать параметры из Entry-виджетов."""
        mapping = {
            "safe_z": "safe_z_entry",
            "drill_z": "drill_z_entry",
            "feed_rate": "feed_rate_entry",
            "mill_feed": "mill_feed_entry",
            "rapid_rate": "rapid_rate_entry",
            "park_z": "park_z_entry",
        }
        for key, widget_key in mapping.items():
            w = widgets.get(widget_key)
            if w is not None:
                try:
                    self._data[key] = float(w.get())
                except ValueError:
                    pass
