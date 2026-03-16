from fastapi import APIRouter, Depends, Form
from sqlalchemy.orm import Session

import models
from database import get_db
from services.auth import get_current_admin
from services.helpers import admin_redirect
from services.game_service import broadcast_display_update

router = APIRouter()


@router.post("/admin/game/set-teams")
async def set_current_teams(
        team1_id: int = Form(...),
        team2_id: int = Form(...),
        admin: str = Depends(get_current_admin),
        db: Session = Depends(get_db)
):
    if team1_id == team2_id:
        return admin_redirect("game", extra_params={"error": "same_teams"})

    current_game = db.query(models.CurrentGame).first()
    if not current_game:
        current_game = models.CurrentGame()
        db.add(current_game)

    current_game.team1_id = team1_id
    current_game.team2_id = team2_id
    current_game.team1_score = 0
    current_game.team2_score = 0
    db.commit()
    await broadcast_display_update(db)
    return admin_redirect("game")


@router.post("/admin/game/show-question/{question_id}")
async def show_question(
        question_id: int,
        admin: str = Depends(get_current_admin),
        db: Session = Depends(get_db)
):
    current_game = db.query(models.CurrentGame).first()
    if current_game:
        current_game.current_question_id = question_id
        current_game.show_question = True
        db.commit()
        await broadcast_display_update(db)
    return admin_redirect("questions")


@router.post("/admin/game/hide-question")
async def hide_question(
        admin: str = Depends(get_current_admin),
        db: Session = Depends(get_db)
):
    current_game = db.query(models.CurrentGame).first()
    if current_game:
        current_game.show_question = False
        db.commit()
        await broadcast_display_update(db)
    return admin_redirect("game")


@router.post("/admin/game/add-score")
async def add_score(
        team: str = Form(...),
        points: float = Form(...),
        admin: str = Depends(get_current_admin),
        db: Session = Depends(get_db)
):
    current_game = db.query(models.CurrentGame).first()
    if current_game:
        if team == "team1":
            current_game.team1_score += points
        elif team == "team2":
            current_game.team2_score += points
        db.commit()

        if current_game.current_question_id:
            question = db.query(models.Question).filter(
                models.Question.id == current_game.current_question_id
            ).first()
            if question:
                question.is_used = True
                db.commit()

        await broadcast_display_update(db)
    return admin_redirect("game")


@router.post("/admin/game/finish-round")
async def finish_round(
        admin: str = Depends(get_current_admin),
        db: Session = Depends(get_db)
):
    current_game = db.query(models.CurrentGame).first()
    if current_game and current_game.team1_id and current_game.team2_id:
        winner_id = None
        if current_game.team1_score > current_game.team2_score:
            winner_id = current_game.team1_id
        elif current_game.team2_score > current_game.team1_score:
            winner_id = current_game.team2_id

        result = models.GameResult(
            team1_id=current_game.team1_id,
            team2_id=current_game.team2_id,
            team1_score=current_game.team1_score,
            team2_score=current_game.team2_score,
            winner_id=winner_id
        )
        db.add(result)

        current_game.team1_id = None
        current_game.team2_id = None
        current_game.team1_score = 0
        current_game.team2_score = 0
        current_game.current_question_id = None
        current_game.show_question = False
        db.commit()
        await broadcast_display_update(db)

    return admin_redirect("game")