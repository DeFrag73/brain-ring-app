from fastapi import APIRouter, Request, Depends, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

import models
from database import get_db
from services.connection_manager import manager
from services.game_service import broadcast_display_update

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        db = next(get_db())
        await broadcast_display_update(db)
        db.close()

        while True:
            data = await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)


@router.get("/display", response_class=HTMLResponse)
async def display_screen(request: Request, db: Session = Depends(get_db)):
    current_game = db.query(models.CurrentGame).first()

    team1 = team2 = current_question = None
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


@router.get("/api/display-data")
async def get_display_data(db: Session = Depends(get_db)):
    current_game = db.query(models.CurrentGame).first()

    data = {
        "team1": None, "team2": None,
        "team1_score": 0, "team2_score": 0,
        "current_question": None, "show_question": False
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
                "number": question.number, "text": question.text
            } if question else None

    return JSONResponse(data)