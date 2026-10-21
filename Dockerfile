FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY pyproject.toml README.md alembic.ini ./
COPY agentguard_core ./agentguard_core
COPY migrations ./migrations
COPY data ./data
COPY scripts_seed.py ./

RUN python -m pip install --no-cache-dir .

EXPOSE 8000

CMD ["uvicorn", "agentguard_core.api:app", "--host", "0.0.0.0", "--port", "8000"]
