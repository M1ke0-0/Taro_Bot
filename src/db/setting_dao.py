from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from src.db.models import Setting

class SettingDAO:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_setting(self, key: str, default: str = None) -> str | None:
        stmt = select(Setting).where(Setting.key == key)
        result = await self.session.execute(stmt)
        setting = result.scalar_one_or_none()
        if setting:
            return setting.value
        return default

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
