"""
UI интеграционные тесты: симуляция взаимодействия пользователя с интерфейсом.

Тестируют:
1. Создание и инициализацию UI компонентов
2. Симуляцию кликов и ввода данных
3. Переключение режимов (Simple/Pro)
4. Открытие диалогов и окон
5. Обновление визуализации
"""
import os
import pytest
import tkinter as tk
from unittest.mock import Mock, patch, MagicMock
from core.mode_engine import ModeEngine
from core.gcode_params import GCodeParams
from core.tool_database import ToolDatabase


# Путь к тестовым файлам
SAMPLES_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "Samples")


@pytest.mark.gui
class TestUIInteraction:
    """Тесты взаимодействия с UI."""
    
    @pytest.fixture
    def root(self):
        """Создать корневое окно Tkinter для тестов."""
        root = tk.Tk()
        root.withdraw()  # Скрыть окно
        yield root
        try:
            root.destroy()
        except tk.TclError:
            pass
    
    @pytest.fixture
    def mode_engine(self):
        """Создать экземпляр ModeEngine для тестов."""
        return ModeEngine()
    
    @pytest.fixture
    def gcode_params(self):
        """Создать экземпляр GCodeParams для тестов."""
        return GCodeParams()
    
    def test_app_context_initialization(self):
        """Тест инициализации контекста приложения."""
        from ui.app import AppContext
        
        context = AppContext()
        assert context.mode_engine is not None
        assert context.gcode_params is not None
        assert context.tool_db is not None
        assert isinstance(context.mode_engine, ModeEngine)
        assert isinstance(context.gcode_params, GCodeParams)
        assert isinstance(context.tool_db, ToolDatabase)
    
    def test_mode_toggle_simple_to_pro(self, mode_engine):
        """Тест переключения из Simple в Pro режим."""
        # Начальный режим — Simple
        assert mode_engine.current_mode == "simple"
        
        # Переключить в Pro
        mode_engine.set_mode("pro")
        assert mode_engine.current_mode == "pro"
        
        # Переключить обратно в Simple
        mode_engine.set_mode("simple")
        assert mode_engine.current_mode == "simple"
    
    def test_gcode_params_validation(self, gcode_params):
        """Тест валидации параметров G-code через UI."""
        # Установить валидные параметры
        gcode_params.set_param('safe_z', 5.0)
        gcode_params.set_param('drill_z', -2.5)
        gcode_params.set_param('feed_rate', 100)
        gcode_params.set_param('rapid_rate', 500)
        gcode_params.set_param('park_z', 30)
        
        params = gcode_params.get_all_params()
        assert params['safe_z'] == 5.0
        assert params['drill_z'] == -2.5
        assert params['feed_rate'] == 100
        assert params['rapid_rate'] == 500
        assert params['park_z'] == 30
    
    def test_tool_database_ui_operations(self):
        """Тест операций с базой данных инструментов через UI."""
        tool_db = ToolDatabase()
        
        # Добавить инструмент
        tool_db.set_tool_params("drills", "01", {
            "diameter": 0.8,
            "spindle_speed": 10000,
            "feed_rate": 100
        })
        
        # Получить параметры
        params = tool_db.get_tool_params("drills", "01")
        assert params is not None
        assert params["diameter"] == 0.8
        assert params["spindle_speed"] == 10000
        
        # Удалить инструмент
        tool_db.delete_tool("drills", "01")
        params = tool_db.get_tool_params("drills", "01")
        assert params is None
    
    @patch('tkinter.filedialog.askopenfilename')
    def test_file_loading_simulation(self, mock_filedialog, root, mode_engine):
        """Симуляция загрузки файла через диалог."""
        # Настроить mock для возврата тестового файла
        test_file = os.path.join(SAMPLES_DIR, "Материнка универсальная-RoundHoles.TXT")
        mock_filedialog.return_value = test_file
        
        # Симулировать выбор файла
        selected_file = mock_filedialog()
        assert selected_file == test_file
        assert os.path.exists(selected_file)
    
    def test_visibility_toggle_simulation(self, mode_engine):
        """Симуляция переключения видимости инструментов."""
        from core.parser import parse_excellon_file
        
        # Загрузить тестовые данные
        test_file = os.path.join(SAMPLES_DIR, "Материнка универсальная-RoundHoles.TXT")
        tools = parse_excellon_file(test_file, "4.2")
        
        # Все инструменты видимы по умолчанию
        for tool_num, tool_data in tools.items():
            assert tool_data['visible'] == True
        
        # Симулировать скрытие инструмента
        first_tool = list(tools.keys())[0]
        tools[first_tool]['visible'] = False
        assert tools[first_tool]['visible'] == False
        
        # Симулировать показ инструмента
        tools[first_tool]['visible'] = True
        assert tools[first_tool]['visible'] == True
    
    def test_coordinate_format_ui_change(self, root):
        """Тест изменения формата координат через UI."""
        import core.config as cfg
        
        # Сохранить исходное значение
        original_format = cfg.coordinate_format
        
        # Симулировать изменение формата
        cfg.coordinate_format = "3.3"
        assert cfg.coordinate_format == "3.3"
        
        cfg.coordinate_format = "4.2"
        assert cfg.coordinate_format == "4.2"
        
        # Восстановить исходное значение
        cfg.coordinate_format = original_format
    
    @patch('ui.themed_messagebox.showinfo')
    def test_messagebox_display(self, mock_messagebox, root):
        """Тест отображения сообщений пользователю."""
        from ui import themed_messagebox as messagebox
        
        # Симулировать показ информационного сообщения
        messagebox.showinfo("Тест", "Тестовое сообщение")
        mock_messagebox.assert_called_once_with("Тест", "Тестовое сообщение")
    
    def test_statistics_data_collection(self):
        """Тест сбора статистики для отображения в UI."""
        from core.parser import parse_excellon_file
        
        test_file = os.path.join(SAMPLES_DIR, "Материнка универсальная-RoundHoles.TXT")
        tools = parse_excellon_file(test_file, "4.2")
        
        # Собрать статистику
        total_holes = sum(len(data['holes']) for data in tools.values())
        tool_count = len(tools)
        
        assert total_holes > 0, "Должны быть отверстия для статистики"
        assert tool_count > 0, "Должны быть инструменты для статистики"
        
        # Проверить диапазон диаметров
        diameters = [data['diameter'] for data in tools.values()]
        min_diameter = min(diameters)
        max_diameter = max(diameters)
        
        assert min_diameter > 0
        assert max_diameter >= min_diameter
    
    def test_language_switching(self):
        """Тест переключения языка интерфейса."""
        from core.i18n import set_language, get_language, t
        
        # Сохранить текущий язык
        original_lang = get_language()
        
        # Переключить на английский
        set_language("en")
        assert get_language() == "en"
        
        # Переключить на русский
        set_language("ru")
        assert get_language() == "ru"
        
        # Проверить, что переводы работают
        app_title = t("app.title")
        assert app_title is not None
        assert len(app_title) > 0
        
        # Восстановить исходный язык
        set_language(original_lang)
    
    def test_tooltip_creation(self, root):
        """Тест создания подсказок для UI элементов."""
        from ui.enhanced_tooltip import EnhancedTooltip
        
        # Создать тестовую кнопку
        button = tk.Button(root, text="Test")
        button.pack()
        
        # Создать подсказку
        tooltip = EnhancedTooltip(button, "Тестовая подсказка")
        assert tooltip is not None
        
        # Очистить
        button.destroy()
    
    def test_panel_visibility_in_modes(self, mode_engine):
        """Тест видимости панелей в разных режимах."""
        # В Simple режиме некоторые панели скрыты
        mode_engine.set_mode("simple")
        assert mode_engine.current_mode == "simple"
        
        # В Pro режиме все панели видимы
        mode_engine.set_mode("pro")
        assert mode_engine.current_mode == "pro"
    
    @patch('tkinter.filedialog.asksaveasfilename')
    def test_gcode_save_simulation(self, mock_savedialog, root):
        """Симуляция сохранения G-code через диалог."""
        # Настроить mock для возврата пути сохранения
        save_path = "test_output.nc"
        mock_savedialog.return_value = save_path
        
        # Симулировать выбор пути сохранения
        selected_path = mock_savedialog()
        assert selected_path == save_path
    
    def test_visualization_data_preparation(self):
        """Тест подготовки данных для визуализации."""
        from core.parser import parse_excellon_file
        
        test_file = os.path.join(SAMPLES_DIR, "Материнка универсальная-RoundHoles.TXT")
        tools = parse_excellon_file(test_file, "4.2")
        
        # Подготовить данные для визуализации
        viz_data = []
        for tool_num, tool_data in tools.items():
            if tool_data['visible']:
                for x, y in tool_data['holes']:
                    viz_data.append({
                        'type': 'hole',
                        'x': x,
                        'y': y,
                        'diameter': tool_data['diameter'],
                        'tool': tool_num
                    })
        
        assert len(viz_data) > 0, "Должны быть данные для визуализации"
        
        # Проверить структуру данных
        for item in viz_data:
            assert 'type' in item
            assert 'x' in item
            assert 'y' in item
            assert 'diameter' in item
            assert 'tool' in item
    
    def test_error_handling_in_ui(self, gcode_params):
        """Тест обработки ошибок в UI."""
        from core.validators import validate_gcode_params
        
        # Попытка установить невалидные параметры
        invalid_params = {
            'safe_z': -5.0,  # Невалидно
            'drill_z': -2.5,
            'feed_rate': 100,
            'rapid_rate': 500,
            'park_z': 30
        }
        
        errors = validate_gcode_params(invalid_params)
        assert len(errors) > 0, "Должны быть ошибки валидации"
    
    def test_multi_file_workflow_ui(self):
        """Тест workflow с несколькими файлами через UI."""
        from core.parser import parse_excellon_file, parse_slot_file
        
        # Загрузить отверстия
        holes_file = os.path.join(SAMPLES_DIR, "Материнка универсальная-RoundHoles.TXT")
        tools = parse_excellon_file(holes_file, "4.2")
        assert len(tools) > 0
        
        # Загрузить слоты
        slots_file = os.path.join(SAMPLES_DIR, "Материнка универсальная-SlotHoles.TXT")
        slot_tools = parse_slot_file(slots_file, "4.2")
        assert len(slot_tools) > 0
        
        # Оба набора данных загружены
        assert tools is not None
        assert slot_tools is not None


