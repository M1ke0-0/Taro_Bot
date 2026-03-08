from aiogram import Dispatcher

from .spread import router as spread_router
from .start import router as registration_router
from .profile import router as profile_router
from .pro import router as pro_router
from .about import router as about_router
from .settings import router as settings_router
from .reports import router as reports_router
from .admin import router as admin_router # Added admin import

def setup_routers(dp: Dispatcher) -> None:
    dp.include_router(registration_router)
    dp.include_router(spread_router)
    dp.include_router(profile_router)
    dp.include_router(pro_router)
    dp.include_router(about_router)
    dp.include_router(settings_router)
    dp.include_router(reports_router)
    dp.include_router(admin_router) # Added admin router inclusion
