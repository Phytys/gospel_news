from __future__ import annotations

import asyncio
from ..db import init_db_schema


async def main() -> None:
    await init_db_schema()
    print("DB schema initialized.")


if __name__ == "__main__":
    asyncio.run(main())
