import os
import secrets
from datetime import datetime, timedelta, timezone
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
import jwt

app = FastAPI()

# 1. Конфігурація (У реальному проєкті зберігайте це в .env!)
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "brainring2025")

# Секретний ключ для підпису JWT (згенеруйте надійний рядок, наприклад через `openssl rand -hex 32`)
SECRET_KEY = os.getenv("SECRET_KEY", "your-very-secret-key-change-it-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# 2. Налаштування схеми OAuth2 (вказуємо URL ендпоінту, де видається токен)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


def create_access_token(data: dict, expires_delta: timedelta | None = None):
    """Створення JWT токена"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)

    to_encode.update({"exp": expire})
    # Підписуємо дані нашим секретним ключем
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


async def get_current_admin(token: str = Depends(oauth2_scheme)):
    """Перевірка JWT токена (наш новий захист)"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Не вдалося перевірити облікові дані",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        # Розшифровуємо токен
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")

        # Перевіряємо, чи є логін у токені і чи це саме адмін
        if username is None or username != ADMIN_USERNAME:
            raise credentials_exception

    except jwt.InvalidTokenError:  # Спрацює, якщо токен підроблений або протермінований
        raise credentials_exception

    return username


# 3. Ендпоінт для входу (генерація токена)
@app.post("/token")
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    # Перевіряємо логін і пароль, які надіслав користувач
    correct_username = secrets.compare_digest(form_data.username, ADMIN_USERNAME)
    correct_password = secrets.compare_digest(form_data.password, ADMIN_PASSWORD)

    if not (correct_username and correct_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Невірний логін або пароль",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Якщо все ок — створюємо токен
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": form_data.username}, expires_delta=access_token_expires
    )

    return {"access_token": access_token, "token_type": "bearer"}


# 4. Приклад захищеного маршруту
@app.get("/protected-admin-data")
async def read_admin_data(current_admin: str = Depends(get_current_admin)):
    return {"message": "Вітаю! Ти успішно пройшов JWT авторизацію.", "admin": current_admin}