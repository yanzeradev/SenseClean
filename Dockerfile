FROM python:3.11-slim

RUN --mount=type=cache,target=/var/cache/apt \
    apt-get update && apt-get install -y \
    ffmpeg libsm6 libxext6 \
    && rm -rf /var/lib/apt/lists/*
    
WORKDIR /app

# Habilita mounts de cache (precisa do BuildKit)
RUN pip install poetry

COPY pyproject.toml poetry.lock* ./

# Poetry install com cache mounts
RUN --mount=type=cache,target=/root/.cache/pip \
    --mount=type=cache,target=/root/.cache/poetry \
    poetry config virtualenvs.create false \
    && poetry install --no-root --no-interaction --no-ansi

COPY . .

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]