# UI Panels Module

Модуль содержит компоненты панелей пользовательского интерфейса.

## Структура

### `files_panel.py`
Панель работы с файлами (Excellon, слоты, контур Gerber).

**Функции:**
- `create_files_panel(parent, localize_widget, handlers)` - создание панели с кнопками загрузки файлов

**Компоненты:**
- Кнопка открытия Excellon файла
- Кнопка открытия файла слотов
- Кнопка открытия контура (Gerber)
- Кнопки очистки слотов и контура
- Выбор формата координат

### `params_panel.py`
Панели параметров G-code и обрезки по контуру.

**Функции:**
- `create_gcode_params_panel(parent, root, localize_widget, validate_numeric_entry, on_param_change)` - параметры G-code
- `create_outline_params_panel(parent, root, localize_widget, validate_numeric_entry, on_param_change)` - параметры контура

**Параметры G-code:**
- Safe Z, Drill Z, Feed Rate, Mill Feed, Rapid Rate, Park Z

**Параметры контура:**
- Диаметр инструмента, глубина прохода, количество перемычек, ширина/высота перемычек, направление

### `gcode_panel.py`
Панели генерации G-code и отображения.

**Функции:**
- `create_gcode_panel(parent, localize_widget, handlers)` - кнопки генерации G-code
- `create_display_panel(parent, localize_widget, on_show_paths_change)` - настройки отображения

**Компоненты:**
- Кнопки генерации: сверление, фрезерование, контур, комбинированный
- Чекбокс отображения путей

### `options_panel.py`
Панель опций (режим работы, инструменты, визуализация).

**Функции:**
- `create_options_panel(parent, context, localize_widget, handlers)` - создание панели опций

**Компоненты:**
- Переключатель режимов Simple/Pro
- Кнопка базы инструментов
- Кнопка визуализации
- Кнопки статистики и справки

## Использование

```python
from ui.panels.files_panel import create_files_panel
from ui.panels.params_panel import create_gcode_params_panel
from ui.panels.gcode_panel import create_gcode_panel
from ui.panels.options_panel import create_options_panel

# Создание панелей
create_files_panel(parent, localize_widget, file_handlers)
create_gcode_params_panel(parent, root, localize_widget, validate_func, on_change)
create_gcode_panel(parent, localize_widget, gcode_handlers)
create_options_panel(parent, context, localize_widget, option_handlers)
```

## Преимущества модульной структуры

1. **Читаемость** - каждая панель в отдельном файле
2. **Поддерживаемость** - легко найти и изменить нужную панель
3. **Тестируемость** - панели можно тестировать независимо
4. **Переиспользование** - панели можно использовать в других проектах
