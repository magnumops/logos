# Используем официальный slim-образ Python
FROM python:3.9-slim-bullseye

# Устанавливаем wget, необходимый для healthcheck
RUN apt-get update && apt-get install -y wget && rm -rf /var/lib/apt/lists/*

# Устанавливаем рабочую директорию
WORKDIR /app

# Копируем файл зависимостей и устанавливаем их
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем остальной код приложения
COPY . .

# Открываем порт
EXPOSE 8000

# РЕШЕНИЕ: Явно указываем uvicorn слушать все интерфейсы,
# что решает потенциальные проблемы с IPv4/IPv6 внутри Docker.
CMD ["uvicorn", "logos_api.main:app", "--host", "0.0.0.0", "--port", "8000"]
