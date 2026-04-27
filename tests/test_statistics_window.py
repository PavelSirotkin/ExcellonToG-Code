"""
Тесты для модуля statistics_window.
"""
import unittest
import math
from unittest.mock import Mock, patch, MagicMock
import sys
import os

# Добавляем корневую директорию в путь
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import core.config as cfg
from core.gerber_parser import make_line, make_arc


class TestStatisticsCalculations(unittest.TestCase):
    """Тесты расчётов статистики."""
    
    def setUp(self):
        """Подготовка тестовых данных."""
        # Сохраняем оригинальные значения
        self.orig_current_tools = cfg.current_tools
        self.orig_slot_tools = cfg.slot_tools
        self.orig_board_outline = cfg.board_outline
        self.orig_board_outline_visible = cfg.board_outline_visible
        
        # Мокаем параметры
        cfg.get_param = Mock(side_effect=lambda key: {
            'rapid_rate': 500,
            'feed_rate': 100,
            'mill_feed': 50,
            'safe_z': 5.0,
            'drill_z': -2.5,
            'outline_depth_per_pass': 2.5,
            'outline_n_tabs': 0,
            'outline_tab_height': 1.0,
            'outline_tool_diameter': 3.0
        }.get(key, 0))
    
    def tearDown(self):
        """Восстановление оригинальных значений."""
        cfg.current_tools = self.orig_current_tools
        cfg.slot_tools = self.orig_slot_tools
        cfg.board_outline = self.orig_board_outline
        cfg.board_outline_visible = self.orig_board_outline_visible
    
    def test_calculate_holes_path(self):
        """Тест расчёта пути для отверстий."""
        cfg.current_tools = {
            1: {
                'diameter': 1.0,
                'visible': True,
                'holes': [(0, 0), (10, 0), (10, 10)]
            }
        }
        cfg.slot_tools = {}
        cfg.board_outline = None
        
        # Импортируем после настройки моков
        from ui.statistics_window import StatisticsWindow
        
        # Создаём мок родительского окна
        parent = Mock()
        parent.winfo_x = Mock(return_value=100)
        parent.winfo_y = Mock(return_value=100)
        parent.winfo_width = Mock(return_value=800)
        parent.winfo_height = Mock(return_value=600)
        
        with patch('tkinter.Toplevel'):
            with patch('tkinter.Canvas'):
                with patch('tkinter.Scrollbar'):
                    with patch('tkinter.Frame'):
                        stats = StatisticsWindow.__new__(StatisticsWindow)
                        stats.collect_data()
                        stats.calculate_paths()
        
        # Проверяем расчёты
        self.assertEqual(stats.total_holes, 3)
        self.assertEqual(stats.drill_tools_count, 1)
        # Путь: origin->(0,0)=0, (0,0)->(10,0)=10, (10,0)->(10,10)=10,
        # затем парковка (10,10)->origin = sqrt(200) ~ 14.142
        expected_rapid = 0 + 10 + 10 + math.hypot(10, 10)
        self.assertAlmostEqual(stats.total_rapid, expected_rapid, places=1)
    
    def test_calculate_slots_path(self):
        """Тест расчёта пути для слотов.
        
        Каждый слот — это одно движение фрезы, независимо от количества слотов.
        """
        cfg.current_tools = {}
        cfg.slot_tools = {
            1: {
                'diameter': 2.0,
                'visible': True,
                'slots': [((0, 0), (10, 0)), ((20, 0), (20, 10))]
            }
        }
        cfg.board_outline = None

        from ui.statistics_window import StatisticsWindow

        parent = Mock()
        parent.winfo_x = Mock(return_value=100)
        parent.winfo_y = Mock(return_value=100)
        parent.winfo_width = Mock(return_value=800)
        parent.winfo_height = Mock(return_value=600)

        with patch('tkinter.Toplevel'):
            with patch('tkinter.Canvas'):
                with patch('tkinter.Scrollbar'):
                    with patch('tkinter.Frame'):
                        stats = StatisticsWindow.__new__(StatisticsWindow)
                        stats.collect_data()
                        stats.calculate_paths()

        # Проверяем расчёты
        # total_slots = 1 (одна фреза проходит все слоты)
        # slot_tools_count = 1 (один инструмент)
        self.assertEqual(stats.total_slots, 1)
        self.assertEqual(stats.slot_tools_count, 1)
        # Фрезеровка: (0,0)->(10,0) = 10, (20,0)->(20,10) = 10
        expected_slot_feed = 10 + 10
        self.assertAlmostEqual(stats.slot_feed_dist, expected_slot_feed, places=1)
        # Rapid: origin->(0,0)=0, end-сегмент-1 (10,0)->start-сегмент-2 (20,0)=10,
        # парковка (20,10)->origin = sqrt(400+100) ~ 22.361
        expected_rapid = 0 + 10 + math.hypot(20, 10)
        self.assertAlmostEqual(stats.total_rapid, expected_rapid, places=1)
    
    def test_calculate_outline_path_lines(self):
        """Тест расчёта пути для контура (линии).

        Использует реальный формат gerber_parser ('p1'/'p2' для линий)
        через make_line — чтобы тест соответствовал production-данным.
        """
        cfg.current_tools = {}
        cfg.slot_tools = {}
        cfg.board_outline = [
            make_line((0, 0), (100, 0)),
            make_line((100, 0), (100, 50)),
            make_line((100, 50), (0, 50)),
            make_line((0, 50), (0, 0)),
        ]
        cfg.board_outline_visible = True

        from ui.statistics_window import StatisticsWindow

        parent = Mock()
        parent.winfo_x = Mock(return_value=100)
        parent.winfo_y = Mock(return_value=100)
        parent.winfo_width = Mock(return_value=800)
        parent.winfo_height = Mock(return_value=600)

        with patch('tkinter.Toplevel'):
            with patch('tkinter.Canvas'):
                with patch('tkinter.Scrollbar'):
                    with patch('tkinter.Frame'):
                        stats = StatisticsWindow.__new__(StatisticsWindow)
                        stats.collect_data()
                        stats.calculate_paths()

        # Проверяем расчёты контура
        # Периметр прямоугольника: 100 + 50 + 100 + 50 = 300
        expected_outline = 100 + 50 + 100 + 50
        self.assertAlmostEqual(stats.outline_feed_dist, expected_outline, places=1)
        # Rapid контура: origin->(0,0)=0 + сегменты замкнуты (стыки p2->p1=0)
        # + парковка (0,0)->origin = 0. Итого 0.
        self.assertAlmostEqual(stats.outline_rapid, 0.0, places=1)
    
    def test_calculate_outline_path_arcs(self):
        """Тест расчёта длины дуги — точное значение через r и углы.

        Используем четверть окружности r=10 от (10,0) до (0,10), CCW,
        центр в (0,0). Точная длина = π·r/2 ≈ 15.708.
        Раньше код считал хорду·1.2 = √200·1.2 ≈ 16.97 (~8% переоценка).
        """
        cfg.current_tools = {}
        cfg.slot_tools = {}
        cfg.board_outline = [
            make_arc(center=(0, 0), r=10.0,
                     start=(10, 0), end=(0, 10), ccw=True),
        ]
        cfg.board_outline_visible = True

        from ui.statistics_window import StatisticsWindow

        parent = Mock()
        parent.winfo_x = Mock(return_value=100)
        parent.winfo_y = Mock(return_value=100)
        parent.winfo_width = Mock(return_value=800)
        parent.winfo_height = Mock(return_value=600)

        with patch('tkinter.Toplevel'):
            with patch('tkinter.Canvas'):
                with patch('tkinter.Scrollbar'):
                    with patch('tkinter.Frame'):
                        stats = StatisticsWindow.__new__(StatisticsWindow)
                        stats.collect_data()
                        stats.calculate_paths()

        # Точная длина четверти окружности = π·r/2
        expected = math.pi * 10.0 / 2
        self.assertAlmostEqual(stats.outline_feed_dist, expected, places=2)
    
    def test_board_dimensions(self):
        """Тест расчёта размеров платы."""
        cfg.current_tools = {
            1: {
                'diameter': 1.0,
                'visible': True,
                'holes': [(10, 20), (50, 80)]
            }
        }
        cfg.slot_tools = {}
        cfg.board_outline = None
        
        from ui.statistics_window import StatisticsWindow
        
        parent = Mock()
        parent.winfo_x = Mock(return_value=100)
        parent.winfo_y = Mock(return_value=100)
        parent.winfo_width = Mock(return_value=800)
        parent.winfo_height = Mock(return_value=600)
        
        with patch('tkinter.Toplevel'):
            with patch('tkinter.Canvas'):
                with patch('tkinter.Scrollbar'):
                    with patch('tkinter.Frame'):
                        stats = StatisticsWindow.__new__(StatisticsWindow)
                        stats.collect_data()
        
        # Проверяем размеры
        self.assertEqual(stats.min_x, 10)
        self.assertEqual(stats.max_x, 50)
        self.assertEqual(stats.min_y, 20)
        self.assertEqual(stats.max_y, 80)
        self.assertEqual(stats.board_w, 40)
        self.assertEqual(stats.board_h, 60)
        self.assertAlmostEqual(stats.board_area, 24.0, places=1)  # 40*60/100
    
    def test_time_calculation(self):
        """Тест расчёта времени обработки."""
        cfg.current_tools = {
            1: {
                'diameter': 1.0,
                'visible': True,
                'holes': [(0, 0), (100, 0)]  # 100мм между отверстиями
            }
        }
        cfg.slot_tools = {}
        cfg.board_outline = None
        
        from ui.statistics_window import StatisticsWindow
        
        parent = Mock()
        parent.winfo_x = Mock(return_value=100)
        parent.winfo_y = Mock(return_value=100)
        parent.winfo_width = Mock(return_value=800)
        parent.winfo_height = Mock(return_value=600)
        
        with patch('tkinter.Toplevel'):
            with patch('tkinter.Canvas'):
                with patch('tkinter.Scrollbar'):
                    with patch('tkinter.Frame'):
                        stats = StatisticsWindow.__new__(StatisticsWindow)
                        stats.collect_data()
                        stats.calculate_paths()
        
        # Проверяем время
        # rapid_rate = 500 мм/мин, путь = 100мм
        # время = 100/500 * 60 = 12 сек
        self.assertGreater(stats.time_rapid, 0)
        self.assertGreater(stats.total_time_sec, 0)
    
    def test_invisible_tools_ignored(self):
        """Тест игнорирования невидимых инструментов."""
        cfg.current_tools = {
            1: {
                'diameter': 1.0,
                'visible': False,
                'holes': [(0, 0), (10, 0)]
            },
            2: {
                'diameter': 2.0,
                'visible': True,
                'holes': [(20, 0)]
            }
        }
        cfg.slot_tools = {}
        cfg.board_outline = None
        
        from ui.statistics_window import StatisticsWindow
        
        parent = Mock()
        parent.winfo_x = Mock(return_value=100)
        parent.winfo_y = Mock(return_value=100)
        parent.winfo_width = Mock(return_value=800)
        parent.winfo_height = Mock(return_value=600)
        
        with patch('tkinter.Toplevel'):
            with patch('tkinter.Canvas'):
                with patch('tkinter.Scrollbar'):
                    with patch('tkinter.Frame'):
                        stats = StatisticsWindow.__new__(StatisticsWindow)
                        stats.collect_data()
        
        # Проверяем, что учтён только видимый инструмент
        self.assertEqual(stats.total_holes, 1)
        self.assertEqual(stats.drill_tools_count, 1)
        self.assertEqual(len(stats.tool_data), 1)
        self.assertEqual(stats.tool_data[0]['num'], 2)
    
    def test_empty_data(self):
        """Тест обработки пустых данных."""
        cfg.current_tools = {}
        cfg.slot_tools = {}
        cfg.board_outline = None
        
        from ui.statistics_window import StatisticsWindow
        
        parent = Mock()
        parent.winfo_x = Mock(return_value=100)
        parent.winfo_y = Mock(return_value=100)
        parent.winfo_width = Mock(return_value=800)
        parent.winfo_height = Mock(return_value=600)
        
        with patch('tkinter.Toplevel'):
            with patch('tkinter.Canvas'):
                with patch('tkinter.Scrollbar'):
                    with patch('tkinter.Frame'):
                        stats = StatisticsWindow.__new__(StatisticsWindow)
                        stats.collect_data()
                        stats.calculate_paths()
        
        # Проверяем нулевые значения
        self.assertEqual(stats.total_holes, 0)
        self.assertEqual(stats.total_slots, 0)
        self.assertEqual(stats.total_rapid, 0)
        self.assertEqual(stats.total_feed, 0)
        self.assertEqual(stats.slot_feed_dist, 0)
        self.assertEqual(stats.outline_feed_dist, 0)
    
    def test_outline_multipass_scales(self):
        """Тест масштабирования длины контура при multi-pass.
        
        При depth_per_pass=0.5 и drill_z=-2.5 получаем 5 проходов.
        Периметр должен увеличиться в 5 раз.
        """
        cfg.current_tools = {}
        cfg.slot_tools = {}
        cfg.board_outline = [
            make_line((0, 0), (100, 0)),
            make_line((100, 0), (100, 50)),
            make_line((100, 50), (0, 50)),
            make_line((0, 50), (0, 0)),
        ]
        cfg.board_outline_visible = True
        
        # Переопределяем get_param для этого теста
        cfg.get_param = Mock(side_effect=lambda key: {
            'rapid_rate': 500,
            'feed_rate': 100,
            'mill_feed': 50,
            'safe_z': 5.0,
            'drill_z': -2.5,
            'outline_depth_per_pass': 0.5,  # 5 проходов
            'outline_n_tabs': 0,
            'outline_tab_height': 1.0,
            'outline_tool_diameter': 3.0
        }.get(key, 0))
        
        from ui.statistics_window import StatisticsWindow
        
        parent = Mock()
        parent.winfo_x = Mock(return_value=100)
        parent.winfo_y = Mock(return_value=100)
        parent.winfo_width = Mock(return_value=800)
        parent.winfo_height = Mock(return_value=600)
        
        with patch('tkinter.Toplevel'):
            with patch('tkinter.Canvas'):
                with patch('tkinter.Scrollbar'):
                    with patch('tkinter.Frame'):
                        stats = StatisticsWindow.__new__(StatisticsWindow)
                        stats.collect_data()
                        stats.calculate_paths()
        
        # Периметр: 100 + 50 + 100 + 50 = 300
        # С 5 проходами: 300 × 5 = 1500
        expected_outline = 300 * 5
        self.assertAlmostEqual(stats.outline_feed_dist, expected_outline, places=1)
    
    def test_outline_passes_add_z_travel(self):
        """Тест добавления Z-движений при multi-pass.
        
        Для n_passes=5, safe_z=5, drill_z=-2.5:
        - Каждый проход: plunge от 5 до -(k×0.5), retract обратно
        - Суммарно Z-движения должны увеличить total_feed и total_rapid
        """
        cfg.current_tools = {}
        cfg.slot_tools = {}
        cfg.board_outline = [
            make_line((0, 0), (100, 0)),
            make_line((100, 0), (100, 50)),
            make_line((100, 50), (0, 50)),
            make_line((0, 50), (0, 0)),
        ]
        cfg.board_outline_visible = True
        
        # Тест с 1 проходом
        cfg.get_param = Mock(side_effect=lambda key: {
            'rapid_rate': 500,
            'feed_rate': 100,
            'mill_feed': 50,
            'safe_z': 5.0,
            'drill_z': -2.5,
            'outline_depth_per_pass': 2.5,  # 1 проход
            'outline_n_tabs': 0,
            'outline_tab_height': 1.0,
            'outline_tool_diameter': 3.0
        }.get(key, 0))
        
        from ui.statistics_window import StatisticsWindow
        
        parent = Mock()
        parent.winfo_x = Mock(return_value=100)
        parent.winfo_y = Mock(return_value=100)
        parent.winfo_width = Mock(return_value=800)
        parent.winfo_height = Mock(return_value=600)
        
        with patch('tkinter.Toplevel'):
            with patch('tkinter.Canvas'):
                with patch('tkinter.Scrollbar'):
                    with patch('tkinter.Frame'):
                        stats1 = StatisticsWindow.__new__(StatisticsWindow)
                        stats1.collect_data()
                        stats1.calculate_paths()
        
        total_feed_1pass = stats1.total_feed
        total_rapid_1pass = stats1.total_rapid
        
        # Тест с 5 проходами
        cfg.get_param = Mock(side_effect=lambda key: {
            'rapid_rate': 500,
            'feed_rate': 100,
            'mill_feed': 50,
            'safe_z': 5.0,
            'drill_z': -2.5,
            'outline_depth_per_pass': 0.5,  # 5 проходов
            'outline_n_tabs': 0,
            'outline_tab_height': 1.0,
            'outline_tool_diameter': 3.0
        }.get(key, 0))
        
        with patch('tkinter.Toplevel'):
            with patch('tkinter.Canvas'):
                with patch('tkinter.Scrollbar'):
                    with patch('tkinter.Frame'):
                        stats5 = StatisticsWindow.__new__(StatisticsWindow)
                        stats5.collect_data()
                        stats5.calculate_paths()
        
        total_feed_5pass = stats5.total_feed
        total_rapid_5pass = stats5.total_rapid
        
        # Z-движения должны увеличиться
        # Для 1 прохода: plunge = 5+2.5 = 7.5, retract = 7.5
        # Для 5 проходов: sum(5+0.5k) для k=1..5 = 5×5 + 0.5×(1+2+3+4+5) = 25+7.5 = 32.5 каждое
        expected_feed_increase = 32.5 - 7.5  # 25
        expected_rapid_increase = 32.5 - 7.5  # 25
        
        self.assertAlmostEqual(total_feed_5pass - total_feed_1pass, expected_feed_increase, places=1)
        self.assertAlmostEqual(total_rapid_5pass - total_rapid_1pass, expected_rapid_increase, places=1)
    
    def test_outline_tabs_add_z_travel(self):
        """Тест добавления Z-движений для tabs.
        
        Tabs добавляют 2 × n_tabs × tab_height к total_feed.
        outline_feed_dist остаётся неизменным (XY-длина та же).
        """
        cfg.current_tools = {}
        cfg.slot_tools = {}
        cfg.board_outline = [
            make_line((0, 0), (100, 0)),
            make_line((100, 0), (100, 50)),
            make_line((100, 50), (0, 50)),
            make_line((0, 50), (0, 0)),
        ]
        cfg.board_outline_visible = True
        
        # Тест без tabs
        cfg.get_param = Mock(side_effect=lambda key: {
            'rapid_rate': 500,
            'feed_rate': 100,
            'mill_feed': 50,
            'safe_z': 5.0,
            'drill_z': -2.5,
            'outline_depth_per_pass': 2.5,
            'outline_n_tabs': 0,  # Без tabs
            'outline_tab_height': 1.0,
            'outline_tool_diameter': 3.0
        }.get(key, 0))
        
        from ui.statistics_window import StatisticsWindow
        
        parent = Mock()
        parent.winfo_x = Mock(return_value=100)
        parent.winfo_y = Mock(return_value=100)
        parent.winfo_width = Mock(return_value=800)
        parent.winfo_height = Mock(return_value=600)
        
        with patch('tkinter.Toplevel'):
            with patch('tkinter.Canvas'):
                with patch('tkinter.Scrollbar'):
                    with patch('tkinter.Frame'):
                        stats_no_tabs = StatisticsWindow.__new__(StatisticsWindow)
                        stats_no_tabs.collect_data()
                        stats_no_tabs.calculate_paths()
        
        feed_no_tabs = stats_no_tabs.total_feed
        outline_dist_no_tabs = stats_no_tabs.outline_feed_dist
        
        # Тест с 4 tabs
        cfg.get_param = Mock(side_effect=lambda key: {
            'rapid_rate': 500,
            'feed_rate': 100,
            'mill_feed': 50,
            'safe_z': 5.0,
            'drill_z': -2.5,
            'outline_depth_per_pass': 2.5,
            'outline_n_tabs': 4,  # 4 tabs
            'outline_tab_height': 1.0,
            'outline_tool_diameter': 3.0
        }.get(key, 0))
        
        with patch('tkinter.Toplevel'):
            with patch('tkinter.Canvas'):
                with patch('tkinter.Scrollbar'):
                    with patch('tkinter.Frame'):
                        stats_with_tabs = StatisticsWindow.__new__(StatisticsWindow)
                        stats_with_tabs.collect_data()
                        stats_with_tabs.calculate_paths()
        
        feed_with_tabs = stats_with_tabs.total_feed
        outline_dist_with_tabs = stats_with_tabs.outline_feed_dist
        
        # outline_feed_dist должен остаться одинаковым (XY-длина не меняется)
        self.assertAlmostEqual(outline_dist_no_tabs, outline_dist_with_tabs, places=1)
        
        # total_feed должен увеличиться на 2 × 4 × 1.0 = 8 мм
        expected_increase = 2 * 4 * 1.0
        self.assertAlmostEqual(feed_with_tabs - feed_no_tabs, expected_increase, places=1)


if __name__ == '__main__':
    unittest.main()
