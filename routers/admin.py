from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

import models
from models import DifficultyLevel
from database import get_db
from services.auth import get_current_admin

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/admin", response_class=HTMLResponse)
async def admin_panel(
        request: Request,
        sort_by: str = "number",
        sort_order: str = "asc",
        admin: str = Depends(get_current_admin),
        db: Session = Depends(get_db)
):
    questions_query = db.query(models.Question)

    if sort_by == "text":
        if sort_order == "desc":
            questions_query = questions_query.order_by(models.Question.text.desc())
        else:
            questions_query = questions_query.order_by(models.Question.text.asc())
    elif sort_by == "difficulty":
        questions = questions_query.all()
        questions.sort(key=lambda q: DifficultyLevel.get_sort_order(q.difficulty), reverse=(sort_order == "desc"))
    elif sort_by == "created_at":
        if sort_order == "desc":
            questions_query = questions_query.order_by(models.Question.created_at.desc())
        else:
            questions_query = questions_query.order_by(models.Question.created_at.asc())
    else:
        if sort_order == "desc":
            questions_query = questions_query.order_by(models.Question.number.desc())
        else:
            questions_query = questions_query.order_by(models.Question.number.asc())

    if sort_by != "difficulty":
        questions = questions_query.all()

    teams = db.query(models.Team).all()
    current_game = db.query(models.CurrentGame).first()

    if not current_game:
        current_game = models.CurrentGame()
        db.add(current_game)
        db.commit()
        db.refresh(current_game)

    # Статистика команд
    team_stats = []
    for team in teams:
        wins = db.query(models.GameResult).filter(models.GameResult.winner_id == team.id).count()
        games_played = db.query(models.GameResult).filter(
            (models.GameResult.team1_id == team.id) | (models.GameResult.team2_id == team.id)
        ).count()

        total_points = 0
        team_games = db.query(models.GameResult).filter(
            (models.GameResult.team1_id == team.id) | (models.GameResult.team2_id == team.id)
        ).all()
        losses = draws = 0
        opponents_info = []
        for game in team_games:
            if game.team1_id == team.id:
                total_points += game.team1_score or 0
                opp = game.team2
                my_score, opp_score = game.team1_score, game.team2_score
            else:
                total_points += game.team2_score or 0
                opp = game.team1
                my_score, opp_score = game.team2_score, game.team1_score

            if game.winner_id == team.id:
                result = "Перемога"
            elif game.winner_id is None:
                draws += 1
                result = "Нічия"
            else:
                losses += 1
                result = "Поразка"

            opponents_info.append({
                "opponent_name": opp.name if opp else "?",
                "my_score": my_score, "opp_score": opp_score,
                "result": result,
                "played_at": game.played_at.strftime("%d.%m.%Y %H:%M") if game.played_at else ""
            })

        team_stats.append({
            'team': team, 'wins': wins, 'losses': losses, 'draws': draws,
            'games_played': games_played, 'total_points': total_points,
            'opponents': opponents_info
        })

    team_stats.sort(key=lambda x: (-x['wins'], -x['total_points']))

    # Турнірна сітка
    bracket_matches = db.query(models.TournamentBracket).order_by(
        models.TournamentBracket.round_number, models.TournamentBracket.match_number
    ).all()

    bracket_rounds = {}
    for match in bracket_matches:
        r = match.round_number
        if r not in bracket_rounds:
            bracket_rounds[r] = []
        bracket_rounds[r].append(match)

    total_bracket_rounds = max(bracket_rounds.keys()) if bracket_rounds else 0
    round_names = {}
    if total_bracket_rounds > 0:
        round_names[total_bracket_rounds] = "Фінал"
        if total_bracket_rounds > 1:
            round_names[total_bracket_rounds - 1] = "Півфінал"
        if total_bracket_rounds > 2:
            round_names[total_bracket_rounds - 2] = "Чвертьфінал"
        if total_bracket_rounds > 3:
            round_names[total_bracket_rounds - 3] = "1/8 фіналу"
        for i in range(1, total_bracket_rounds - 3):
            round_names[i] = f"Раунд {i}"

    # Статистика по складності
    difficulty_stats = {}
    for difficulty in DifficultyLevel:
        count = db.query(models.Question).filter(models.Question.difficulty == difficulty).count()
        used_count = db.query(models.Question).filter(
            models.Question.difficulty == difficulty, models.Question.is_used == True
        ).count()
        difficulty_stats[difficulty.value] = {
            'total': count, 'used': used_count, 'available': count - used_count,
            'display_name': DifficultyLevel.get_display_name(difficulty),
            'color_class': DifficultyLevel.get_color_class(difficulty)
        }

    return templates.TemplateResponse(
        request=request,
        name="admin.html",
        context={
            "questions": questions, "teams": teams,
            "current_game": current_game, "team_stats": team_stats,
            "difficulty_stats": difficulty_stats,
            "difficulty_levels": [(level.value, DifficultyLevel.get_display_name(level)) for level in DifficultyLevel],
            "current_sort": {"by": sort_by, "order": sort_order},
            "bracket_rounds": bracket_rounds, "round_names": round_names,
            "total_bracket_rounds": total_bracket_rounds
        }
    )