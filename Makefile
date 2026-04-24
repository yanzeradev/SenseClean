.PHONY: run stop build logs dev-back dev-front clean

# 🚀 COMANDOS DO SISTEMA EMPACOTADO (PRODUÇÃO / USO NORMAL)

run:
	@echo "Ligando o SenseClean..."
	docker compose up -d

stop:
	@echo "Desligando o SenseClean..."
	docker compose down

build:
	@echo "Reconstruindo e ligando o SenseClean..."
	docker compose up -d --build

logs:
	@echo "Lendo logs do sistema (Pressione Ctrl+C para sair)..."
	docker compose logs -f

# 💻 COMANDOS DE DESENVOLVIMENTO (Para quando você for programar/alterar código)

dev-back:
	@echo "Iniciando Backend em Modo Dev..."
	docker compose up -d db go2rtc
	poetry run uvicorn app.main:app --reload

dev-front:
	@echo "Iniciando Frontend em Modo Dev..."
	cd frontend && npm run dev

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +

clean-docker:
	docker system prune -f