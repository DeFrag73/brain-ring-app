from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
import models


def admin_redirect(section: str = "questions", extra_params: dict = None) -> RedirectResponse:
    """Створює RedirectResponse на /admin з параметром секції"""
    params = {"section": section}
    if extra_params:
        params.update(extra_params)
    query_string = "&".join(f"{k}={v}" for k, v in params.items())
    return RedirectResponse(f"/admin?{query_string}", status_code=303)


def renumber_questions(db: Session):
    """Перенумерація всіх питань за порядком створення"""
    questions = db.query(models.Question).order_by(models.Question.created_at).all()
    for idx, question in enumerate(questions, 1):
        question.number = idx
    db.commit()