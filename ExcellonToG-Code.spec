# -*- mode: python ; coding: utf-8 -*-

# datas:
#   i18n/strings_*.json — JSON со строками локализации; читается из
#   sys._MEIPASS/i18n/ через core/i18n.py:34. Других runtime-data-файлов
#   нет: docs/*.md — только для разработчиков, icon.ico — embedded в
#   EXE-bootloader, app_settings.json/gcode_params.json/tool_base.json —
#   пользовательский state, создаётся рядом с exe и НЕ должен бандлиться.
#
# hiddenimports:
#   docs.help_content_{en,ru} — импортируются ленИво внутри
#   docs/help_content.py:_get_sections() в зависимости от языка. Текущая
#   версия PyInstaller (modulegraph) подхватывает их статически по AST,
#   но добавляем явно как страховку от будущих изменений или флага
#   --exclude-module. Без них переключение языка справки в собранном
#   .exe могло бы падать с ImportError.

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
    name='ExcellonToG-Code',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
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
