FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    DATABASE_PATH=/app/data/leads.sqlite3

WORKDIR /app

RUN addgroup --system bot \
    && adduser --system --ingroup bot --home /app bot \
    && mkdir -p /app/data \
    && chown -R bot:bot /app

COPY requirements.txt ./
RUN python -m pip install --no-cache-dir -r requirements.txt

COPY --chown=bot:bot src ./src

USER bot

CMD ["python", "-m", "src.bot"]
