"""
Валидатор путей для предотвращения Path Traversal атак.
"""
import os
import logging
from typing import Tuple

logger = logging.getLogger(__name__)


def validate_save_path(filename: str, allowed_base_dirs: list = None) -> Tuple[bool, str]:
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
        # Защита от path traversal: единственный реальный вектор — компонент пути,
        # ТОЧНО равный "..", позволяющий подняться на уровень. Любые другие
        # вхождения "..", а также символы '~', '$', '%' — НЕ являются угрозой
        # для filesystem-операций save (Python не раскрывает их сам), но раньше
        # отвергались общим substring-фильтром, что блокировало легитимные пути:
        #   - 8.3 short names на Windows (PROGRA~1, PavelS~1, …)
        #   - системные папки ($Recycle.Bin, доступ через C$ share)
        #   - имена с переменными окружения, передаваемыми буквально (%TEMP%
        #     в строке — Python не expand-ит, это просто подстрока в имени)
        #   - имена файлов с двойными точками между версиями (build_2..3.tap)
        # Дополнительная защита от выхода за разрешённые директории
        # реализована ниже через allowed_base_dirs.
        normalized_filename = filename.replace('/', os.sep).replace('\\', os.sep)
        path_parts = normalized_filename.split(os.sep)

        for part in path_parts:
            if part == '..':
                msg = "Suspicious pattern '..' detected in path"
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
        
        # H3: валидация — чистая функция без побочных эффектов.
        # Родительская директория должна СУЩЕСТВОВАТЬ и быть доступной для записи.
        # Создание директорий вынесено в код сохранения — пусть это делает
        # вызывающий уже после явного подтверждения пользователем (а в текущем
        # UI это не требуется: filedialog.asksaveasfilename гарантирует, что
        # родитель существует).
        parent_dir = os.path.dirname(abs_path)
        if parent_dir:
            if not os.path.exists(parent_dir):
                msg = f"Parent directory does not exist: {parent_dir}"
                logger.warning(f"Path validation failed: {msg}")
                return False, msg
            if not os.access(parent_dir, os.W_OK):
                msg = f"Parent directory is not writable: {parent_dir}"
                logger.warning(f"Path validation failed: {msg}")
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
