# GUI-тесты и Tkinter

## Проблема

Тесты, использующие Tkinter, могут падать в окружениях, где:
- Tkinter не установлен или настроен неправильно
- Отсутствуют необходимые файлы Tcl/Tk
- Нет доступа к дисплею (headless-окружения, CI/CD)

## Решение

Все GUI-тесты помечены маркером `@pytest.mark.gui` и автоматически пропускаются, если Tkinter недоступен.

### Как это работает

1. **conftest.py** проверяет доступность Tkinter при запуске тестов
2. Если Tkinter недоступен, все тесты с маркером `gui` автоматически пропускаются
3. Остальные тесты выполняются нормально

### Пометка GUI-тестов

Для тестовых классов:
```python
import pytest

@pytest.mark.gui
class TestMyGUIFeature(unittest.TestCase):
    def setUp(self):
        self.root = tk.Tk()
        # ...
```

Для отдельных тестов:
```python
@pytest.mark.gui
def test_something_with_tkinter():
    root = tk.Tk()
    # ...
```

### Запуск тестов

Запуск всех тестов (GUI-тесты пропускаются при недоступности Tkinter):
```bash
python -m pytest tests/
```

Запуск только GUI-тестов:
```bash
python -m pytest tests/ -m gui
```

Запуск всех тестов кроме GUI:
```bash
python -m pytest tests/ -m "not gui"
```

## Текущие GUI-тесты

- `tests/test_legend_memory_leak.py` - тесты утечек памяти в легенде
