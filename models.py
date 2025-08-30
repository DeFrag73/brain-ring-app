from sqlalchemy import Column, Integer, String, Float, Boolean, Text, DateTime, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

# Базовий клас для всіх моделей
Base = declarative_base()


class Question(Base):
    """Модель для питань брейн-рингу"""
    __tablename__ = "questions"

    id = Column(Integer, primary_key=True, index=True)
    number = Column(Integer, nullable=False)  # Номер питання
    text = Column(Text, nullable=False)  # Текст питання
    notes = Column(Text, default="")  # Нотатки адміністратора
    is_used = Column(Boolean, default=False)  # Чи було використане питання
    created_at = Column(DateTime, default=datetime.utcnow)


class Team(Base):
    """Модель для команд"""
    __tablename__ = "teams"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)  # Назва команди
    members = Column(Text, default="")  # Склад команди (через кому)
    captain = Column(String(100), default="")  # Капітан команди
    created_at = Column(DateTime, default=datetime.utcnow)

    # Зв'язки з результатами ігор
    team1_games = relationship("GameResult", foreign_keys="GameResult.team1_id", back_populates="team1")
    team2_games = relationship("GameResult", foreign_keys="GameResult.team2_id", back_populates="team2")
    won_games = relationship("GameResult", foreign_keys="GameResult.winner_id", back_populates="winner")


class GameResult(Base):
    """Модель для результатів ігор"""
    __tablename__ = "game_results"

    id = Column(Integer, primary_key=True, index=True)
    team1_id = Column(Integer, ForeignKey("teams.id"), nullable=False)
    team2_id = Column(Integer, ForeignKey("teams.id"), nullable=False)
    team1_score = Column(Float, default=0)  # Рахунок першої команди
    team2_score = Column(Float, default=0)  # Рахунок другої команди
    winner_id = Column(Integer, ForeignKey("teams.id"), nullable=True)  # ID переможця (може бути нічия)
    played_at = Column(DateTime, default=datetime.utcnow)

    # Зв'язки з командами
    team1 = relationship("Team", foreign_keys=[team1_id], back_populates="team1_games")
    team2 = relationship("Team", foreign_keys=[team2_id], back_populates="team2_games")
    winner = relationship("Team", foreign_keys=[winner_id], back_populates="won_games")


class CurrentGame(Base):
    """Модель для поточної гри (що відображається на екрані)"""
    __tablename__ = "current_game"

    id = Column(Integer, primary_key=True, index=True)
    team1_id = Column(Integer, ForeignKey("teams.id"), nullable=True)
    team2_id = Column(Integer, ForeignKey("teams.id"), nullable=True)
    team1_score = Column(Float, default=0)  # Поточний рахунок першої команди
    team2_score = Column(Float, default=0)  # Поточний рахунок другої команди
    current_question_id = Column(Integer, ForeignKey("questions.id"), nullable=True)
    show_question = Column(Boolean, default=False)  # Чи показувати питання на екрані
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Зв'язки
    team1 = relationship("Team", foreign_keys=[team1_id])
    team2 = relationship("Team", foreign_keys=[team2_id])
    current_question = relationship("Question", foreign_keys=[current_question_id])


class Settings(Base):
    """Модель для налаштувань додатку"""
    __tablename__ = "settings"

    id = Column(Integer, primary_key=True, index=True)
    key = Column(String(50), unique=True, nullable=False)
    value = Column(String(200), nullable=False)
    description = Column(Text, default="")

    # Приклади налаштувань:
    # - display_theme: "dark" або "light"
    # - default_points: "1" (скільки балів за правильну відповідь)
    # - round_time: "60" (час на відповідь в секундах)
    # - tournament_name: "Брейн-ринг 2025"