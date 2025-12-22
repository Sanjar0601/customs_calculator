#!/bin/bash
set -e

# Функция для ожидания доступности порта БД
wait_for_db() {
    echo "Waiting for postgres..."
    while ! nc -z $POSTGRES_HOST $POSTGRES_PORT; do
      sleep 0.1
    done
    echo "PostgreSQL started"
}

# Ждем базу данных
wait_for_db

# 1. Запускаем миграции Alembic
echo "Running migrations..."
alembic upgrade head

# 2. Запускаем скрипт заполнения базы данных
# Он сам проверит, пустая база или нет
echo "Checking/Initializing database data..."
python scripts/init_db.py

# 3. Запускаем приложение
echo "Starting FastAPI server..."
exec uvicorn main:app --host 0.0.0.0 --port 8000 --reload