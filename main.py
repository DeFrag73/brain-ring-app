from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse

import models
import database
from routers import admin, questions, teams, game, display, tournament

# Створення FastAPI додатку
app = FastAPI(title="Брейн-ринг", description="Додаток для проведення ігор Брейн-ринг")

# Налаштування статичних файлів
app.mount("/static", StaticFiles(directory="static"), name="static")

# Підключення роутерів
app.include_router(admin.router)
app.include_router(questions.router)
app.include_router(teams.router)
app.include_router(game.router)
app.include_router(display.router)
app.include_router(tournament.router)

# Створення таблиць в базі даних при запуску
models.Base.metadata.create_all(bind=database.engine)


@app.get("/")
async def root():
    """Перенаправлення на адмін панель"""
    return RedirectResponse("/admin")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
