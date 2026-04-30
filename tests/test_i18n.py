"""
Тесты для модуля локализации i18n.
"""
import pytest
import os
import sys

# Добавляем корень проекта в путь
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.i18n import t, set_language, get_language, available_languages


def test_default_language():
    """Проверка дефолтного языка."""
    assert get_language() in ["ru", "en"]


def test_available_languages():
    """Проверка списка доступных языков."""
    langs = available_languages()
    assert "ru" in langs
    assert "en" in langs
    assert len(langs) == 2


def test_set_language():
    """Проверка смены языка."""
    set_language("en")
    assert get_language() == "en"
    set_language("ru")
    assert get_language() == "ru"


def test_translation_ru():
    """Проверка перевода на русский."""
    set_language("ru")
    assert "Excellon" in t("app.title", version="1.0")
    assert "Файлы" == t("app.frame.files")
    assert "Открыть" in t("app.btn.open_excellon")


def test_translation_en():
    """Проверка перевода на английский."""
    set_language("en")
    assert "Excellon" in t("app.title", version="1.0")
    assert "Files" == t("app.frame.files")
    assert "Open" in t("app.btn.open_excellon")


def test_translation_with_params():
    """Проверка перевода с параметрами."""
    set_language("ru")
    result = t("app.lbl.holes_file", filename="test.drl")
    assert "test.drl" in result
    assert "Отверстия" in result


def test_missing_key_fallback():
    """Проверка fallback при отсутствии ключа."""
    set_language("ru")
    result = t("nonexistent.key.that.does.not.exist")
    assert result == "nonexistent.key.that.does.not.exist"


def test_format_with_missing_param():
    """Проверка обработки отсутствующих параметров в format."""
    set_language("ru")
    # Если параметр не передан, должен вернуться сырой шаблон
    result = t("app.lbl.holes_file")
    assert "{filename}" in result or "filename" in result.lower()


def test_invalid_language_fallback():
    """Проверка fallback на дефолтный язык при невалидном языке."""
    set_language("invalid_lang")
    assert get_language() == "ru"  # должен откатиться на дефолтный


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
