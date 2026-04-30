"""
Система локализации интерфейса.

Использование:
    from core.i18n import t, set_language, get_language

    label = tk.Label(parent, text=t("app.btn.open_excellon"))
    msg = t("err.write_msg", error=str(e))

Словари хранятся в `i18n/strings_<lang>.json` рядом с корнем проекта.
При отсутствии перевода ключ возвращается как есть, что упрощает отладку.
"""
import json
import os
import sys
from typing import Dict, List, Optional


_DEFAULT_LANGUAGE = "ru"
_SUPPORTED_LANGUAGES = ("ru", "en")

_strings: Dict[str, str] = {}
_lang: str = _DEFAULT_LANGUAGE
_listeners: List = []


def _project_root() -> str:
    """Корень проекта (для PyInstaller-сборки — временная папка _MEIPASS)."""
    if getattr(sys, "frozen", False):
        # PyInstaller распаковывает файлы в sys._MEIPASS
        return sys._MEIPASS
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _strings_path(lang: str) -> str:
    return os.path.join(_project_root(), "i18n", f"strings_{lang}.json")


def _load_strings(lang: str) -> Dict[str, str]:
    """Загрузить словарь строк для указанного языка."""
    path = _strings_path(lang)
    if not os.path.isfile(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return {}


def set_language(lang: str) -> None:
    """Установить активный язык. Уведомить всех слушателей."""
    global _strings, _lang
    if lang not in _SUPPORTED_LANGUAGES:
        lang = _DEFAULT_LANGUAGE
    _lang = lang
    _strings = _load_strings(lang)
    for cb in list(_listeners):
        try:
            cb()
        except Exception:
            pass


def get_language() -> str:
    return _lang


def available_languages() -> List[str]:
    return list(_SUPPORTED_LANGUAGES)


def t(key: str, **kwargs) -> str:
    """Перевод по ключу с подстановкой параметров.

    Если ключ отсутствует в словаре — возвращается сам ключ
    (упрощает поиск пропущенных переводов в UI).
    """
    raw = _strings.get(key, key)
    if kwargs:
        try:
            return raw.format(**kwargs)
        except (KeyError, IndexError):
            return raw
    return raw


def register_listener(callback) -> None:
    """Зарегистрировать колбэк, вызываемый при смене языка.

    Используется UI-модулями для перерисовки заголовков/надписей.
    """
    if callback not in _listeners:
        _listeners.append(callback)


def unregister_listener(callback) -> None:
    if callback in _listeners:
        _listeners.remove(callback)


# Автозагрузка дефолтного языка при импорте
_strings = _load_strings(_lang)
