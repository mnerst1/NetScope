"""Create a reproducible source-only archive, excluding runtime and generated files."""
from pathlib import Path
import zipfile


def main():
    root=Path(__file__).resolve().parent
    archive=root.parent/'NetScope-v1.0.0-source.zip'
    excluded={'.venv','venv','__pycache__','.pytest_cache','build','dist','release','.git','.idea'}
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for path in sorted(root.rglob('*')):
            relative=path.relative_to(root)
            if not path.is_file() or any(p in excluded or p.endswith('.egg-info') for p in relative.parts):
                continue
            if path.suffix in ('.pyc','.pyo','.db','.sqlite','.log','.zip') or path.name.endswith(('-wal','-shm')):
                continue
            if path.name.startswith('.env') or path.name=='NetScope-OneFile.spec':
                continue
            z.write(path,Path('NetScope')/relative)
    print(archive)


if __name__=='__main__':
    main()
