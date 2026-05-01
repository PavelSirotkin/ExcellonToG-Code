# Интеграционные тесты ExcellonToG-Code

## Обзор

Интеграционные тесты проверяют полный workflow приложения от загрузки файлов до генерации G-code. В отличие от unit-тестов, которые тестируют отдельные функции, интеграционные тесты проверяют взаимодействие между модулями.

## Структура

```
tests/integration/
├── __init__.py                  # Пакет интеграционных тестов
├── README.md                    # Краткое описание
├── INTEGRATION_TESTS.md         # Подробная документация (этот файл)
├── test_full_workflow.py        # End-to-end тесты (9 тестов)
├── test_ui_interaction.py       # UI-тесты (28 тестов, требуют GUI)
└── test_performance.py          # Performance-тесты (2 быстрых + 26 медленных)
```

## Категории тестов

### 1. End-to-End тесты (`test_full_workflow.py`)

Проверяют полный цикл обработки файлов:

- **test_excellon_to_gcode_basic_workflow** - Базовый workflow: Excellon → G-code
- **test_slot_to_gcode_workflow** - Workflow для слотов
- **test_combined_workflow** - Комбинированный режим (отверстия + слоты)
- **test_gerber_outline_workflow** - Парсинг контура платы из Gerber
- **test_workflow_with_tool_database** - Использование базы данных инструментов
- **test_workflow_with_invalid_file** - Обработка ошибок при невалидных файлах
- **test_workflow_with_invalid_params** - Обработка ошибок при невалидных параметрах
- **test_coordinate_format_detection** - Автоопределение формата координат
- **test_gcode_output_format** - Проверка формата выходного G-code

**Запуск:**
```bash
pytest tests/integration/test_full_workflow.py -v
```

### 2. UI-тесты (`test_ui_interaction.py`)

Тестируют взаимодействие с пользовательским интерфейсом:

- Загрузка файлов через UI
- Изменение параметров G-code
- Переключение видимости инструментов
- Работа с базой данных инструментов
- Генерация G-code через UI
- Визуализация результатов
- Статистика обработки
- Навигация и масштабирование
- Экспорт/импорт настроек

**Маркер:** `@pytest.mark.gui`

**Запуск:**
```bash
# Запустить все UI-тесты
pytest tests/integration/test_ui_interaction.py -v -m gui

# Пропустить UI-тесты
pytest tests/integration/ -v -m "not gui"
```

**Примечание:** UI-тесты автоматически пропускаются, если Tkinter недоступен.

### 3. Performance-тесты (`test_performance.py`)

Проверяют производительность на больших объёмах данных:

#### Быстрые тесты (не требуют маркера `slow`):
- **test_memory_efficiency_large_file** - Эффективность памяти (1000 отверстий)
- **test_gcode_generation_scalability** - Масштабируемость генерации G-code

#### Медленные тесты (маркер `@pytest.mark.slow`):
- **test_large_excellon_file** - Обработка 10000 отверстий
- **test_large_slot_file** - Обработка 1000 слотов
- **test_tsp_optimization_performance** - TSP оптимизация на 500 точках
- **test_gerber_outline_complex** - Сложный контур (1000 сегментов)
- **test_multipass_slot_performance** - Multi-pass фрезеровка
- **test_memory_usage_monitoring** - Мониторинг использования памяти
- И другие...

**Запуск:**
```bash
# Только быстрые performance-тесты
pytest tests/integration/test_performance.py -v -m "not slow"

# Все performance-тесты (включая медленные)
pytest tests/integration/test_performance.py -v

# Только медленные тесты
pytest tests/integration/test_performance.py -v -m slow
```

## Маркеры pytest

Интеграционные тесты используют следующие маркеры:

- **`@pytest.mark.integration`** - Интеграционный тест
- **`@pytest.mark.gui`** - Требует GUI (Tkinter)
- **`@pytest.mark.slow`** - Медленный тест (> 1 секунды)

## Запуск тестов

### Все интеграционные тесты (быстрые)
```bash
pytest tests/integration/ -v -m "not slow and not gui"
```

### Все тесты проекта (быстрые, без GUI)
```bash
pytest tests/ -v -m "not slow and not gui"
```

### С покрытием кода
```bash
pytest tests/integration/ -v --cov=core --cov=ui --cov-report=html
```

### Только end-to-end тесты
```bash
pytest tests/integration/test_full_workflow.py -v
```

### Все тесты (включая медленные и GUI)
```bash
pytest tests/integration/ -v
```

