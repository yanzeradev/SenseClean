.PHONY: run install test format clean

# Starts the SenseVision server
run:
	poetry run uvicorn app.main:app --reload

install:
	poetry install

test:
	poetry run pytest

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
