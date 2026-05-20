FROM python:3.13-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*
RUN pip install poetry

COPY pyproject.toml poetry.lock* ./
RUN poetry config virtualenvs.create false && poetry install --only main --no-root --no-interaction --no-ansi

COPY . .

EXPOSE 8000

CMD ["sh", "-c", "poetry run uvicorn app.main:app --host 0.0.0.0 --port ${API_PORT}"]