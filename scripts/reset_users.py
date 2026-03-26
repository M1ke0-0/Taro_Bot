import asyncio
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.config import settings
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

async def reset_users_table():
    engine = create_async_engine(settings.database_url, echo=False)
    async with engine.begin() as conn:
        print("Dropping users table...")
        await conn.execute(text("DROP TABLE IF EXISTS users CASCADE;"))
        print("Dropped.")
        
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(reset_users_table())
