# Руководство по использованию системы локализации (i18n)

## Обзор

Система локализации в проекте ExcellonToG-Code обеспечивает поддержку нескольких языков (русский и английский). Она состоит из следующих компонентов:

- `core/i18n.py` - основной модуль локализации
- `i18n/strings_ru.json` - словарь русских строк
- `i18n/strings_en.json` - словарь английских строк
- `docs/help_content.py` - прокси для динамической загрузки справки на текущем языке

## Основное использование

```python
from core.i18n import t, set_language, get_language

# Установка языка (обычно делается один раз при запуске приложения)
set_language("ru")  # или "en"

# Получение переведенной строки
label_text = t("app.btn.open_excellon")

# Перевод с параметрами
message = t("app.lbl.holes_file", filename="test.drl")
```

## Race Condition в docs/help_content.py

### Проблема

`docs/help_content.py` содержит прокси-объект `HELP_SECTIONS`, который при каждом обращении вызывает `get_language()` для определения, какой модуль справки загрузить (`help_content_ru` или `help_content_en`).

**При очень раннем импорте** (например, в тесте, который импортирует `docs.help_content` до вызова `set_language()`), может быть загружен неправильный язык:

```python
# НЕПРАВИЛЬНО - race condition!
from docs.help_content import HELP_SECTIONS  # Язык еще не установлен!
from core.i18n import set_language

set_language("en")  # Слишком поздно - HELP_SECTIONS уже мог закешировать RU
```

### Решение

**Всегда вызывайте `set_language()` ДО импорта модулей, использующих систему локализации:**

```python
# ПРАВИЛЬНО
from core.i18n import set_language

set_language("en")  # Устанавливаем язык ПЕРВЫМ
from docs.help_content import HELP_SECTIONS  # Теперь безопасно
```

### В тестах

Для тестов создан файл `tests/conftest.py`, который автоматически устанавливает язык перед запуском всех тестов:

```python
# tests/conftest.py
from core.i18n import set_language
set_language("ru")  # Дефолтный язык для тестов
```

Этот файл выполняется pytest автоматически, поэтому в большинстве тестов дополнительная инициализация не требуется.

**Если тест требует конкретного языка:**

```python
def test_english_help():
    from core.i18n import set_language
    set_language("en")
    
    # Теперь можно безопасно импортировать
    from docs.help_content import HELP_SECTIONS
    
    # Тест...
```

### В production коде

В `ui/app.py` язык устанавливается в функции `create_app()` до создания любых UI-компонентов:

```python
def create_app():
    # Загрузка настроек и установка языка ДО создания виджетов
    settings.load()
    set_language(settings.get("language", "ru"))
    
    # Теперь безопасно создавать UI
    root = tk.Tk()
    # ...
```

## Severity

- **Критическая в теории**: Может привести к отображению справки на неправильном языке
- **Низкая на практике**: В нормальном workflow `set_language()` вызывается до открытия окна справки
- **Средняя в тестировании**: Без `conftest.py` тесты могут получить неожиданный язык

## Best Practices

1. **Всегда устанавливайте язык как можно раньше** - в начале `main()` или `create_app()`
2. **В тестах используйте conftest.py** - он автоматически инициализирует язык
3. **Не импортируйте `docs.help_content` на уровне модуля** - делайте это внутри функций, после установки языка
4. **Используйте `register_listener()`** для обновления UI при смене языка

## Примеры

### Правильно: Ленивый импорт

```python
def show_help():
    from core.i18n import get_language
    from docs.help_content import HELP_SECTIONS
    
    # Язык уже установлен в create_app()
    sections = HELP_SECTIONS
    # ...
```

### Неправильно: Импорт на уровне модуля

```python
# ИЗБЕГАЙТЕ ЭТОГО!
from docs.help_content import HELP_SECTIONS  # Может быть выполнено до set_language()

def show_help():
    sections = HELP_SECTIONS  # Может быть на неправильном языке
    # ...
```

### Правильно: Тест с явной установкой языка

```python
def test_help_content_english():
    from core.i18n import set_language
    
    # Явно устанавливаем нужный язык
    set_language("en")
    
    # Импортируем после установки языка
    from docs.help_content import HELP_SECTIONS
    
    assert "Overview" in HELP_SECTIONS["intro"]["content"]
```

## Заключение

Система локализации работает надежно при соблюдении простого правила: **устанавливайте язык до импорта модулей, использующих локализацию**. Файл `tests/conftest.py` автоматически решает эту проблему для всех тестов.
