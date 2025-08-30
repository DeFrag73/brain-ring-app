from fastapi import FastAPI, Request, Form, Depends, HTTPException, status
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from sqlalchemy.orm import Session
from typing import Optional, List
import secrets
import models
import database
from database import get_db

# Створення FastAPI додатку
app = FastAPI(title="Брейн-ринг", description="Додаток для проведення ігор Брейн-ринг")

# Налаштування шаблонів та статичних файлів
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

# Проста HTTP Basic авторизація
security = HTTPBasic()

# Дані для авторизації (в реальному додатку зберігайте в змінних середовища)
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


# Створення таблиць в базі даних при запуску
models.Base.metadata.create_all(bind=database.engine)


# ============= МАРШРУТИ ДЛЯ АДМІНІСТРАТОРА =============

@app.get("/admin", response_class=HTMLResponse)
async def admin_panel(request: Request, admin: str = Depends(get_current_admin), db: Session = Depends(get_db)):
    """Головна сторінка адміністратора"""
    # Отримуємо всі дані для відображення
    questions = db.query(models.Question).all()
    teams = db.query(models.Team).all()
    current_game = db.query(models.CurrentGame).first()

    # Якщо немає поточної гри, створюємо
    if not current_game:
        current_game = models.CurrentGame()
        db.add(current_game)
        db.commit()
        db.refresh(current_game)

    # Статистика команд
    team_stats = []
    for team in teams:
        wins = db.query(models.GameResult).filter(models.GameResult.winner_id == team.id).count()
        total_score = db.query(models.GameResult).filter(
            (models.GameResult.team1_id == team.id) | (models.GameResult.team2_id == team.id)
        ).count()
        team_stats.append({
            'team': team,
            'wins': wins,
            'games_played': total_score
        })

    return templates.TemplateResponse("admin.html", {
        "request": request,
        "questions": questions,
        "teams": teams,
        "current_game": current_game,
        "team_stats": team_stats
    })


# ============= API для управління питаннями =============

@app.post("/admin/questions/add")
async def add_question(
        question_text: str = Form(...),
        notes: str = Form(""),
        admin: str = Depends(get_current_admin),
        db: Session = Depends(get_db)
):
    """Додавання нового питання"""
    # Знаходимо максимальний номер питання
    max_number = db.query(models.Question).count()

    question = models.Question(
        number=max_number + 1,
        text=question_text,
        notes=notes
    )
    db.add(question)
    db.commit()
    return RedirectResponse("/admin", status_code=303)


@app.post("/admin/questions/{question_id}/edit")
async def edit_question(
        question_id: int,
        question_text: str = Form(...),
        notes: str = Form(""),
        admin: str = Depends(get_current_admin),
        db: Session = Depends(get_db)
):
    """Редагування питання"""
    question = db.query(models.Question).filter(models.Question.id == question_id).first()
    if not question:
        raise HTTPException(status_code=404, detail="Питання не знайдено")

    question.text = question_text
    question.notes = notes
    db.commit()
    return RedirectResponse("/admin", status_code=303)


@app.post("/admin/questions/{question_id}/delete")
async def delete_question(
        question_id: int,
        admin: str = Depends(get_current_admin),
        db: Session = Depends(get_db)
):
    """Видалення питання"""
    question = db.query(models.Question).filter(models.Question.id == question_id).first()
    if question:
        db.delete(question)
        db.commit()
    return RedirectResponse("/admin", status_code=303)


@app.post("/admin/questions/{question_id}/toggle-used")
async def toggle_question_used(
        question_id: int,
        admin: str = Depends(get_current_admin),
        db: Session = Depends(get_db)
):
    """Позначити питання як використане/невикористане"""
    question = db.query(models.Question).filter(models.Question.id == question_id).first()
    if question:
        question.is_used = not question.is_used
        db.commit()
    return RedirectResponse("/admin", status_code=303)


# ============= API для управління командами =============

@app.post("/admin/teams/add")
async def add_team(
        name: str = Form(...),
        members: str = Form(""),
        captain: str = Form(""),
        admin: str = Depends(get_current_admin),
        db: Session = Depends(get_db)
):
    """Додавання нової команди"""
    team = models.Team(
        name=name,
        members=members,
        captain=captain
    )
    db.add(team)
    db.commit()
    return RedirectResponse("/admin", status_code=303)


@app.post("/admin/teams/{team_id}/delete")
async def delete_team(
        team_id: int,
        admin: str = Depends(get_current_admin),
        db: Session = Depends(get_db)
):
    """Видалення команди"""
    team = db.query(models.Team).filter(models.Team.id == team_id).first()
    if team:
        # Спочатку видаляємо пов'язані записи з game_results
        db.query(models.GameResult).filter(
            (models.GameResult.team1_id == team_id) |
            (models.GameResult.team2_id == team_id) |
            (models.GameResult.winner_id == team_id)
        ).delete(synchronize_session=False)

        # Також оновлюємо current_game, якщо там є посилання на цю команду
        current_game = db.query(models.CurrentGame).first()
        if current_game:
            if current_game.team1_id == team_id:
                current_game.team1_id = None
            if current_game.team2_id == team_id:
                current_game.team2_id = None

        # Тепер можемо безпечно видалити команду
        db.delete(team)
        db.commit()
    return RedirectResponse("/admin", status_code=303)


# ============= API для управління грою =============

