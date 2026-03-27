#!/usr/bin/env python3
"""Run from repo root: PYTHONPATH=apps/api python scripts/ingest_all.py"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "apps" / "api"))

from app.ingest_pipeline import main  # noqa: E402

if __name__ == "__main__":
    asyncio.run(main())
