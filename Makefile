.DEFAULT_GOAL := check
UV ?= uv

.PHONY: install lint format typecheck test check hooks up down clean

install:
	$(UV) sync --all-extras

lint:
	$(UV) run ruff check .
	$(UV) run ruff format --check .

format:
	$(UV) run ruff check --fix .
	$(UV) run ruff format .

typecheck:
	$(UV) run mypy

test:
	$(UV) run pytest

check: lint typecheck test

hooks:
	$(UV) run pre-commit install

up:
	docker compose up --build

down:
	docker compose down -v

clean:
	rm -rf .pytest_cache .mypy_cache .ruff_cache .coverage htmlcov
