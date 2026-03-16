from fastapi import APIRouter, Depends, Form, HTTPException, UploadFile, File
from fastapi.responses import JSONResponse, StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Optional, List
import csv
import io

import models
from models import DifficultyLevel
from database import get_db
from services.auth import get_current_admin
from services.helpers import admin_redirect, renumber_questions
from services.game_service import broadcast_display_update

router = APIRouter()


@router.post("/admin/questions/renumber")
async def renumber_questions_endpoint(
        admin: str = Depends(get_current_admin),
        db: Session = Depends(get_db)
):
    renumber_questions(db)
    return JSONResponse({"status": "success", "message": "Питання перенумеровано"})


@router.get("/api/difficulty-stats")
async def get_difficulty_stats(db: Session = Depends(get_db)):
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


@router.post("/admin/questions/add")
async def add_question(
        question_text: str = Form(...),
        notes: str = Form(""),
        difficulty: str = Form("medium"),
        admin: str = Depends(get_current_admin),
        db: Session = Depends(get_db)
):
    try:
        difficulty_enum = DifficultyLevel(difficulty)
    except ValueError:
        difficulty_enum = DifficultyLevel.MEDIUM

    max_number = db.query(models.Question).count()
    question = models.Question(
        number=max_number + 1,
        text=question_text,
        notes=notes,
        difficulty=difficulty_enum
    )
    db.add(question)
    db.commit()
    renumber_questions(db)
    return admin_redirect("questions")


@router.post("/admin/questions/{question_id}/edit")
async def edit_question(
        question_id: int,
        question_text: str = Form(...),
        notes: str = Form(""),
        difficulty: str = Form("medium"),
        admin: str = Depends(get_current_admin),
        db: Session = Depends(get_db)
):
    question = db.query(models.Question).filter(models.Question.id == question_id).first()
    if not question:
        raise HTTPException(status_code=404, detail="Питання не знайдено")

    try:
        difficulty_enum = DifficultyLevel(difficulty)
    except ValueError:
        difficulty_enum = DifficultyLevel.MEDIUM

    question.text = question_text
    question.notes = notes
    question.difficulty = difficulty_enum
    db.commit()

    current_game = db.query(models.CurrentGame).first()
    if current_game and current_game.current_question_id == question_id:
        await broadcast_display_update(db)

    return admin_redirect("questions")


@router.post("/admin/questions/{question_id}/delete")
async def delete_question(
        question_id: int,
        admin: str = Depends(get_current_admin),
        db: Session = Depends(get_db)
):
    question = db.query(models.Question).filter(models.Question.id == question_id).first()
    if question:
        current_game = db.query(models.CurrentGame).first()
        if current_game and current_game.current_question_id == question_id:
            current_game.current_question_id = None
            current_game.show_question = False
            db.commit()
            await broadcast_display_update(db)

        db.delete(question)
        db.commit()
        renumber_questions(db)

    return admin_redirect("questions")


@router.post("/admin/questions/{question_id}/toggle-used")
async def toggle_question_used(
        question_id: int,
        admin: str = Depends(get_current_admin),
        db: Session = Depends(get_db)
):
    question = db.query(models.Question).filter(models.Question.id == question_id).first()
    if question:
        question.is_used = not question.is_used
        db.commit()
    return admin_redirect("questions")


@router.post("/api/questions/reset-all")
async def reset_all_questions(
        admin: str = Depends(get_current_admin),
        db: Session = Depends(get_db)
):
    db.query(models.Question).update({"is_used": False})
    db.commit()
    return JSONResponse({"status": "success", "message": "Статус всіх питань скинуто"})


@router.get("/api/questions/export")
async def export_questions(
        admin: str = Depends(get_current_admin),
        db: Session = Depends(get_db)
):
    questions = db.query(models.Question).order_by(models.Question.number).all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Текст питання', 'Складність', 'Нотатки', 'Використано'])
    for question in questions:
        writer.writerow([
            question.text,
            question.difficulty_display,
            question.notes or '',
            'Так' if question.is_used else 'Ні',
        ])

    output.seek(0)
    bom = '\ufeff'
    csv_bytes = (bom + output.getvalue()).encode('utf-8')

    return StreamingResponse(
        io.BytesIO(csv_bytes),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=brainring_questions.csv"}
    )


