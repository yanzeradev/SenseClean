FROM python:3.11-slim

RUN apt-get update && apt-get install -y ffmpeg libsm6 libxext6 && rm -rf /var/lib/apt/lists/*
    
WORKDIR /app

# Instala o poetry
RUN pip install poetry

# Copia apenas os arquivos de dependências primeiro (otimiza cache)
COPY pyproject.toml poetry.lock* ./

# Instala dependências (com cache do BuildKit)
RUN --mount=type=cache,target=/root/.cache/pip \
    --mount=type=cache,target=/root/.cache/poetry \
    poetry config virtualenvs.create false \
    && poetry install --no-root --no-interaction --no-ansi

# O COPY . . é mantido para builds de produção, 
# mas no desenvolvimento ele será sobrescrito pelo volume do compose.
COPY . .

EXPOSE 8000
# Comando padrão (será sobrescrito pelo --reload do compose no dev)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]