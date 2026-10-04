import subprocess
import sys
from pathlib import Path


def set_autostart(enabled):
    import winreg
    # HKCU only, explicit setting, visible registry Run entry; no scheduled task or elevation.
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER,r'Software\Microsoft\Windows\CurrentVersion\Run') as key:
        if enabled:
            source_python=Path(sys.executable).with_name('pythonw.exe')
            args=[sys.executable] if getattr(sys,'frozen',False) else [str(source_python if source_python.exists() else Path(sys.executable)),str(Path(__file__).resolve().parents[2]/'main.py')]
            winreg.SetValueEx(key,'NetScope',0,winreg.REG_SZ,subprocess.list2cmdline(args))
        else:
            try:
                winreg.DeleteValue(key,'NetScope')
            except FileNotFoundError:
                pass
