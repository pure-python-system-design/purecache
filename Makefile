# Run all checks and unit tests (use after each step / before commit)
.PHONY: check test

check:
	uv run ruff check .
	uv run ruff format --check .
	uv run mypy src/
	uv run pytest

test:
	uv run pytest