@app.post("/admin/game/set-teams")
async def set_current_teams(
        team1_id: int = Form(...),
        team2_id: int = Form(...),
        admin: str = Depends(get_current_admin),
        db: Session = Depends(get_db)
):
    """Встановлення команд для поточного раунду"""
    current_game = db.query(models.CurrentGame).first()
    if not current_game:
        current_game = models.CurrentGame()
        db.add(current_game)

    current_game.team1_id = team1_id
    current_game.team2_id = team2_id
    current_game.team1_score = 0
    current_game.team2_score = 0
    db.commit()
    return RedirectResponse("/admin", status_code=303)


@app.post("/admin/game/show-question/{question_id}")
async def show_question(
        question_id: int,
        admin: str = Depends(get_current_admin),
        db: Session = Depends(get_db)
):
    """Показати питання на екрані глядачів"""
    current_game = db.query(models.CurrentGame).first()
    if current_game:
        current_game.current_question_id = question_id
        current_game.show_question = True
        db.commit()
    return RedirectResponse("/admin", status_code=303)


@app.post("/admin/game/hide-question")
async def hide_question(
        admin: str = Depends(get_current_admin),
        db: Session = Depends(get_db)
):
    """Сховати питання з екрану глядачів"""
    current_game = db.query(models.CurrentGame).first()
    if current_game:
        current_game.show_question = False
        db.commit()
    return RedirectResponse("/admin", status_code=303)


@app.post("/admin/game/add-score")
async def add_score(
        team: str = Form(...),  # "team1" або "team2"
        points: float = Form(...),
        admin: str = Depends(get_current_admin),
        db: Session = Depends(get_db)
):
    """Додати/зняти бали команді"""
    current_game = db.query(models.CurrentGame).first()
    if current_game:
        if team == "team1":
            current_game.team1_score += points
        elif team == "team2":
            current_game.team2_score += points
        db.commit()

        # Автоматично позначити поточне питання як використане
        if current_game.current_question_id:
            question = db.query(models.Question).filter(
                models.Question.id == current_game.current_question_id
            ).first()
            if question:
                question.is_used = True
                db.commit()

    return RedirectResponse("/admin", status_code=303)


@app.post("/admin/game/finish-round")
async def finish_round(
        admin: str = Depends(get_current_admin),
        db: Session = Depends(get_db)
):
    """Завершити поточний раунд і записати результат"""
    current_game = db.query(models.CurrentGame).first()
    if current_game and current_game.team1_id and current_game.team2_id:
        # Визначаємо переможця
        winner_id = None
        if current_game.team1_score > current_game.team2_score:
            winner_id = current_game.team1_id
        elif current_game.team2_score > current_game.team1_score:
            winner_id = current_game.team2_id

        # Записуємо результат
        result = models.GameResult(
            team1_id=current_game.team1_id,
            team2_id=current_game.team2_id,
            team1_score=current_game.team1_score,
            team2_score=current_game.team2_score,
            winner_id=winner_id
        )
        db.add(result)

        # Очищаємо поточну гру
        current_game.team1_id = None
        current_game.team2_id = None
        current_game.team1_score = 0
        current_game.team2_score = 0
        current_game.current_question_id = None
        current_game.show_question = False

        db.commit()

    return RedirectResponse("/admin", status_code=303)


# ============= ЕКРАН ГЛЯДАЧІВ =============

@app.get("/display", response_class=HTMLResponse)
async def display_screen(request: Request, db: Session = Depends(get_db)):
    """Екран для глядачів (проєктор)"""
    current_game = db.query(models.CurrentGame).first()

    # Отримуємо дані для відображення
    team1 = None
    team2 = None
    current_question = None

    if current_game:
        if current_game.team1_id:
            team1 = db.query(models.Team).filter(models.Team.id == current_game.team1_id).first()
        if current_game.team2_id:
            team2 = db.query(models.Team).filter(models.Team.id == current_game.team2_id).first()
        if current_game.current_question_id and current_game.show_question:
            current_question = db.query(models.Question).filter(
                models.Question.id == current_game.current_question_id
            ).first()

    return templates.TemplateResponse("display.html", {
        "request": request,
        "current_game": current_game,
        "team1": team1,
        "team2": team2,
        "current_question": current_question
    })


# ============= API ДЛЯ REAL-TIME ОНОВЛЕНЬ =============

@app.get("/api/display-data")
async def get_display_data(db: Session = Depends(get_db)):
    """API для отримання даних екрану глядачів (для real-time оновлень)"""
    current_game = db.query(models.CurrentGame).first()

    data = {
        "team1": None,
        "team2": None,
        "team1_score": 0,
        "team2_score": 0,
        "current_question": None,
        "show_question": False
    }

    if current_game:
        data["team1_score"] = current_game.team1_score or 0
        data["team2_score"] = current_game.team2_score or 0
        data["show_question"] = current_game.show_question or False

        if current_game.team1_id:
            team1 = db.query(models.Team).filter(models.Team.id == current_game.team1_id).first()
            data["team1"] = team1.name if team1 else None

        if current_game.team2_id:
            team2 = db.query(models.Team).filter(models.Team.id == current_game.team2_id).first()
            data["team2"] = team2.name if team2 else None

        if current_game.current_question_id and current_game.show_question:
            question = db.query(models.Question).filter(
                models.Question.id == current_game.current_question_id
            ).first()
            data["current_question"] = {
                "number": question.number,
                "text": question.text
            } if question else None

    return JSONResponse(data)


# ============= ГОЛОВНА СТОРІНКА =============

@app.get("/")
async def root():
    """Перенаправлення на адмін панель"""
    return RedirectResponse("/admin")


# ============= ЗАПУСК ДОДАТКУ =============

if __name__ == "__main__":
    import uvicorn

    # Запуск додатку на localhost:8000
    uvicorn.run(app, host="0.0.0.0", port=8000)