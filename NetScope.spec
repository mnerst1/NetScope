# PyInstaller's official PySide6 hooks collect the platform plugins and Qt runtime.
from pathlib import Path
from PyInstaller.utils.hooks import collect_data_files
root = Path(SPECPATH)
datas = [(str(root/'netscope'/'assets'),'netscope/assets'),
         (str(root/'netscope'/'i18n'/'locales'),'netscope/i18n/locales')]
datas += collect_data_files('PySide6', includes=['Qt/translations/*'])
a = Analysis([str(root/'main.py')], pathex=[str(root)], binaries=[], datas=datas,
             hiddenimports=[], hookspath=[], hooksconfig={}, runtime_hooks=[],
             excludes=['PyQt5','PyQt6','tkinter','PySide6.QtWebEngineWidgets','PySide6.QtWebEngineCore'], noarchive=False)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name='NetScope', debug=False,
          bootloader_ignore_signals=False, strip=False, upx=False, console=False,
          icon=str(root/'netscope'/'assets'/'netscope.ico'))
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name='NetScope')
