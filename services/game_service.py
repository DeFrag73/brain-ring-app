import json
from sqlalchemy.orm import Session
import models
from services.connection_manager import manager


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