#!/usr/bin/env python3
"""Generate daily for today: PYTHONPATH=apps/api python scripts/generate_daily.py"""

import asyncio
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "apps" / "api"))

from app.db import AsyncSessionLocal, init_db_schema  # noqa: E402
from app.services.daily_service import generate_daily_for_date  # noqa: E402


async def main() -> None:
    await init_db_schema()
    async with AsyncSessionLocal() as session:
        await generate_daily_for_date(session, date.today())
        print("Daily generated.")


if __name__ == "__main__":
    asyncio.run(main())
