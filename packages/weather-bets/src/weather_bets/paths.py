from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[4]
DEFAULT_DATA_DIR = REPO_ROOT / ".bets"
DEFAULT_DB_PATH = DEFAULT_DATA_DIR / "bets.db"
