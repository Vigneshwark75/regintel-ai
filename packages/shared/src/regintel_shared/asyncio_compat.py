import asyncio
import sys


def ensure_windows_selector_event_loop() -> None:
    """psycopg's async mode cannot run on asyncio's default ProactorEventLoop on
    Windows. Must be called before any event loop is created (e.g. before
    asyncio.run() or uvicorn.run()) whenever async Postgres access is involved.
    """
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
