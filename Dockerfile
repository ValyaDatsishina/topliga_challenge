# Используем базовый образ Python
FROM python:3.9-slim

# Устанавливаем рабочую директорию
WORKDIR /app

RUN apt-get update \
    && apt-get install -y libpq-dev gcc \
    && apt-get clean

# Копируем файл зависимостей в контейнер
COPY requirements.txt .

CMD [ "python3", "-m venv venv"]
CMD [ "source", "venv/bin/activate"]

# Устанавливаем зависимости
RUN pip install --upgrade pip
RUN pip install -r requirements.txt
# RUN pip install --no-cache-dir -r requirements.txt
# RUN pip install --upgrade -r requirements.txt

# Копируем остальной код приложения в контейнер
COPY . .

# Указываем команду для запуска приложения
CMD ["python", "app.py"]
