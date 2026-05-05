from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, Request
from contextlib import asynccontextmanager
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from services.auth import RequiresLoginException

import models
import database
from routers import admin, questions, teams, game, display, tournament, auth, buzzer
from services.lighting import light_manager


@asynccontextmanager
async def lifespan(app: FastAPI):
    connected = await light_manager.connect()
    if not connected:
        raise RuntimeError("Сервер не запущено: не вдалося підтвердити підключення до ламп Tapo")
    yield
    # Виконується при зупинці (можна вимкнути лампи, якщо треба)


app = FastAPI(title="Брейн-ринг", description="Додаток для проведення ігор Брейн-ринг", lifespan=lifespan)

app.mount("/static", StaticFiles(directory="static"), name="static")

@app.exception_handler(RequiresLoginException)
async def requires_login_exception_handler(request: Request, exc: RequiresLoginException):
    return RedirectResponse(url="/login")

# Підключення роутерів
app.include_router(auth.router)
app.include_router(admin.router)
app.include_router(questions.router)
app.include_router(teams.router)
app.include_router(game.router)
app.include_router(display.router)
app.include_router(tournament.router)
app.include_router(buzzer.router)

models.Base.metadata.create_all(bind=database.engine)

@app.get("/")
async def root():
    return RedirectResponse("/admin")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)