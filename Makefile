.DEFAULT_GOAL := check
UV ?= uv
LOCAL_DSN ?= postgresql+psycopg://trading:trading@localhost:5433/trading

.PHONY: install lint format typecheck test test-integration check hooks \
        up up-db down migrate cycle clean

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

# Integration tests skip themselves unless TEST_DATABASE_URL is set, so this
# target is the one that runs everything.
test:
	$(UV) run pytest

test-integration: up-db
	TEST_DATABASE_URL=$(LOCAL_DSN) $(UV) run pytest

check: lint typecheck test

hooks:
	$(UV) run pre-commit install

up-db:
	docker compose up -d --wait postgres

migrate: up-db
	BOT_DATABASE_URL=$(LOCAL_DSN) $(UV) run alembic upgrade head

# One trading cycle in containers, the way the Container Apps Job will run it.
up:
	docker compose up --build --abort-on-container-exit bot

cycle: migrate
	BOT_DATABASE_URL=$(LOCAL_DSN) $(UV) run python -m trading_bot

down:
	docker compose down -v

clean:
	rm -rf .pytest_cache .mypy_cache .ruff_cache .coverage htmlcov
