from aiogram import Dispatcher

from .start import router as registration_router
from .profile import router as profile_router


def setup_routers(dp: Dispatcher) -> None:
    dp.include_router(registration_router)
    dp.include_router(profile_router)
