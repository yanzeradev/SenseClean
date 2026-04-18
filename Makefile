.PHONY: run install test format clean

# Starts the SenseVision server
run-back:
	docker compose up -d go2rtc
	poetry run uvicorn app.main:app --reload
install-back:
	poetry install

test:
	poetry run pytest

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +

run-front:
	cd frontend && npm run dev

install-front:
	cd frontend && npm install