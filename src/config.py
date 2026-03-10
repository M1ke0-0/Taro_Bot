import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass
class Settings:
    BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
    @property
    def ADMIN_IDS(self) -> list[int]:
        ids_str = os.getenv("ADMIN_IDS", os.getenv("ADMIN_ID", "0"))
        return [int(i.strip()) for i in ids_str.split(",") if i.strip()]
    DB_HOST: str = os.getenv("DB_HOST", "localhost")
    DB_PORT: int = int(os.getenv("DB_PORT", "5432"))
    DB_NAME: str = os.getenv("DB_NAME", "tarot_bot")
    DB_USER: str = os.getenv("DB_USER", "postgres")
    DB_PASSWORD: str = os.getenv("DB_PASSWORD", "")

    ENCRYPTION_KEY: str = os.getenv("ENCRYPTION_KEY", "")

    OPENROUTER_API_KEY: str = os.getenv("OPENROUTER_API_KEY", "")
    OPENROUTER_MODEL: str = os.getenv("OPENROUTER_MODEL", "google/gemini-2.0-flash-001")

    APP_ENV: str = os.getenv("APP_ENV", "development")

    @property
    def database_url(self) -> str:
        """DSN для asyncpg."""
        return (
            f"postgresql+asyncpg://{self.DB_USER}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )

    @property
    def asyncpg_dsn(self) -> str:
        """DSN для asyncpg.create_pool()."""
        return (
            f"postgresql://{self.DB_USER}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )


settings = Settings()
