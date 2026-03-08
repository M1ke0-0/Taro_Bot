import asyncio
from datetime import datetime, timezone

from src.db.base import create_session_maker
from src.db.user_dao import UserDAO

async def main():
    session_maker = await create_session_maker()
    async with session_maker() as session:
        dao = UserDAO(session)
        user = await dao.get_by_telegram_id(1199681092)
        print("Last report date:", user.last_report_date, user.last_report_date.tzinfo if user.last_report_date else None)
        
        now = datetime.now(timezone.utc)
        print("Now:", now, now.tzinfo)
        
        if user.last_report_date:
            diff_days = (now.astimezone() - user.last_report_date).days if user.last_report_date.tzinfo else (now.replace(tzinfo=None) - user.last_report_date).days
            print("Diff days:", diff_days)

if __name__ == "__main__":
    asyncio.run(main())
