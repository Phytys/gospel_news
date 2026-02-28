from __future__ import annotations

import asyncio
from datetime import date

from ..db import AsyncSessionLocal, init_db_schema
from ..digest import generate_daily_digest


async def main() -> None:
    await init_db_schema()
    async with AsyncSessionLocal() as session:
        digest = await generate_daily_digest(session, digest_date=date.today())
        print(f"Digest for {digest.digest_date} has {len(digest.entries)} entries.")


if __name__ == "__main__":
    asyncio.run(main())
