FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Native libraries required by WeasyPrint.
RUN apt-get update && apt-get install -y --no-install-recommends \
    libglib2.0-0 \
    libpango-1.0-0 \
    libpangoft2-1.0-0 \
    libpangocairo-1.0-0 \
    libharfbuzz-subset0 \
    libcairo2 \
    libgdk-pixbuf-2.0-0 \
    shared-mime-info \
    fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md alembic.ini ./
COPY agentguard_core ./agentguard_core
COPY migrations ./migrations
COPY data ./data
COPY templates ./templates
COPY scripts_seed.py ./

RUN python -m pip install --no-cache-dir .

EXPOSE 10000

CMD ["sh", "-c", "exec uvicorn agentguard_core.api:app --host 0.0.0.0 --port ${PORT:-10000}"]
