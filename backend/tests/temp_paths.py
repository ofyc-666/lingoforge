from __future__ import annotations

import tempfile
import uuid
from pathlib import Path


def temp_db_path(name: str) -> Path:
    directory = Path(tempfile.gettempdir()) / "lingoforge_tests"
    directory.mkdir(parents=True, exist_ok=True)
    return directory / f"{name}_{uuid.uuid4().hex}.sqlite3"

