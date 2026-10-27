"""Vercel serverless entrypoint for FastAPI application."""

import sys
from pathlib import Path

# Add backend directory to sys.path so app modules are resolvable
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR / "backend"))

from app.main import app  # noqa: E402

__all__ = ["app"]
