"""
Обработчики событий для работы с файлами.
"""
import logging
from tkinter import filedialog
from ui import themed_messagebox as messagebox
from core.i18n import t
import core.config as cfg

logger = logging.getLogger(__name__)


def choose_file():
    """Выбор файла Excellon с отверстиями."""
    from ui.widgets import choose_file as _choose_file
    _choose_file()


def choose_slot_file():
    """Выбор файла со слотами."""
    from ui.widgets import choose_slot_file as _choose_slot_file
    _choose_slot_file()


def choose_outline_file():
    """Выбор файла контура платы (Gerber)."""
    from ui.widgets import choose_outline_file as _choose_outline_file
    _choose_outline_file()


def clear_slots():
    """Очистка загруженных слотов."""
    from ui.widgets import clear_slots as _clear_slots
    _clear_slots()


def clear_outline():
    """Очистка загруженного контура."""
    from ui.widgets import clear_outline as _clear_outline
    _clear_outline()


def on_format_change(event):
    """Обработчик изменения формата координат."""
    from ui.widgets import on_format_change as _on_format_change
    _on_format_change(event)


def on_show_paths_change():
    """Обработчик переключения отображения путей."""
    from ui.widgets import on_show_paths_change as _on_show_paths_change
    _on_show_paths_change()
