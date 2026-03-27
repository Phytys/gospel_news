"""Scheduled daily generation for Gospel Resonance."""

from __future__ import annotations

import asyncio
from datetime import date
from zoneinfo import ZoneInfo

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.db import AsyncSessionLocal, init_db_schema
from app.services.daily_service import generate_daily_for_date
from app.settings import settings


async def run_daily() -> None:
    await init_db_schema()
    async with AsyncSessionLocal() as session:
        today = date.today()
        try:
            await generate_daily_for_date(session, today)
            print(f"[worker] Daily generated for {today}")
        except ValueError as e:
            print(f"[worker] Skip: {e}")
        except Exception as e:
            print(f"[worker] Error: {e}")


async def main() -> None:
    await init_db_schema()
    parts = (settings.digest_time_utc or "06:00").split(":")
    hour, minute = int(parts[0]), int(parts[1]) if len(parts) > 1 else 0
    scheduler = AsyncIOScheduler(timezone=ZoneInfo("UTC"))
    scheduler.add_job(
        run_daily,
        CronTrigger(hour=hour, minute=minute, timezone=ZoneInfo("UTC")),
        id="daily",
        max_instances=1,
        coalesce=True,
    )
    scheduler.start()
    print(f"[worker] Daily job at {hour:02d}:{minute:02d} UTC")
    if settings.run_daily_on_startup:
        await run_daily()
    # Keep process alive so APScheduler can fire the cron job.
    await asyncio.Event().wait()


if __name__ == "__main__":
    asyncio.run(main())
