import os
import secrets
from datetime import datetime, timedelta, timezone
from fastapi import Request, HTTPException, status
import jwt

# Конфігурація
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "brainring2025")
SECRET_KEY = os.getenv("SECRET_KEY", "super-secret-key-change-it")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # Токен діє 1 день


class RequiresLoginException(Exception):
    """Спеціальний виняток для перенаправлення неавторизованих користувачів"""
    pass


def create_access_token(data: dict):
    """Створення JWT токена"""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


async def get_current_admin(request: Request):
    """Перевірка JWT токена з Cookies"""
    token = request.cookies.get("access_token")

    if not token:
        raise RequiresLoginException()

    try:
        # Відрізаємо приставку "Bearer " якщо вона є
        if token.startswith("Bearer "):
            token = token.split(" ")[1]

        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")

        if username is None or username != ADMIN_USERNAME:
            raise RequiresLoginException()

    except jwt.InvalidTokenError:
        raise RequiresLoginException()

    return username