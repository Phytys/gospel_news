#!/usr/bin/env python3
"""PYTHONPATH=apps/api python scripts/rebuild_umap.py"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "apps" / "api"))

from app.services.umap_rebuild import run_rebuild_umap  # noqa: E402

if __name__ == "__main__":
    n = asyncio.run(run_rebuild_umap())
    print(f"Wrote {n} map points.")
