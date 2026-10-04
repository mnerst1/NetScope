import os
from pathlib import Path


def data_dir(demo=False):
    root = Path(os.environ.get("LOCALAPPDATA", str(Path.home() / ".local" / "share"))) / "NetScope"
    path = root / ("demo" if demo else "live")
    path.mkdir(parents=True, exist_ok=True)
    return path


def asset(name):
    return Path(__file__).resolve().parents[1] / "assets" / name
