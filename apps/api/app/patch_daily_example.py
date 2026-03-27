"""
Rewrite AI text fields for the example daily (2026-03-26) so plain/deeper stay tradition-specific.

Run in API container:
  python -m app.patch_daily_example
"""

from __future__ import annotations

import argparse
import asyncio
from datetime import date

from sqlalchemy import select

from .db import AsyncSessionLocal
from .models import DailyEntry

DEFAULT_DATE = date(2026, 3, 26)

# Same theme, sources, and reflection questions as before; plain/deeper/interpretation separated correctly.
PATCH = {
    "daily_rationale_text": (
        "Desire drives us toward fulfillment, but its direction determines transformation or stagnation."
    ),
    "plain_reading_text": (
        "In Gethsemane, desire is named plainly: Jesus asks that the cup pass, yet places his own wish "
        "under the Father's will. The disciples' sleep and his return to prayer show longing stretched thin—"
        "spirit willing, flesh weak—with no neat resolution in the scene itself."
    ),
    "deeper_reading_text": (
        "This Thomas saying treats desire as seeking that does not stop until something is found; what is "
        "found may disturb before it opens into wonder and breadth. It imagines longing as a path that "
        "unsettles first, then widens—without leaning on any other text."
    ),
    "why_matched_text": (
        "Selections evoke desire through yielded will in prayer and through imperative seeking that refuses "
        "to stop—human impulse tied to spiritual movement."
    ),
    "interpretation_text": (
        "This pairing juxtaposes the struggle to align personal longing with greater purpose against the "
        "call to pursue truth relentlessly, revealing desire as a pathway to awe and authority."
    ),
    "tension_text": None,
    "reflection_questions": [
        "What desires pull you most strongly today?",
        "How might yielding personal wants foster deeper alignment?",
        "What would unrelenting pursuit of truth disturb in your life?",
    ],
}


async def run_patch(target: date) -> None:
    async with AsyncSessionLocal() as session:
        res = await session.execute(select(DailyEntry).where(DailyEntry.entry_date == target))
        row = res.scalars().first()
        if row is None:
            raise SystemExit(f"No daily entry for {target}")
        if target != DEFAULT_DATE:
            raise SystemExit(
                f"This patch only contains copy for {DEFAULT_DATE.isoformat()}. "
                "Edit PATCH in patch_daily_example.py or use admin/API for other dates."
            )
        for key, val in PATCH.items():
            setattr(row, key, val)
        await session.commit()
        print(f"Updated daily_fields for {target}")


def main() -> None:
    p = argparse.ArgumentParser(description="Patch stored daily AI text fields.")
    p.add_argument(
        "--date",
        type=lambda s: date.fromisoformat(s),
        default=DEFAULT_DATE,
        help=f"ISO date (default {DEFAULT_DATE.isoformat()})",
    )
    args = p.parse_args()
    asyncio.run(run_patch(args.date))


if __name__ == "__main__":
    main()
