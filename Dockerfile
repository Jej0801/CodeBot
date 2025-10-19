FROM python:3.11-slim

WORKDIR /app

# system deps for psycopg2 & building wheels
RUN apt-get update && apt-get install -y build-essential libpq-dev gcc --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["sh", "-c", "alembic upgrade head && python scripts/seed_data.py && uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"]
