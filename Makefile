.PHONY: install dev lint format typecheck test smoke clean

install:
	uv sync

dev:
	uv sync --extra dev

lint:
	uv run ruff check src/ tests/

format:
	uv run black src/ tests/

typecheck:
	uv run mypy src/

test:
	mkdir -p tests/logs
	PYTHONPATH=src uv run pytest tests/unit/ -v --tb=short

smoke:
	mkdir -p tests/logs
	PYTHONPATH=src uv run pytest tests/smoke/ -v --tb=short

ci: lint typecheck test

ingest:
	PYTHONPATH=src uv run python src/heart_speaks/ingest.py

eval:
	mkdir -p logs
	PYTHONPATH=src uv run python tests/eval/run_eval.py

run-api:
	PYTHONPATH=src uv run uvicorn heart_speaks.api:app --reload --port 8000

clean:
	rm -rf .venv __pycache__ .mypy_cache .ruff_cache .pytest_cache
