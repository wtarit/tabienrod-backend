#!/usr/bin/env python3
"""Standalone cron job runner. Execute via system cron or manually.

Usage:
    uv run python scripts/run_cron.py

Crontab example (every minute):
    * * * * * cd /path/to/tabienrod-backend && uv run python scripts/run_cron.py
"""
import asyncio

from app.config import settings
from app.database import async_session, engine
from app.cron import run_cron_job


async def main():
    async with async_session() as session:
        await run_cron_job(session, settings)
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
