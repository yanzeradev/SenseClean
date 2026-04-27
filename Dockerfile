# Usa uma versão leve do Python 3.11
FROM python:3.11-slim

# Instala as dependências do sistema
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libsm6 \
    libxext6 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copia apenas o requirements primeiro para aproveitar o cache do Docker
COPY requirements.txt .

# Instala as dependências do Python usando o cache do BuildKit para o PIP
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install -r requirements.txt

# Copia o restante do código
COPY . .

EXPOSE 8000

# Comando para iniciar o servidor
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]