## Статистика

### Общее количество тестов в проекте
- **Unit-тесты:** 268 тестов
- **Интеграционные тесты:** 41 тест
  - End-to-end: 9 тестов
  - UI-тесты: 28 тестов (требуют GUI)
  - Performance: 4 теста (2 быстрых + 2 медленных в базовом наборе)
- **Всего:** 309 тестов

### Время выполнения
- Быстрые тесты (без GUI и slow): ~2 секунды (277 тестов)
- Все интеграционные тесты: ~5-10 секунд
- С медленными тестами: ~30-60 секунд

## Конфигурация

### pytest.ini
```ini
[pytest]
markers =
    gui: тесты, требующие GUI (Tkinter)
    slow: медленные тесты (> 1 секунды)
    integration: интеграционные тесты
```

### conftest.py
- Автоматическая установка языка для тестов
- Автоматический пропуск GUI-тестов при недоступности Tkinter
- Регистрация маркеров

## Тестовые данные

Интеграционные тесты используют реальные файлы из директории `Samples/`:
- `Материнка универсальная-RoundHoles.TXT` - Excellon файл с отверстиями
- `Материнка универсальная-SlotHoles.TXT` - Файл со слотами
- `Материнка универсальная_Profile.gbr` - Gerber файл контура платы

## Добавление новых тестов

### Шаблон end-to-end теста
```python
def test_my_workflow(self):
    """Описание теста."""
    # 1. Подготовка данных
    excellon_file = os.path.join(SAMPLES_DIR, "test.drl")
    
    # 2. Выполнение операций
    tools = parse_excellon_file(excellon_file, "4.2")
    gcode, errors = _build_drilling_gcode(tools, excellon_file, params)
    
    # 3. Проверка результатов
    assert errors == []
    assert "M30" in gcode
```

### Шаблон UI-теста
```python
@pytest.mark.gui
def test_my_ui_feature(self):
    """Описание UI-теста."""
    root = tk.Tk()
    try:
        app = ExcellonApp(root)
        # Симуляция действий пользователя
        app.load_file("test.drl")
        # Проверка состояния UI
        assert app.some_state == expected_value
    finally:
        root.destroy()
```

### Шаблон performance-теста
```python
@pytest.mark.slow
def test_my_performance(self):
    """Описание performance-теста."""
    # Генерация больших данных
    large_data = generate_test_data(size=10000)
    
    # Измерение времени
    start = time.time()
    result = process_data(large_data)
    duration = time.time() - start
    
    # Проверка производительности
    assert duration < 5.0, f"Обработка заняла {duration:.2f}с"
```

## CI/CD интеграция

Рекомендуемая конфигурация для CI:

```yaml
# Быстрые тесты (на каждый commit)
- pytest tests/ -v -m "not slow and not gui" --maxfail=5

# Полные тесты (на pull request)
- pytest tests/ -v -m "not gui" --cov=core --cov=ui

# Все тесты (перед релизом)
- pytest tests/ -v --cov=core --cov=ui --cov-report=html
```

## Отладка

### Запуск с подробным выводом
```bash
pytest tests/integration/ -vv -s
```

### Запуск конкретного теста
```bash
pytest tests/integration/test_full_workflow.py::TestExcellonToGCodeWorkflow::test_excellon_to_gcode_basic_workflow -v
```

### Остановка на первой ошибке
```bash
pytest tests/integration/ -v -x
```

### Показать локальные переменные при ошибке
```bash
pytest tests/integration/ -v -l
```

## Лучшие практики

1. **Изоляция тестов** - Каждый тест должен быть независимым
2. **Очистка ресурсов** - Используйте `try/finally` для UI-тестов
3. **Реалистичные данные** - Используйте реальные файлы из `Samples/`
4. **Понятные сообщения** - Добавляйте информативные assert-сообщения
5. **Маркировка** - Правильно маркируйте медленные и GUI-тесты
6. **Документация** - Добавляйте docstring к каждому тесту

## Известные ограничения

1. UI-тесты не работают в headless-окружении (без дисплея)
2. Performance-тесты могут давать разные результаты на разном железе
3. Некоторые тесты зависят от наличия тестовых файлов в `Samples/`

## Поддержка

При возникновении проблем с тестами:
1. Проверьте наличие всех зависимостей: `pip install -r requirements-dev.txt`
2. Убедитесь, что тестовые файлы присутствуют в `Samples/`
3. Для UI-тестов проверьте доступность Tkinter
4. Проверьте логи pytest с флагом `-vv`
