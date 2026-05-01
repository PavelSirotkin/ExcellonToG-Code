"""
Тест для проверки отсутствия утечки памяти в ui/legend.py
"""
import unittest
import tkinter as tk
from unittest.mock import MagicMock, patch
import sys
import os
import pytest

# Добавляем корневую директорию в путь
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import core.config as cfg
from ui.legend import update_legend


@pytest.mark.gui
class TestLegendMemoryLeak(unittest.TestCase):
    """Тесты для проверки отсутствия утечки памяти при обновлении легенды."""
    
    def setUp(self):
        """Подготовка тестового окружения."""
        self.root = tk.Tk()
        self.root.withdraw()  # Скрыть окно
        
        # Создать тестовый legend_frame
        self.legend_frame = tk.Frame(self.root)
        cfg.widgets["legend_frame"] = self.legend_frame
        cfg.widgets["legend_canvas"] = tk.Canvas(self.root)
        cfg.widgets["root"] = self.root
        
        # Сбросить реестр themed_widgets
        cfg._themed_widgets = []
        
        # Настроить тестовые данные
        cfg.current_tools = {
            "T01": {"diameter": 0.8, "holes": [(0, 0), (1, 1)], "visible": True, "var": None}
        }
        cfg.slot_tools = None
        cfg.board_outline = None
    
    def tearDown(self):
        """Очистка после теста."""
        try:
            self.root.destroy()
        except:
            pass
        cfg.current_tools = None
        cfg.slot_tools = None
        cfg.board_outline = None
        cfg._themed_widgets = []
    
    def test_no_memory_leak_on_multiple_updates(self):
        """Проверка, что повторные вызовы update_legend() не приводят к утечке памяти."""
        # Первое обновление
        update_legend()
        initial_widget_count = len(cfg._themed_widgets)
        
        # Второе обновление
        update_legend()
        second_widget_count = len(cfg._themed_widgets)
        
        # Третье обновление
        update_legend()
        third_widget_count = len(cfg._themed_widgets)
        
        # Количество зарегистрированных виджетов должно оставаться примерно одинаковым
        # (может быть небольшая разница из-за особенностей создания виджетов)
        self.assertEqual(
            initial_widget_count, second_widget_count,
            f"Утечка памяти: после второго обновления {second_widget_count} виджетов вместо {initial_widget_count}"
        )
        self.assertEqual(
            second_widget_count, third_widget_count,
            f"Утечка памяти: после третьего обновления {third_widget_count} виджетов вместо {second_widget_count}"
        )
    
    def test_widgets_unregistered_before_destroy(self):
        """Проверка, что виджеты отменяют регистрацию перед уничтожением."""
        # Создать легенду
        update_legend()
        widget_count_after_first = len(cfg._themed_widgets)
        
        # Запомнить виджеты
        old_widgets = [w for w, _ in cfg._themed_widgets]
        
        # Обновить легенду (старые виджеты должны быть уничтожены и отменена их регистрация)
        update_legend()
        
        # Проверить, что старые виджеты больше не в реестре
        new_widgets = [w for w, _ in cfg._themed_widgets]
        for old_widget in old_widgets:
            self.assertNotIn(
                old_widget, new_widgets,
                "Старый виджет остался в реестре после update_legend()"
            )
    
    def test_unregister_themed_widget_function(self):
        """Проверка работы функции unregister_themed_widget()."""
        # Создать тестовый виджет
        test_widget = tk.Label(self.root, text="Test")
        
        # Зарегистрировать
        cfg.register_themed_widget(test_widget, bg="panel_bg", fg="panel_fg")
        self.assertEqual(len(cfg._themed_widgets), 1)
        
        # Отменить регистрацию
        cfg.unregister_themed_widget(test_widget)
        self.assertEqual(len(cfg._themed_widgets), 0)
    
    def test_unregister_nonexistent_widget(self):
        """Проверка, что отмена регистрации несуществующего виджета не вызывает ошибок."""
        test_widget = tk.Label(self.root, text="Test")
        
        # Попытка отменить регистрацию незарегистрированного виджета
        try:
            cfg.unregister_themed_widget(test_widget)
        except Exception as e:
            self.fail(f"unregister_themed_widget() вызвала исключение: {e}")


if __name__ == "__main__":
    unittest.main()