@router.post("/api/questions/import")
async def import_questions(
        file: UploadFile = File(...),
        admin: str = Depends(get_current_admin),
        db: Session = Depends(get_db)
):
    try:
        content = await file.read()
        csv_content = content.decode('utf-8-sig')
        reader = csv.DictReader(io.StringIO(csv_content))
        added_count = 0
        errors = []

        difficulty_mapping = {
            'дуже легке': 'very_easy',
            'легке': 'easy',
            'середнє': 'medium',
            'складне': 'hard',
            'дуже складне': 'very_hard',
        }
        used_mapping = {
            'так': True, 'ні': False,
            'yes': True, 'no': False,
            'true': True, 'false': False,
            '1': True, '0': False,
        }

        for row_num, row in enumerate(reader, 1):
            try:
                text = (row.get('Текст питання') or row.get('text') or '').strip()
                difficulty_str = (row.get('Складність') or row.get('difficulty') or 'medium').strip()
                notes = (row.get('Нотатки') or row.get('notes') or '').strip()
                used_str = (row.get('Використано') or row.get('is_used') or '').strip().lower()

                if not text:
                    continue

                difficulty_value = difficulty_mapping.get(difficulty_str.lower(), difficulty_str.lower())
                try:
                    difficulty_enum = models.DifficultyLevel(difficulty_value)
                except ValueError:
                    difficulty_enum = models.DifficultyLevel.MEDIUM

                is_used = used_mapping.get(used_str, False)

                max_number = db.query(models.Question).count()
                question = models.Question(
                    number=max_number + 1,
                    text=text,
                    notes=notes,
                    difficulty=difficulty_enum,
                    is_used=is_used
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
        return JSONResponse({"status": "error", "message": f"Помилка імпорту: {str(e)}"}, status_code=400)


@router.post("/api/questions/bulk-update-status")
async def bulk_update_question_status(
        question_ids: List[int] = Form(...),
        mark_as_used: bool = Form(...),
        admin: str = Depends(get_current_admin),
        db: Session = Depends(get_db)
):
    updated = db.query(models.Question).filter(
        models.Question.id.in_(question_ids)
    ).update({"is_used": mark_as_used}, synchronize_session=False)
    db.commit()
    return JSONResponse({"status": "success", "message": f"Оновлено статус {updated} питань"})


@router.get("/api/questions/by-difficulty/{difficulty}")
async def get_questions_by_difficulty(
        difficulty: str,
        include_used: bool = False,
        db: Session = Depends(get_db)
):
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
                "id": q.id, "number": q.number,
                "text": q.text[:100] + "..." if len(q.text) > 100 else q.text,
                "is_used": q.is_used, "notes": q.notes
            }
            for q in questions
        ]
    })


@router.get("/api/questions/usage-stats")
async def get_question_usage_stats(db: Session = Depends(get_db)):
    stats = {}
    for difficulty in models.DifficultyLevel:
        total = db.query(models.Question).filter(models.Question.difficulty == difficulty).count()
        used = db.query(models.Question).filter(
            models.Question.difficulty == difficulty,
            models.Question.is_used == True
        ).count()
        stats[difficulty.value] = {
            "display_name": models.DifficultyLevel.get_display_name(difficulty),
            "color_class": models.DifficultyLevel.get_color_class(difficulty),
            "total": total, "used": used, "available": total - used,
            "usage_percentage": round((used / total * 100) if total > 0 else 0, 1)
        }

    total_questions = db.query(models.Question).count()
    used_questions = db.query(models.Question).filter(models.Question.is_used == True).count()

    return JSONResponse({
        "by_difficulty": stats,
        "overall": {
            "total": total_questions, "used": used_questions,
            "available": total_questions - used_questions,
            "usage_percentage": round((used_questions / total_questions * 100) if total_questions > 0 else 0, 1)
        }
    })


@router.get("/api/questions/recommendations")
async def get_question_recommendations(
        difficulty: Optional[str] = None,
        exclude_used: bool = True,
        limit: int = 10,
        db: Session = Depends(get_db)
):
    query = db.query(models.Question)
    if exclude_used:
        query = query.filter(models.Question.is_used == False)
    if difficulty:
        try:
            difficulty_enum = models.DifficultyLevel(difficulty)
            query = query.filter(models.Question.difficulty == difficulty_enum)
        except ValueError:
            pass

    questions = query.order_by(func.random()).limit(limit).all()
    return JSONResponse({
        "questions": [
            {
                "id": q.id, "number": q.number, "text": q.text,
                "difficulty": q.difficulty_display, "difficulty_color": q.difficulty_color,
                "notes": q.notes, "is_used": q.is_used
            }
            for q in questions
        ],
        "total_found": len(questions)
    })


@router.get("/api/questions/search")
async def search_questions(
        q: str = "",
        difficulty: Optional[str] = None,
        used_status: Optional[str] = None,
        limit: int = 50,
        db: Session = Depends(get_db)
):
    query = db.query(models.Question)
    if q:
        search_term = f"%{q}%"
        query = query.filter(
            (models.Question.text.like(search_term)) |
            (models.Question.notes.like(search_term))
        )
    if difficulty:
        try:
            difficulty_enum = models.DifficultyLevel(difficulty)
            query = query.filter(models.Question.difficulty == difficulty_enum)
        except ValueError:
            pass
    if used_status == "used":
        query = query.filter(models.Question.is_used == True)
    elif used_status == "available":
        query = query.filter(models.Question.is_used == False)

    questions = query.order_by(models.Question.number).limit(limit).all()
    return JSONResponse({
        "questions": [
            {
                "id": q.id, "number": q.number,
                "text": q.text[:150] + "..." if len(q.text) > 150 else q.text,
                "difficulty": q.difficulty_display, "difficulty_color": q.difficulty_color,
                "notes": q.notes, "is_used": q.is_used,
                "created_at": q.created_at.isoformat() if q.created_at else None
            }
            for q in questions
        ],
        "total_found": len(questions),
        "search_query": q,
        "filters": {"difficulty": difficulty, "used_status": used_status}
    })