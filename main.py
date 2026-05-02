"""
Excellon To G-code — точка входа.
Конвертация Excellon-файлов в G-code с визуализацией.
"""
import logging
import os

# Корневой логгер настраиваем до любых импортов, которые могут писать в лог.
# EXCELLON_DEBUG=1 переключает на DEBUG; иначе INFO.
# EXCELLON_LOG_ENABLE=1 включает логирование в консоль.
# EXCELLON_LOG_FILE_ENABLE=1 включает запись в файл excellon2gcode.log.
_log_level = logging.DEBUG if os.environ.get("EXCELLON_DEBUG") else logging.INFO

# Формируем список обработчиков
_handlers = []

# Добавляем файловый обработчик, если явно включен
if os.environ.get("EXCELLON_LOG_FILE_ENABLE"):
    _handlers.append(logging.FileHandler("excellon2gcode.log", encoding="utf-8"))

# Добавляем консольный обработчик, если явно включен
if os.environ.get("EXCELLON_LOG_ENABLE"):
    _handlers.append(logging.StreamHandler())

# Если хотя бы один обработчик включен, настраиваем логирование
if _handlers:
    logging.basicConfig(
        level=_log_level,
        format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
        handlers=_handlers,
    )
else:
    # Если ни один обработчик не включен, отключаем логирование
    logging.basicConfig(level=logging.CRITICAL + 1)

from ui.app import create_app


def main():
    """Запуск приложения."""
    root = create_app()
    root.mainloop()


if __name__ == "__main__":
    main()
