# Базовий образ Python
FROM python:3.9-slim

# Встановлення робочої директорії
WORKDIR /app

# Встановлення залежностей
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копіювання коду проєкту
COPY . .

# Створення директорій для статичних файлів і шаблонів
# (якщо вони не існують в репозиторії)
RUN mkdir -p static templates

# Змінні середовища
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PORT=8000

# Експонування порту
EXPOSE 8000

# Запуск застосунку
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]