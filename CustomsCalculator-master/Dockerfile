# Используем официальный легкий образ Python
FROM python:3.11-slim

# Устанавливаем переменные окружения
# PYTHONDONTWRITEBYTECODE: Запрещает Python писать .pyc файлы
# PYTHONUNBUFFERED: Гарантирует, что логи выводятся в консоль сразу
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

# Устанавливаем рабочую директорию
WORKDIR /app

# Устанавливаем системные зависимости (если нужны для pandas/numpy, хотя binary wheel обычно хватает)
# netcat-openbsd нужен для скрипта ожидания базы данных (опционально, но полезно)
RUN apt-get update && apt-get install -y --no-install-recommends \
    netcat-openbsd \
    && rm -rf /var/lib/apt/lists/*

# Копируем файл зависимостей
COPY requirements.txt .

# Устанавливаем python-зависимости
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Копируем весь проект в контейнер
COPY . .

# Делаем скрипт запуска исполняемым
RUN chmod +x scripts/entrypoint.sh

# Открываем порт
EXPOSE 8000

# Запускаем через entrypoint (чтобы накатить миграции перед стартом)
ENTRYPOINT ["/app/scripts/entrypoint.sh"]