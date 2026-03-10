import asyncio
import os
from src.config import settings
import asyncpg

async def patch_db():
    print(f"Connecting to {settings.database_url}")
    # asyncpg expects postgresql:// instead of postgresql+asyncpg://
    dsn = settings.database_url.replace("postgresql+asyncpg://", "postgresql://")
    conn = await asyncpg.connect(dsn)
    try:
        # Add new columns to users table that might be missing
        await conn.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS last_report_date TIMESTAMP WITH TIME ZONE;")
        await conn.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS cached_weekly_report TEXT;")
        await conn.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS total_spreads INTEGER DEFAULT 0;")
        await conn.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS avg_stress_index DOUBLE PRECISION;")
        
        # Ensure suggestions table is created
        print("Database patched successfully.")
    except Exception as e:
        print(f"Error patching db: {e}")
    finally:
        await conn.close()
        
    # Now run sqlalchemy create_all to create the suggestions table if missing
    from sqlalchemy.ext.asyncio import create_async_engine
    from src.db.models import Base
    
    engine = create_async_engine(settings.database_url)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        print("SQLAlchemy tables ensured.")

if __name__ == "__main__":
    asyncio.run(patch_db())
