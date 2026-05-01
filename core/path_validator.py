"""
Валидатор путей для предотвращения Path Traversal атак.
"""
import os
import logging

logger = logging.getLogger(__name__)


def validate_save_path(filename: str, allowed_base_dirs: list = None) -> tuple[bool, str]:
    """
    Проверить безопасность пути для сохранения файла.
    
    Args:
        filename: Путь к файлу для сохранения
        allowed_base_dirs: Список разрешённых базовых директорий (опционально)
                          Если None, проверяется только на подозрительные паттерны
    
    Returns:
        tuple: (is_valid: bool, error_message: str)
               is_valid=True если путь безопасен, False если обнаружена угроза
               error_message содержит описание проблемы при is_valid=False
    """
    if not filename:
        return True, ""
    
    try:
        # Проверка на подозрительные паттерны в исходном пути (до нормализации)
        suspicious_patterns = ['..', '~', '$', '%']
        # Нормализуем разделители для проверки
        normalized_filename = filename.replace('/', os.sep).replace('\\', os.sep)
        path_parts = normalized_filename.split(os.sep)
        
        for part in path_parts:
            for pattern in suspicious_patterns:
                if pattern in part:
                    msg = f"Suspicious pattern '{pattern}' detected in path"
                    logger.warning(f"Path validation failed: {msg} - {filename}")
                    return False, msg
        
        # Получить абсолютный путь
        abs_path = os.path.abspath(filename)
        
        # Если указаны разрешённые директории, проверить что путь находится внутри них
        if allowed_base_dirs:
            is_allowed = False
            for base_dir in allowed_base_dirs:
                try:
                    abs_base = os.path.abspath(base_dir)
                    # Проверить что путь начинается с разрешённой директории
                    if abs_path.startswith(abs_base + os.sep) or abs_path == abs_base:
                        is_allowed = True
                        break
                except Exception as e:
                    logger.warning(f"Failed to validate base directory {base_dir}: {e}")
                    continue
            
            if not is_allowed:
                msg = "Path is outside allowed directories"
                logger.warning(f"Path validation failed: {msg} - {abs_path}")
                return False, msg
        
        # Проверка что родительская директория существует или может быть создана
        parent_dir = os.path.dirname(abs_path)
        if parent_dir and not os.path.exists(parent_dir):
            try:
                # Попытка создать директорию для проверки прав
                os.makedirs(parent_dir, exist_ok=True)
            except (OSError, PermissionError) as e:
                msg = f"Cannot create directory: {str(e)}"
                logger.warning(f"Path validation failed: {msg} - {parent_dir}")
                return False, msg
        
        logger.debug(f"Path validation passed: {abs_path}")
        return True, ""
        
    except Exception as e:
        msg = f"Path validation error: {str(e)}"
        logger.error(msg)
        return False, msg


def get_safe_filename(filename: str) -> str:
    """
    Получить безопасное имя файла, удалив подозрительные символы.
    
    Args:
        filename: Исходное имя файла
    
    Returns:
        str: Безопасное имя файла
    """
    if not filename:
        return filename
    
    # Удалить потенциально опасные символы из имени файла
    # Важно: '..' заменяется на '__' (два символа на два символа)
    dangerous_chars = {
        '..': '__',
        '~': '_',
        '$': '_',
        '%': '_',
        '|': '_',
        '&': '_',
        ';': '_',
        '`': '_'
    }
    safe_name = filename
    
    for char, replacement in dangerous_chars.items():
        safe_name = safe_name.replace(char, replacement)
    
    return safe_name
