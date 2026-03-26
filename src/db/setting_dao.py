from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from src.db.models import Setting
from src.db.redis import redis_client

class SettingDAO:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_setting(self, key: str, default: str = None) -> str | None:
        if redis_client:
            cached_val = await redis_client.get(f"setting:{key}")
            if cached_val is not None:
                return cached_val

        stmt = select(Setting).where(Setting.key == key)
        result = await self.session.execute(stmt)
        setting = result.scalar_one_or_none()
        
        val = setting.value if setting else default
        
        # cache the result for 15 minutes (900 seconds) if redis is available
        if redis_client and val is not None:
            await redis_client.set(f"setting:{key}", val, ex=900)
            
        return val

    async def set_setting(self, key: str, value: str, description: str = None) -> Setting:
        stmt = select(Setting).where(Setting.key == key)
        result = await self.session.execute(stmt)
        setting = result.scalar_one_or_none()
        
        if setting:
            setting.value = str(value)
            if description is not None:
                setting.description = description
        else:
            setting = Setting(key=key, value=str(value), description=description)
            self.session.add(setting)
            
        await self.session.commit()
        
        if redis_client:
            await redis_client.set(f"setting:{key}", str(value), ex=900)
            
        return setting

    async def init_defaults(self):
        defaults = {
            "free_spread_limit": ("1", "Лимит бесплатных раскладов в день"),
            "pro_sub_price": ("500", "Цена PRO подписки в рублях"),
            "single_spread_price": ("100", "Цена разового расклада в рублях")
        }
        for key, (val, desc) in defaults.items():
            stmt = select(Setting).where(Setting.key == key)
            result = await self.session.execute(stmt)
            if not result.scalar_one_or_none():
                self.session.add(Setting(key=key, value=val, description=desc))
        await self.session.commit()
