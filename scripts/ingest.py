#!/usr/bin/env python3
"""Proxy script to run backend/scripts/ingest.py from repository root."""

import os
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
BACKEND_DIR = ROOT_DIR / "backend"
VENV_PYTHON = BACKEND_DIR / ".venv" / "bin" / "python"

# Re-exec with virtualenv python if available and not already in virtualenv
if VENV_PYTHON.exists() and Path(sys.executable).resolve() != VENV_PYTHON.resolve():
    try:
        import httpx  # noqa: F401
    except ImportError:
        os.execv(str(VENV_PYTHON), [str(VENV_PYTHON)] + sys.argv)

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from scripts.ingest import main  # noqa: E402

if __name__ == "__main__":
    main()
