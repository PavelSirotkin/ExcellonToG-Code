"""
Хелперы для числовых Entry-полей.

Обеспечивают:
  - валидацию ввода (только числа, с поддержкой запятой как разделителя);
  - живую замену запятой на точку прямо в поле ('0,3' -> '0.3').
"""


def numeric_key_validator(value, min_val=None, max_val=None):
    """Валидация числового ввода для Entry-виджетов (validate='key').

    Принимает запятую как разделитель (нормализует ','->'.'). Пустая строка и
    одиночные '-', ',', '.' разрешены как промежуточный ввод.

    Args:
        value: Строка для валидации (значение поля после правки, %P).
        min_val: Минимальное допустимое значение (опционально).
        max_val: Максимальное допустимое значение (опционально).

    Returns:
        True если значение валидно, False иначе.
    """
    # Пустая строка разрешена (пользователь может очищать поле)
    if value == "":
        return True

    # Промежуточный ввод: минус, точка или запятая в начале
    if value in ("-", ".", ","):
        return True

    try:
        num = float(value.replace(",", "."))
        if min_val is not None and num < min_val:
            return False
        if max_val is not None and num > max_val:
            return False
        return True
    except ValueError:
        return False


def normalize_comma_inplace(entry):
    """Если в Entry есть запятая — заменить её на точку, сохранив позицию курсора."""
    try:
        value = entry.get()
    except Exception:
        return
    if "," not in value:
        return
    try:
        pos = entry.index("insert")
        entry.delete(0, "end")
        entry.insert(0, value.replace(",", "."))
        entry.icursor(pos)
    except Exception:
        # readonly / disabled поля или иные ситуации — молча пропускаем
        pass


def attach_numeric_validation(entry, root, min_val=None, max_val=None):
    """Навесить на Entry валидацию числового ввода и живую замену запятой на точку.

    Args:
        entry: Виджет tk.Entry.
        root: Корневое окно (для root.register валидатора).
        min_val: Минимальное допустимое значение (опционально).
        max_val: Максимальное допустимое значение (опционально).
    """
    def _validate(value):
        return numeric_key_validator(value, min_val, max_val)

    validate_cmd = (root.register(_validate), "%P")
    entry.configure(validate="key", validatecommand=validate_cmd)
    entry.bind("<KeyRelease>", lambda e: normalize_comma_inplace(entry), add="+")
