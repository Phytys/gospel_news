from __future__ import annotations

import asyncio
from datetime import datetime
from zoneinfo import ZoneInfo

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from .db import init_db_schema, AsyncSessionLocal
from .digest import generate_daily_digest
from .settings import settings

SGT = ZoneInfo("Asia/Singapore")


def _parse_hhmm(s: str) -> tuple[int, int]:
    s = (s or "").strip()
    if not s or ":" not in s:
        return 6, 30
    hh, mm = s.split(":", 1)
    return int(hh), int(mm)


async def run_once() -> None:
    await init_db_schema()
    async with AsyncSessionLocal() as session:
        digest_date = datetime.now(SGT).date()
        digest = await generate_daily_digest(session, digest_date=digest_date)
        print(f"[worker] Generated digest for {digest.digest_date} with {len(digest.entries)} entries.")


async def main() -> None:
    await init_db_schema()

    hour, minute = _parse_hhmm(settings.digest_time_sgt)
    scheduler = AsyncIOScheduler(timezone=SGT)
    scheduler.add_job(
        run_once,
        CronTrigger(hour=hour, minute=minute, timezone=SGT),
        id="daily_digest",
        max_instances=1,
        coalesce=True,
        misfire_grace_time=60 * 60,
    )
    scheduler.start()

    print(f"[worker] Scheduled daily digest at {hour:02d}:{minute:02d} Asia/Singapore")

    if settings.run_digest_on_startup:
        try:
            await run_once()
        except Exception as e:
            print(f"[worker] Startup digest failed: {e}")

    # Keep running forever
    while True:
        await asyncio.sleep(3600)


if __name__ == "__main__":
    asyncio.run(main())
