FROM python:3.11-slim

WORKDIR /app

# Установка системных зависимостей
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Копирование зависимостей
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копирование проекта
COPY . .

# Создание пользователя для безопасности
RUN useradd -m -u 1000 django && chown -R django:django /app
USER django

# Порт приложения
EXPOSE 8000

# Команда запуска
CMD ["gunicorn", "network_project.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3"]