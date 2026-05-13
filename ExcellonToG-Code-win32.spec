# -*- mode: python ; coding: utf-8 -*-
#
# Spec для сборки 32-битного .exe под Windows 7.
#
# КАК СОБИРАТЬ:
#   1. Установите 32-битный Python 3.8 (Win7 не поддерживается версиями ≥3.9).
#   2. pip install pyinstaller
#   3. pyinstaller ExcellonToG-Code-win32.spec --clean
#   Результат: dist\ExcellonToG-Code.exe (32-битный, ~12–15 MB).
#
# ЧЕМ ОТЛИЧАЕТСЯ ОТ ОБЫЧНОГО ExcellonToG-Code.spec:
#
#   1. workpath переопределяется на %TEMP%\pyi_excellon_win32_build —
#      обход бага PyInstaller с pathlib.Path.resolve() на нестандартных
#      дисках (subst, сетевые маппинги Z:/Y:/..., VirtualBox shared
#      folders, WebDAV). На таких дисках WinAPI GetFinalPathNameByHandle
#      возвращает ERROR_INVALID_FUNCTION (WinError 1), и сборка падает
#      на стадии PKG. Перенос промежуточных артефактов в локальный TEMP
#      гарантирует, что resolve() будет работать.
#      Финальный .exe всё равно попадает в ./dist/ (как и обычно).
#
#   2. upx=False. UPX на 32-битной Windows регулярно ломает упакованные
#      DLL Tcl/Tk (tk86t.dll, tcl86t.dll), приводя к падению .exe на
#      старте с «не является приложением Win32» или «procedure entry
#      point not found». Распакованный .exe чуть больше (~+5 MB), зато
#      гарантированно запускается на чистой Win7 без зависимостей.
#
# Прочие настройки (datas, hiddenimports, icon) совпадают с основным spec.

import os
import tempfile
from PyInstaller.config import CONF

# Переопределяем рабочую директорию ДО создания Analysis/EXE. CONF
# доступен внутри spec'а и читается PyInstaller'ом для всех последующих
# операций.
_safe_workpath = os.path.join(tempfile.gettempdir(), 'pyi_excellon_win32_build')
os.makedirs(_safe_workpath, exist_ok=True)
CONF['workpath'] = _safe_workpath


a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[('i18n', 'i18n')],
    hiddenimports=[
        'docs.help_content_en',
        'docs.help_content_ru',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='ExcellonToG-Code-win32',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['icon.ico'],
)
