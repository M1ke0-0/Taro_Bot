"""
Кастомный SQLAlchemy TypeDecorator для прозрачного шифрования данных.
Использует симметричное шифрование Fernet (библиотека cryptography).

Как это работает:
- При записи в БД (process_bind_param): строка → зашифрованная строка
- При чтении из БД (process_result_value): зашифрованная строка → исходная строка
- Код вне этого файла не знает о шифровании — всё прозрачно.

Генерация ключа (выполнить 1 раз!):
    python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
Полученный ключ записать в .env как ENCRYPTION_KEY=...
"""

import os
from datetime import date

from cryptography.fernet import Fernet, InvalidToken
from sqlalchemy import String, TypeDecorator


def _get_fernet() -> Fernet:
    key = os.getenv("ENCRYPTION_KEY")
    if not key:
        raise RuntimeError(
            "ENCRYPTION_KEY не задан в переменных окружения! "
            "Сгенерируйте ключ командой:\n"
            "  python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\"\n"
            "и добавьте его в .env."
        )
    return Fernet(key.encode())


class EncryptedString(TypeDecorator):
    """
    Зашифрованное строковое поле (Fernet AES-128-CBC).
    Данные хранятся в БД в виде base64-строки.
    При чтении автоматически расшифровываются.
    """

    impl = String
    cache_ok = True

    def process_bind_param(self, value: str | None, dialect) -> str | None:
        """При записи в БД — шифруем строку."""
        if value is None:
            return None
        fernet = _get_fernet()
        return fernet.encrypt(value.encode()).decode()

    def process_result_value(self, value: str | None, dialect) -> str | None:
        """При чтении из БД — расшифровываем строку."""
        if value is None:
            return None
        try:
            fernet = _get_fernet()
            return fernet.decrypt(value.encode()).decode()
        except InvalidToken:
            # Не удалось расшифровать — возможно, старые незашифрованные данные
            return value


class EncryptedDate(TypeDecorator):
    """
    Зашифрованное поле даты.
    В БД хранится строка вида 'YYYY-MM-DD' в зашифрованном виде.
    """

    impl = String
    cache_ok = True

    def process_bind_param(self, value: date | None, dialect) -> str | None:
        """При записи — конвертируем date в строку и шифруем."""
        if value is None:
            return None
        fernet = _get_fernet()
        return fernet.encrypt(str(value).encode()).decode()

    def process_result_value(self, value: str | None, dialect) -> date | None:
        """При чтении — расшифровываем и конвертируем в date."""
        if value is None:
            return None
        try:
            fernet = _get_fernet()
            decrypted = fernet.decrypt(value.encode()).decode()
            return date.fromisoformat(decrypted)
        except (InvalidToken, ValueError):
            # Старые данные без шифрования
            try:
                return date.fromisoformat(value)
            except ValueError:
                return None
