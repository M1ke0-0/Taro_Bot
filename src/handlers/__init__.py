from aiogram import Dispatcher

from .start import router as registration_router


def setup_routers(dp: Dispatcher) -> None:
    dp.include_router(registration_router)
