# UI Handlers Module

Модуль содержит обработчики событий пользовательского интерфейса.

## Структура

### `file_handlers.py`
Обработчики событий для работы с файлами.

**Функции:**
- `choose_file()` - выбор файла Excellon с отверстиями
- `choose_slot_file()` - выбор файла со слотами
- `choose_outline_file()` - выбор файла контура платы (Gerber)
- `clear_slots()` - очистка загруженных слотов
- `clear_outline()` - очистка загруженного контура
- `on_format_change(event)` - обработчик изменения формата координат
- `on_show_paths_change()` - обработчик переключения отображения путей

### `gcode_handlers.py`
Обработчики событий для генерации G-code.

**Основные функции генерации:**
- `generate_drilling_gcode()` - генерация G-code для сверления
- `generate_milling_gcode()` - генерация G-code для фрезерования слотов
- `generate_combined_gcode()` - комбинированная генерация (сверление + фрезерование + контур)
- `generate_outline_gcode()` - генерация G-code только для контура

**Вспомогательные функции:**
- `check_missing_tools(tool_type, tools_dict)` - проверка недостающих инструментов в Pro-режиме
- `show_missing_tools_warning(missing_tools)` - предупреждение о недостающих инструментах
- `check_endmill_multipass(tools_dict)` - проверка multi-pass обработки
- `show_multipass_warning(multipass_list)` - предупреждение о multi-pass
- `build_drill_tool_params_dict()` - сборка параметров сверл из базы
- `build_endmill_tool_params_dict()` - сборка параметров фрез из базы
- `save_gcode_params_from_ui()` - сохранение параметров из UI
- `on_param_change(event)` - автосохранение параметров
- `enrich_outline_params_with_tool(outline_params, global_params)` - обогащение параметров контура

## Использование

```python
from ui.handlers.file_handlers import choose_file, clear_slots
from ui.handlers.gcode_handlers import generate_drilling_gcode, on_param_change

# Использование обработчиков
button = tk.Button(parent, command=choose_file)
entry.bind("<FocusOut>", on_param_change)
```

## Архитектура

### Разделение ответственности

1. **file_handlers.py** - работа с файлами (загрузка, очистка)
2. **gcode_handlers.py** - генерация G-code и валидация

### Dependency Injection

Обработчики получают контекст приложения через `get_app_context()`:
```python
def get_app_context():
    from ui.app import get_app_context as _get_app_context
    return _get_app_context()
```

### Блокировка кнопок

Все функции генерации G-code блокируют кнопки на время выполнения:
```python
gcode_frame_buttons = [
    cfg.widgets.get("btn_gen_drill"),
    cfg.widgets.get("btn_gen_mill"),
    cfg.widgets.get("btn_gen_outline"),
    cfg.widgets.get("btn_gen_combined")
]
for btn in gcode_frame_buttons:
    if btn:
        btn.config(state="disabled")

try:
    # Генерация G-code
    ...
finally:
    # Разблокировка кнопок
    for btn in gcode_frame_buttons:
        if btn:
            btn.config(state="normal")
```

## Преимущества модульной структуры

1. **Изоляция логики** - бизнес-логика отделена от UI
2. **Тестируемость** - обработчики можно тестировать независимо
3. **Переиспользование** - обработчики можно вызывать из разных мест
4. **Читаемость** - код организован по функциональности
