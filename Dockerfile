# Usa uma versão leve do Python 3.11
FROM python:3.11-slim

# Instala as dependências do sistema necessárias para o OpenCV e leitura de vídeos (FFmpeg)
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libsm6 \
    libxext6 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Instala o gerenciador de pacotes Poetry
RUN pip install poetry

# Copia os arquivos de dependência primeiro (para aproveitar o cache do Docker)
COPY pyproject.toml poetry.lock* ./

# Instala as bibliotecas do Python sem criar ambiente virtual (o container já é isolado)
RUN poetry config virtualenvs.create false \
    && poetry install --no-root --no-interaction --no-ansi

# Copia o restante do código do backend, incluindo a pasta app e o modelo IA
COPY . .

EXPOSE 8000

# Comando para iniciar o servidor do FastAPI
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]