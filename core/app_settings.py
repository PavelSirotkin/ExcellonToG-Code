"""
Хранилище пользовательских настроек приложения (язык, тема и т.п.).

Сохраняется в `app_settings.json` в корне проекта (рядом с `gcode_params.json`).
"""
import json
import os
import sys
from typing import Any, Dict


DEFAULT_SETTINGS: Dict[str, Any] = {
    "language": "ru",
    "theme": "light",
}


class AppSettings:
    """Простое JSON-хранилище настроек приложения."""

    def __init__(self):
        self._path: str = ""
        self._data: Dict[str, Any] = dict(DEFAULT_SETTINGS)

    @property
    def path(self) -> str:
        return self._path

    @path.setter
    def path(self, value: str) -> None:
        self._path = value

    def get(self, key: str, default: Any = None) -> Any:
        if default is None:
            default = DEFAULT_SETTINGS.get(key)
        return self._data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        self._data[key] = value

    def load(self, path: str = "") -> bool:
        """Загрузить настройки из JSON. При отсутствии файла — создать с default."""
        p = path or self._path
        if not p:
            return False
        self._path = p
        if not os.path.isfile(p):
            self._data = dict(DEFAULT_SETTINGS)
            self.save()
            return True
        try:
            with open(p, "r", encoding="utf-8") as f:
                data = json.load(f)
            merged = dict(DEFAULT_SETTINGS)
            merged.update(data)
            self._data = merged
            return True
        except (json.JSONDecodeError, IOError):
            self._data = dict(DEFAULT_SETTINGS)
            return False

    def save(self, path: str = "") -> bool:
        """Сохранить настройки в JSON."""
        p = path or self._path
        if not p:
            return False
        self._path = p
        try:
            os.makedirs(os.path.dirname(os.path.abspath(p)), exist_ok=True)
            with open(p, "w", encoding="utf-8") as f:
                json.dump(self._data, f, indent=2, ensure_ascii=False)
            return True
        except IOError:
            return False


def default_settings_path() -> str:
    """Путь к файлу настроек (рядом с .exe или с исходниками)."""
    if getattr(sys, "frozen", False):
        return os.path.join(os.path.dirname(sys.executable), "app_settings.json")
    project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(project_dir, "app_settings.json")


# Глобальный синглтон настроек
settings = AppSettings()
