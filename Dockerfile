FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app

COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install --no-cache-dir .
COPY alembic.ini ./
COPY migrations ./migrations

RUN useradd --create-home --uid 10001 appuser \
    && mkdir -p /app/.local/db /app/.local/storage /data \
    && chown -R appuser:appuser /app/.local /data
USER appuser
EXPOSE 8000
CMD ["uvicorn", "creator.main:app", "--host", "0.0.0.0", "--port", "8000"]
