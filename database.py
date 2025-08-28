from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os

# Налаштування для різних баз даних
# За замовчуванням використовується SQLite для простоти
# Для PostgreSQL розкоментуйте відповідний рядок

# SQLite (локальна база даних)
DATABASE_URL = "sqlite:///./brainring.db"

# PostgreSQL (для production)
# DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:password@localhost/brainring")

# MySQL (альтернативний варіант)
# DATABASE_URL = os.getenv("DATABASE_URL", "mysql+pymysql://user:password@localhost/brainring")

# Створення підключення до бази даних
if DATABASE_URL.startswith("sqlite"):
    # Для SQLite додаємо параметр check_same_thread=False
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False},
        echo=False  # Встановіть True для відображення SQL запитів в консолі
    )
else:
    # Для PostgreSQL та MySQL
    engine = create_engine(
        DATABASE_URL,
        echo=False
    )

# Створення фабрики сесій
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    """
    Функція для отримання сесії бази даних
    Використовується як залежність в FastAPI
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_database():
    """
    Функція для ініціалізації бази даних
    Створює таблиці якщо вони не існують
    """
    from models import Base
    Base.metadata.create_all(bind=engine)
    print("База даних ініціалізована!")


def reset_database():
    """
    УВАГА: Ця функція видаляє всі дані!
    Використовуйте тільки для тестування
    """
    from models import Base
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    print("База даних очищена та створена заново!")


def add_sample_data():
    """
    Функція для додавання тестових даних
    Корисно для першого запуску
    """
    from models import Question, Team, Settings

    db = SessionLocal()

    try:
        # Перевіряємо чи є вже дані
        if db.query(Question).count() > 0:
            print("Дані вже існують в базі")
            return

        # Додаємо приклади питань
        sample_questions = [
            {
                "number": 1,
                "text": "Яка столиця України?",
                "notes": "Легке питання"
            },
            {
                "number": 2,
                "text": "Хто написав роман 'Кобзар'?",
                "notes": "Література"
            },
            {
                "number": 3,
                "text": "Скільки планет в Сонячній системі?",
                "notes": "Астрономія"
            }
        ]

        for q_data in sample_questions:
            question = Question(**q_data)
            db.add(question)

        # Додаємо приклади команд
        sample_teams = [
            {
                "name": "Знавці",
                "members": "Олександр, Марія, Петро",
                "captain": "Олександр"
            },
            {
                "name": "Мудреці",
                "members": "Анна, Дмитро, Ольга",
                "captain": "Анна"
            },
            {
                "name": "Ерудити",
                "members": "Василь, Катерина, Ігор",
                "captain": "Василь"
            }
        ]

        for t_data in sample_teams:
            team = Team(**t_data)
            db.add(team)

        # Додаємо базові налаштування
        default_settings = [
            {
                "key": "tournament_name",
                "value": "Брейн-ринг 2025",
                "description": "Назва турніру"
            },
            {
                "key": "default_points",
                "value": "1",
                "description": "Базова кількість балів за правильну відповідь"
            },
            {
                "key": "display_theme",
                "value": "dark",
                "description": "Тема оформлення екрану глядачів"
            }
        ]

        for s_data in default_settings:
            setting = Settings(**s_data)
            db.add(setting)

        db.commit()
        print("Тестові дані додано!")

    except Exception as e:
        print(f"Помилка при додаванні тестових даних: {e}")
        db.rollback()
    finally:
        db.close()


# Функція для міграції на PostgreSQL
def migrate_to_postgresql():
    """
    Функція для міграції з SQLite на PostgreSQL
    Використовуйте коли захочете перейти на production базу
    """
    # Цей код потрібно буде адаптувати під ваші потреби
    pass


if __name__ == "__main__":
    # При прямому запуску файлу ініціалізуємо базу та додаємо тестові дані
    init_database()
    add_sample_data()