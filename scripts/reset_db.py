"""Root-level database reset entrypoint.

Keeps the command `python scripts\reset_db.py` working while the actual
implementation lives under `backend/scripts`.
"""

from __future__ import annotations

import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1] / "backend"
sys.path.insert(0, str(BACKEND_ROOT))

from app.config import load_settings  # noqa: E402
from app.database import reset_database  # noqa: E402


def main() -> None:
    settings = load_settings()
    reset_database(settings.database_path)
    print(f"SQLite database reset: {settings.database_path}")


if __name__ == "__main__":
    main()
