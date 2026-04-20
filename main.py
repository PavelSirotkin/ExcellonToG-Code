"""
Excellon To G-code — точка входа.
Конвертация Excellon-файлов в G-code с визуализацией.
"""
from ui.app import create_app


def main():
    """Запуск приложения."""
    root = create_app()
    root.mainloop()


if __name__ == "__main__":
    main()
