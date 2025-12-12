import shutil
from pathlib import Path
from typing import Iterable


class StorageManager:
    def ensure_dir(self, path: Path) -> Path:
        path.mkdir(parents=True, exist_ok=True)
        return path

    def cleanup(self, paths: Iterable[str]):
        for path in paths:
            if not path:
                continue
            p = Path(path)
            try:
                if p.is_dir():
                    shutil.rmtree(p, ignore_errors=True)
                elif p.exists():
                    p.unlink()
            except Exception:
                pass


storage_manager = StorageManager()
