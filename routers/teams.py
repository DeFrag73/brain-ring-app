from fastapi import APIRouter, Depends, Form
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

import models
from database import get_db
from services.auth import get_current_admin
from services.helpers import admin_redirect
from services.game_service import broadcast_display_update

router = APIRouter()


@router.post("/admin/teams/add")
async def add_team(
        name: str = Form(...),
        members: str = Form(""),
        captain: str = Form(""),
        admin: str = Depends(get_current_admin),
        db: Session = Depends(get_db)
):
    team = models.Team(name=name, members=members, captain=captain)
    db.add(team)
    db.commit()
    return admin_redirect("teams")


@router.post("/admin/teams/{team_id}/delete")
async def delete_team(
        team_id: int,
        admin: str = Depends(get_current_admin),
        db: Session = Depends(get_db)
):
    team = db.query(models.Team).filter(models.Team.id == team_id).first()
    if team:
        db.query(models.GameResult).filter(
            (models.GameResult.team1_id == team_id) |
            (models.GameResult.team2_id == team_id) |
            (models.GameResult.winner_id == team_id)
        ).delete(synchronize_session=False)

        current_game = db.query(models.CurrentGame).first()
        update_display = False
        if current_game:
            if current_game.team1_id == team_id:
                current_game.team1_id = None
                update_display = True
            if current_game.team2_id == team_id:
                current_game.team2_id = None
                update_display = True

        db.delete(team)
        db.commit()

        if update_display:
            await broadcast_display_update(db)

    return admin_redirect("teams")


@router.get("/api/team-stats")
async def get_team_stats_api(db: Session = Depends(get_db)):
    teams = db.query(models.Team).all()
    stats = []

    for team in teams:
        games = db.query(models.GameResult).filter(
            (models.GameResult.team1_id == team.id) | (models.GameResult.team2_id == team.id)
        ).all()

        wins = losses = draws = total_points = 0
        opponents = []

        for game in games:
            if game.team1_id == team.id:
                total_points += game.team1_score or 0
                opponent = game.team2
                my_score, opp_score = game.team1_score, game.team2_score
            else:
                total_points += game.team2_score or 0
                opponent = game.team1
                my_score, opp_score = game.team2_score, game.team1_score

            if game.winner_id == team.id:
                wins += 1
                result = "win"
            elif game.winner_id is None:
                draws += 1
                result = "draw"
            else:
                losses += 1
                result = "loss"

            opponents.append({
                "opponent_name": opponent.name if opponent else "Невідомо",
                "my_score": my_score, "opponent_score": opp_score,
                "result": result,
                "played_at": game.played_at.strftime("%d.%m.%Y %H:%M") if game.played_at else ""
            })

        stats.append({
            "id": team.id, "name": team.name, "captain": team.captain,
            "wins": wins, "losses": losses, "draws": draws,
            "games_played": len(games), "total_points": total_points,
            "opponents": opponents,
            "win_rate": round((wins / len(games) * 100) if games else 0, 1)
        })

    stats.sort(key=lambda x: (-x["wins"], -x["total_points"]))
    return JSONResponse({"team_stats": stats})