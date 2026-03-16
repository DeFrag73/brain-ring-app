from fastapi import APIRouter, Request, Depends, Form, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
import secrets
from services.auth import create_access_token, ADMIN_USERNAME, ADMIN_PASSWORD

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})


@router.post("/login")
async def login(request: Request, username: str = Form(...), password: str = Form(...)):
    # Перевіряємо логін і пароль
    correct_username = secrets.compare_digest(username, ADMIN_USERNAME)
    correct_password = secrets.compare_digest(password, ADMIN_PASSWORD)

    if not (correct_username and correct_password):
        return templates.TemplateResponse(
            "login.html",
            {"request": request, "error": "Невірний логін або пароль"}
        )

    # Якщо все ок, генеруємо токен
    access_token = create_access_token(data={"sub": username})

    # Створюємо відповідь з перенаправленням на адмінку
    response = RedirectResponse(url="/admin", status_code=status.HTTP_303_SEE_OTHER)

    # Встановлюємо безпечну Cookie
    response.set_cookie(
        key="access_token",
        value=f"Bearer {access_token}",
        httponly=True,  # Захист від XSS атак
        max_age=60 * 60 * 24,  # 1 день
        samesite="lax"
    )
    return response


@router.get("/logout")
async def logout():
    # Перенаправляємо на сторінку логіну і видаляємо куку
    response = RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)
    response.delete_cookie("access_token")
    return response