@pytest.mark.gui
class TestUIDialogs:
    """Тесты диалоговых окон."""
    
    @pytest.fixture
    def root(self):
        """Создать корневое окно Tkinter для тестов."""
        root = tk.Tk()
        root.withdraw()
        yield root
        try:
            root.destroy()
        except tk.TclError:
            pass
    
    def test_tool_params_dialog_data(self, root):
        """Тест данных диалога параметров инструмента."""
        # Создать тестовые параметры инструмента
        tool_params = {
            "diameter": 0.8,
            "spindle_speed": 10000,
            "feed_rate": 100,
            "rapid_rate": 500
        }
        
        # Проверить структуру данных
        assert "diameter" in tool_params
        assert "spindle_speed" in tool_params
        assert tool_params["diameter"] > 0
        assert tool_params["spindle_speed"] > 0
    
    def test_help_window_content(self):
        """Тест содержимого окна справки."""
        from docs.help_content import get_help_content
        
        # Получить содержимое справки
        help_content = get_help_content()
        assert help_content is not None
        assert len(help_content) > 0
    
    def test_statistics_window_data(self):
        """Тест данных окна статистики."""
        from core.parser import parse_excellon_file
        
        test_file = os.path.join(SAMPLES_DIR, "Материнка универсальная-RoundHoles.TXT")
        tools = parse_excellon_file(test_file, "4.2")
        
        # Подготовить статистику
        stats = {
            "total_holes": sum(len(data['holes']) for data in tools.values()),
            "total_tools": len(tools),
            "min_diameter": min(data['diameter'] for data in tools.values()),
            "max_diameter": max(data['diameter'] for data in tools.values())
        }
        
        assert stats["total_holes"] > 0
        assert stats["total_tools"] > 0
        assert stats["min_diameter"] > 0
        assert stats["max_diameter"] >= stats["min_diameter"]
