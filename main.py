from fastapi import FastAPI, Request, Form, Depends, HTTPException, status, WebSocket, WebSocketDisconnect, UploadFile, \
    File
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse, StreamingResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from sqlalchemy.orm import Session
from typing import Optional, List
import secrets
import json
import asyncio
import models
import database
import csv
import io
from database import get_db
from sqlalchemy import func
from models import DifficultyLevel

def admin_redirect(section: str = "questions", extra_params: dict = None) -> RedirectResponse:
    """Створює RedirectResponse на /admin з параметром секції"""
    params = {"section": section}
    if extra_params:
        params.update(extra_params)
    query_string = "&".join(f"{k}={v}" for k, v in params.items())
    return RedirectResponse(f"/admin?{query_string}", status_code=303)

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


# Список активних WebSocket з'єднань
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def send_personal_message(self, message: str, websocket: WebSocket):
        try:
            await websocket.send_text(message)
        except:
            self.disconnect(websocket)

    async def broadcast(self, message: str):
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except:
                disconnected.append(connection)

        # Видаляємо недоступні з'єднання
        for connection in disconnected:
            self.disconnect(connection)


manager = ConnectionManager()


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


async def broadcast_display_update(db: Session):
    """Функція для відправки оновлених даних всім підключеним клієнтам"""
    current_game = db.query(models.CurrentGame).first()

    data = {
        "type": "display_update",
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

    await manager.broadcast(json.dumps(data))


# Створення таблиць в базі даних при запуску
models.Base.metadata.create_all(bind=database.engine)


# ============= WEBSOCKET З'ЄДНАННЯ =============

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        # Відправляємо початкові дані після підключення
        db = next(get_db())
        await broadcast_display_update(db)
        db.close()

        while True:
            # Очікуємо повідомлення від клієнта (хоча вони не потрібні для display)
            data = await websocket.receive_text()
            # Можна обробляти команди від клієнта, якщо потрібно

    except WebSocketDisconnect:
        manager.disconnect(websocket)


# ============= МАРШРУТИ ДЛЯ АДМІНІСТРАТОРА =============

@app.get("/admin", response_class=HTMLResponse)
async def admin_panel(
        request: Request,
        sort_by: str = "number",  # Параметр сортування
        sort_order: str = "asc",  # Порядок сортування
        admin: str = Depends(get_current_admin),
        db: Session = Depends(get_db)
):
    """Головна сторінка адміністратора з сортуванням"""

    # Базовий запит для питань
    questions_query = db.query(models.Question)

    # Застосовуємо сортування
    if sort_by == "text":
        if sort_order == "desc":
            questions_query = questions_query.order_by(models.Question.text.desc())
        else:
            questions_query = questions_query.order_by(models.Question.text.asc())
    elif sort_by == "difficulty":
        # Отримуємо всі питання і сортуємо вручну за числовим порядком
        questions = questions_query.all()
        questions.sort(key=lambda q: DifficultyLevel.get_sort_order(q.difficulty), reverse=(sort_order == "desc"))
    elif sort_by == "created_at":
        if sort_order == "desc":
            questions_query = questions_query.order_by(models.Question.created_at.desc())
        else:
            questions_query = questions_query.order_by(models.Question.created_at.asc())
    else:  # sort_by == "number" або будь-що інше
        if sort_order == "desc":
            questions_query = questions_query.order_by(models.Question.number.desc())
        else:
            questions_query = questions_query.order_by(models.Question.number.asc())

    # Отримуємо питання (якщо ще не отримали при сортуванні за складністю)
    if sort_by != "difficulty":
        questions = questions_query.all()
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

    # Статистика по складності питань
    difficulty_stats = {}
    for difficulty in DifficultyLevel:
        count = db.query(models.Question).filter(models.Question.difficulty == difficulty).count()
        used_count = db.query(models.Question).filter(
            models.Question.difficulty == difficulty,
            models.Question.is_used == True
        ).count()
        difficulty_stats[difficulty.value] = {
            'total': count,
            'used': used_count,
            'available': count - used_count,
            'display_name': DifficultyLevel.get_display_name(difficulty),
            'color_class': DifficultyLevel.get_color_class(difficulty)
        }

    return templates.TemplateResponse("admin.html", {
        "request": request,
        "questions": questions,
        "teams": teams,
        "current_game": current_game,
        "team_stats": team_stats,
        "difficulty_stats": difficulty_stats,
        "difficulty_levels": [(level.value, DifficultyLevel.get_display_name(level)) for level in DifficultyLevel],
        "current_sort": {"by": sort_by, "order": sort_order}
    })


# ============= API для управління питаннями =============

@app.post("/admin/questions/renumber")
async def renumber_questions_endpoint(
        admin: str = Depends(get_current_admin),
        db: Session = Depends(get_db)
):
    """Ендпойнт для ручної перенумерації питань"""
    renumber_questions(db)
    return JSONResponse({"status": "success", "message": "Питання перенумеровано"})


# API ендпойнт для отримання статистики по складності
@app.get("/api/difficulty-stats")
async def get_difficulty_stats(db: Session = Depends(get_db)):
    """API для отримання статистики по рівням складності"""
    stats = {}
    for difficulty in DifficultyLevel:
        total = db.query(models.Question).filter(models.Question.difficulty == difficulty).count()
        used = db.query(models.Question).filter(
            models.Question.difficulty == difficulty,
            models.Question.is_used == True
        ).count()

        stats[difficulty.value] = {
            'display_name': DifficultyLevel.get_display_name(difficulty),
            'color_class': DifficultyLevel.get_color_class(difficulty),
            'total': total,
            'used': used,
            'available': total - used
        }

    return JSONResponse(stats)

# Функція для перенумерації питань
def renumber_questions(db: Session):
    """Перенумерація всіх питань за порядком створення"""
    questions = db.query(models.Question).order_by(models.Question.created_at).all()
    for idx, question in enumerate(questions, 1):
        question.number = idx
    db.commit()


# Оновлена функція додавання питання
@app.post("/admin/questions/add")
async def add_question(
        question_text: str = Form(...),
        notes: str = Form(""),
        difficulty: str = Form("medium"),
        admin: str = Depends(get_current_admin),
        db: Session = Depends(get_db)
):
    """Додавання нового питання"""
    # Конвертуємо строку в enum
    try:
        difficulty_enum = DifficultyLevel(difficulty)
    except ValueError:
        difficulty_enum = DifficultyLevel.MEDIUM

    # Знаходимо максимальний номер питання
    max_number = db.query(models.Question).count()

    question = models.Question(
        number=max_number + 1,
        text=question_text,
        notes=notes,
        difficulty=difficulty_enum
    )
    db.add(question)
    db.commit()

    # Перенумеровуємо всі питання
    renumber_questions(db)

    return admin_redirect("questions")


@app.post("/admin/questions/{question_id}/edit")
async def edit_question(
        question_id: int,
        question_text: str = Form(...),
        notes: str = Form(""),
        difficulty: str = Form("medium"),
        admin: str = Depends(get_current_admin),
        db: Session = Depends(get_db)
):
    """Редагування питання"""
    question = db.query(models.Question).filter(models.Question.id == question_id).first()
    if not question:
        raise HTTPException(status_code=404, detail="Питання не знайдено")

    # Конвертуємо строку в enum
    try:
        difficulty_enum = DifficultyLevel(difficulty)
    except ValueError:
        difficulty_enum = DifficultyLevel.MEDIUM

    question.text = question_text
    question.notes = notes
    question.difficulty = difficulty_enum
    db.commit()

    # Оновлюємо display якщо це поточне питання
    current_game = db.query(models.CurrentGame).first()
    if current_game and current_game.current_question_id == question_id:
        await broadcast_display_update(db)

    return admin_redirect("questions")


@app.post("/admin/questions/{question_id}/delete")
async def delete_question(
        question_id: int,
        admin: str = Depends(get_current_admin),
        db: Session = Depends(get_db)
):
    """Видалення питання"""
    question = db.query(models.Question).filter(models.Question.id == question_id).first()
    if question:
        # Якщо це поточне питання, приховати його з екрану
        current_game = db.query(models.CurrentGame).first()
        if current_game and current_game.current_question_id == question_id:
            current_game.current_question_id = None
            current_game.show_question = False
            db.commit()
            await broadcast_display_update(db)

        db.delete(question)
        db.commit()

        # Перенумеровуємо всі питання після видалення
        renumber_questions(db)

    return admin_redirect("questions")


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
    return admin_redirect("questions")


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
    return admin_redirect("teams")


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
        update_display = False
        if current_game:
            if current_game.team1_id == team_id:
                current_game.team1_id = None
                update_display = True
            if current_game.team2_id == team_id:
                current_game.team2_id = None
                update_display = True

        # Тепер можемо безпечно видалити команду
        db.delete(team)
        db.commit()

        # Оновлюємо display якщо команда була залучена в грі
        if update_display:
            await broadcast_display_update(db)

    return admin_redirect("teams")


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

    # Миттєво оновлюємо display
    await broadcast_display_update(db)

    return admin_redirect("game")


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

        # Миттєво оновлюємо display
        await broadcast_display_update(db)

    return admin_redirect("questions")


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

        # Миттєво оновлюємо display
        await broadcast_display_update(db)

    return admin_redirect("game")


@app.post("/admin/game/add-score")
async def add_score(
        team: str = Form(...),
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

        # Миттєво оновлюємо display
        await broadcast_display_update(db)

    return admin_redirect("game")


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

        # Миттєво оновлюємо display
        await broadcast_display_update(db)

    return admin_redirect("game")


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


# API ендпойнт для скидання статусу всіх питань
@app.post("/api/questions/reset-all")
async def reset_all_questions(
        admin: str = Depends(get_current_admin),
        db: Session = Depends(get_db)
):
    """Скидання статусу всіх питань"""
    db.query(models.Question).update({"is_used": False})
    db.commit()
    return JSONResponse({"status": "success", "message": "Статус всіх питань скинуто"})


# API ендпойнт для експорту питань в CSV
@app.get("/api/questions/export")
async def export_questions(
        admin: str = Depends(get_current_admin),
        db: Session = Depends(get_db)
):
    """Експорт питань у форматі CSV"""
    questions = db.query(models.Question).order_by(models.Question.number).all()

    output = io.StringIO()
    writer = csv.writer(output)

    # Заголовки
    writer.writerow(['Номер', 'Текст питання', 'Складність', 'Нотатки', 'Використано', 'Дата створення'])

    # Дані
    for question in questions:
        writer.writerow([
            question.number,
            question.text,
            question.difficulty_display,
            question.notes or '',
            'Так' if question.is_used else 'Ні',
            question.created_at.strftime('%Y-%m-%d %H:%M') if question.created_at else ''
        ])

    output.seek(0)

    return StreamingResponse(
        io.BytesIO(output.getvalue().encode('utf-8')),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=brainring_questions.csv"}
    )


# API ендпойнт для імпорту питань з CSV
@app.post("/api/questions/import")
async def import_questions(
        file: UploadFile = File(...),
        admin: str = Depends(get_current_admin),
        db: Session = Depends(get_db)
):
    """Імпорт питань з CSV файлу"""
    try:
        # Читаємо файл
        content = await file.read()
        csv_content = content.decode('utf-8')

        # Парсимо CSV
        reader = csv.DictReader(io.StringIO(csv_content))
        added_count = 0
        errors = []

        for row_num, row in enumerate(reader, 1):
            try:
                text = row.get('Текст питання') or row.get('text', '').strip()
                difficulty_str = row.get('Складність') or row.get('difficulty', 'medium')
                notes = row.get('Нотатки') or row.get('notes', '')

                if not text:
                    continue

                # Конвертуємо українську назву складності в enum
                difficulty_mapping = {
                    'Дуже легке': 'very_easy',
                    'Легке': 'easy',
                    'Середнє': 'medium',
                    'Складне': 'hard',
                    'Дуже складне': 'very_hard'
                }

                difficulty_value = difficulty_mapping.get(difficulty_str, difficulty_str.lower())

                try:
                    difficulty_enum = models.DifficultyLevel(difficulty_value)
                except ValueError:
                    difficulty_enum = models.DifficultyLevel.MEDIUM

                # Створюємо питання
                max_number = db.query(models.Question).count()
                question = models.Question(
                    number=max_number + 1,
                    text=text,
                    notes=notes,
                    difficulty=difficulty_enum
                )
                db.add(question)
                added_count += 1

            except Exception as e:
                errors.append(f"Рядок {row_num}: {str(e)}")

        if added_count > 0:
            db.commit()
            renumber_questions(db)

        return JSONResponse({
            "status": "success" if added_count > 0 else "warning",
            "message": f"Імпортовано {added_count} питань",
            "errors": errors
        })

    except Exception as e:
        return JSONResponse({
            "status": "error",
            "message": f"Помилка імпорту: {str(e)}"
        }, status_code=400)


# API ендпойнт для пакетного оновлення статусу питань
@app.post("/api/questions/bulk-update-status")
async def bulk_update_question_status(
        question_ids: List[int] = Form(...),
        mark_as_used: bool = Form(...),
        admin: str = Depends(get_current_admin),
        db: Session = Depends(get_db)
):
    """Пакетне оновлення статусу питань"""
    updated = db.query(models.Question).filter(
        models.Question.id.in_(question_ids)
    ).update({"is_used": mark_as_used}, synchronize_session=False)

    db.commit()

    return JSONResponse({
        "status": "success",
        "message": f"Оновлено статус {updated} питань"
    })


# API ендпойнт для отримання питань за складністю
@app.get("/api/questions/by-difficulty/{difficulty}")
async def get_questions_by_difficulty(
        difficulty: str,
        include_used: bool = False,
        db: Session = Depends(get_db)
):
    """Отримання питань за рівнем складності"""
    try:
        difficulty_enum = models.DifficultyLevel(difficulty)
    except ValueError:
        raise HTTPException(status_code=400, detail="Невірний рівень складності")

    query = db.query(models.Question).filter(models.Question.difficulty == difficulty_enum)

    if not include_used:
        query = query.filter(models.Question.is_used == False)

    questions = query.order_by(models.Question.number).all()

    return JSONResponse({
        "difficulty": models.DifficultyLevel.get_display_name(difficulty_enum),
        "total": len(questions),
        "questions": [
            {
                "id": q.id,
                "number": q.number,
                "text": q.text[:100] + "..." if len(q.text) > 100 else q.text,
                "is_used": q.is_used,
                "notes": q.notes
            }
            for q in questions
        ]
    })


# API ендпойнт для отримання статистики використання питань
@app.get("/api/questions/usage-stats")
async def get_question_usage_stats(db: Session = Depends(get_db)):
    """Детальна статистика використання питань"""
    stats = {}

    for difficulty in models.DifficultyLevel:
        total = db.query(models.Question).filter(
            models.Question.difficulty == difficulty
        ).count()

        used = db.query(models.Question).filter(
            models.Question.difficulty == difficulty,
            models.Question.is_used == True
        ).count()

        stats[difficulty.value] = {
            "display_name": models.DifficultyLevel.get_display_name(difficulty),
            "color_class": models.DifficultyLevel.get_color_class(difficulty),
            "total": total,
            "used": used,
            "available": total - used,
            "usage_percentage": round((used / total * 100) if total > 0 else 0, 1)
        }

    # Загальна статистика
    total_questions = db.query(models.Question).count()
    used_questions = db.query(models.Question).filter(models.Question.is_used == True).count()

    return JSONResponse({
        "by_difficulty": stats,
        "overall": {
            "total": total_questions,
            "used": used_questions,
            "available": total_questions - used_questions,
            "usage_percentage": round((used_questions / total_questions * 100) if total_questions > 0 else 0, 1)
        }
    })


# API ендпойнт для отримання рекомендацій питань
@app.get("/api/questions/recommendations")
async def get_question_recommendations(
        difficulty: Optional[str] = None,
        exclude_used: bool = True,
        limit: int = 10,
        db: Session = Depends(get_db)
):
    """Отримання рекомендованих питань для гри"""
    query = db.query(models.Question)

    if exclude_used:
        query = query.filter(models.Question.is_used == False)

    if difficulty:
        try:
            difficulty_enum = models.DifficultyLevel(difficulty)
            query = query.filter(models.Question.difficulty == difficulty_enum)
        except ValueError:
            pass

    # Сортуємо по створенню і беремо випадкові
    questions = query.order_by(func.random()).limit(limit).all()

    return JSONResponse({
        "questions": [
            {
                "id": q.id,
                "number": q.number,
                "text": q.text,
                "difficulty": q.difficulty_display,
                "difficulty_color": q.difficulty_color,
                "notes": q.notes,
                "is_used": q.is_used
            }
            for q in questions
        ],
        "total_found": len(questions)
    })


# API ендпойнт для пошуку питань
@app.get("/api/questions/search")
async def search_questions(
        q: str = "",
        difficulty: Optional[str] = None,
        used_status: Optional[str] = None,
        limit: int = 50,
        db: Session = Depends(get_db)
):
    """Пошук питань за різними критеріями"""
    query = db.query(models.Question)

    # Пошук за текстом
    if q:
        search_term = f"%{q}%"
        query = query.filter(
            (models.Question.text.like(search_term)) |
            (models.Question.notes.like(search_term))
        )

    # Фільтр за складністю
    if difficulty:
        try:
            difficulty_enum = models.DifficultyLevel(difficulty)
            query = query.filter(models.Question.difficulty == difficulty_enum)
        except ValueError:
            pass

    # Фільтр за статусом використання
    if used_status == "used":
        query = query.filter(models.Question.is_used == True)
    elif used_status == "available":
        query = query.filter(models.Question.is_used == False)

    questions = query.order_by(models.Question.number).limit(limit).all()

    return JSONResponse({
        "questions": [
            {
                "id": q.id,
                "number": q.number,
                "text": q.text[:150] + "..." if len(q.text) > 150 else q.text,
                "difficulty": q.difficulty_display,
                "difficulty_color": q.difficulty_color,
                "notes": q.notes,
                "is_used": q.is_used,
                "created_at": q.created_at.isoformat() if q.created_at else None
            }
            for q in questions
        ],
        "total_found": len(questions),
        "search_query": q,
        "filters": {
            "difficulty": difficulty,
            "used_status": used_status
        }
    })

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