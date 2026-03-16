import math
import random

from fastapi import APIRouter, Depends, Form, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

import models
from database import get_db
from services.auth import get_current_admin
from services.helpers import admin_redirect

router = APIRouter()


def _advance_winners(db: Session, from_round: int):
    current_matches = db.query(models.TournamentBracket).filter(
        models.TournamentBracket.round_number == from_round
    ).order_by(models.TournamentBracket.match_number).all()

    next_round_matches = db.query(models.TournamentBracket).filter(
        models.TournamentBracket.round_number == from_round + 1
    ).order_by(models.TournamentBracket.match_number).all()

    if not next_round_matches:
        return

    for i, match in enumerate(current_matches):
        if match.winner_id:
            next_match_index = i // 2
            if next_match_index < len(next_round_matches):
                next_match = next_round_matches[next_match_index]
                if i % 2 == 0:
                    next_match.team1_id = match.winner_id
                else:
                    next_match.team2_id = match.winner_id
    db.commit()


@router.get("/api/tournament-bracket")
async def get_tournament_bracket(db: Session = Depends(get_db)):
    matches = db.query(models.TournamentBracket).order_by(
        models.TournamentBracket.round_number,
        models.TournamentBracket.match_number
    ).all()

    rounds = {}
    for match in matches:
        r = match.round_number
        if r not in rounds:
            rounds[r] = []
        rounds[r].append({
            "id": match.id, "match_number": match.match_number,
            "team1": {"id": match.team1_id, "name": match.team1.name if match.team1 else "TBD"},
            "team2": {"id": match.team2_id, "name": match.team2.name if match.team2 else "TBD"},
            "team1_score": match.team1_score, "team2_score": match.team2_score,
            "winner": {"id": match.winner_id, "name": match.winner.name if match.winner else None},
            "is_completed": match.is_completed
        })
    return JSONResponse({"rounds": rounds})


@router.post("/admin/tournament/generate")
async def generate_tournament_bracket(
        admin: str = Depends(get_current_admin),
        db: Session = Depends(get_db)
):
    teams = db.query(models.Team).all()
    if len(teams) < 2:
        return JSONResponse({"status": "error", "message": "Потрібно мінімум 2 команди"}, status_code=400)

    db.query(models.TournamentBracket).delete()
    db.commit()

    num_teams = len(teams)
    bracket_size = 1
    while bracket_size < num_teams:
        bracket_size *= 2

    total_rounds = int(math.log2(bracket_size))

    for round_num in range(1, total_rounds + 1):
        matches_in_round = bracket_size // (2 ** round_num)
        for match_num in range(1, matches_in_round + 1):
            match = models.TournamentBracket(round_number=round_num, match_number=match_num)
            db.add(match)
    db.commit()

    shuffled_teams = list(teams)
    random.shuffle(shuffled_teams)

    first_round = db.query(models.TournamentBracket).filter(
        models.TournamentBracket.round_number == 1
    ).order_by(models.TournamentBracket.match_number).all()

    team_index = 0
    for match in first_round:
        if team_index < len(shuffled_teams):
            match.team1_id = shuffled_teams[team_index].id
            team_index += 1
        if team_index < len(shuffled_teams):
            match.team2_id = shuffled_teams[team_index].id
            team_index += 1

        if match.team1_id and not match.team2_id:
            match.winner_id = match.team1_id
            match.is_completed = True
        elif match.team2_id and not match.team1_id:
            match.winner_id = match.team2_id
            match.is_completed = True

    db.commit()
    _advance_winners(db, 1)
    return admin_redirect("stats")


@router.post("/admin/tournament/match/{match_id}/result")
async def set_tournament_match_result(
        match_id: int,
        winner_team_id: int = Form(...),
        team1_score: float = Form(0),
        team2_score: float = Form(0),
        admin: str = Depends(get_current_admin),
        db: Session = Depends(get_db)
):
    match = db.query(models.TournamentBracket).filter(
        models.TournamentBracket.id == match_id
    ).first()
    if not match:
        raise HTTPException(status_code=404, detail="Матч не знайдено")

    match.team1_score = team1_score
    match.team2_score = team2_score
    match.winner_id = winner_team_id
    match.is_completed = True
    db.commit()
    _advance_winners(db, match.round_number)
    return admin_redirect("stats")


@router.post("/admin/tournament/reset")
async def reset_tournament_bracket(
        admin: str = Depends(get_current_admin),
        db: Session = Depends(get_db)
):
    db.query(models.TournamentBracket).delete()
    db.commit()
    return admin_redirect("stats")