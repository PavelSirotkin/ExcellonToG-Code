"""
Диспатчер контента справки.
Возвращает HELP_SECTIONS на текущем языке (через core.i18n).
"""
from core.i18n import get_language


def _get_sections():
    """Получить словарь разделов справки для текущего языка."""
    lang = get_language()
    if lang == "en":
        from docs.help_content_en import HELP_SECTIONS as _en
        return _en
    from docs.help_content_ru import HELP_SECTIONS as _ru
    return _ru


class _HelpSectionsProxy:
    """Прокси к словарю — каждый запрос идёт в актуальный язык."""

    def __getitem__(self, key):
        return _get_sections()[key]

    def __contains__(self, key):
        return key in _get_sections()

    def items(self):
        return _get_sections().items()

    def keys(self):
        return _get_sections().keys()

    def values(self):
        return _get_sections().values()

    def get(self, key, default=None):
        return _get_sections().get(key, default)


HELP_SECTIONS = _HelpSectionsProxy()
