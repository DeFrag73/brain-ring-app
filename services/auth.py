import secrets
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials

security = HTTPBasic()

# В реальному проєкті зберігайте в змінних середовища
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "brainring2025"


def get_current_admin(credentials: HTTPBasicCredentials = Depends(security)):
    """Перевірка авторизації адміністратора"""
    correct_username = secrets.compare_digest(credentials.username, ADMIN_USERNAME)
    correct_password = secrets.compare_digest(credentials.password, ADMIN_PASSWORD)
    if not (correct_username and correct_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Невірні дані для входу",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username