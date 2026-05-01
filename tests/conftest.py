"""
Конфигурация pytest для всех тестов.

Этот файл автоматически выполняется перед запуском тестов
и устанавливает язык по умолчанию, чтобы избежать race condition
в системе локализации.
"""
import sys
import os
import pytest

# Добавляем корень проекта в путь
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Устанавливаем язык ДО любых импортов, которые могут использовать i18n
from core.i18n import set_language

# Устанавливаем дефолтный язык для тестов
# Это предотвращает race condition в docs/help_content.py
set_language("ru")


def pytest_configure(config):
    """Регистрация маркеров для pytest."""
    config.addinivalue_line(
        "markers", "gui: тесты, требующие GUI (Tkinter)"
    )
    config.addinivalue_line(
        "markers", "slow: медленные тесты (> 1 секунды)"
    )
    config.addinivalue_line(
        "markers", "integration: интеграционные тесты"
    )


def pytest_collection_modifyitems(config, items):
    """Автоматически пропускать GUI-тесты если Tkinter недоступен."""
    try:
        import tkinter as tk
        # Попытка создать Tk для проверки работоспособности
        root = tk.Tk()
        root.destroy()
        tkinter_available = True
    except Exception:
        tkinter_available = False
    
    if not tkinter_available:
        skip_gui = pytest.mark.skip(reason="Tkinter недоступен или не настроен")
        for item in items:
            if "gui" in item.keywords:
                item.add_marker(skip_gui)
