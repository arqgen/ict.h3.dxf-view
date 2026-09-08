.PHONY: install lint format test dev dev-web build-web phoenix-up phoenix-down phoenix-logs

PORT ?= 8787
HOST ?= 0.0.0.0
VITE_PORT ?= 5173
VITE_API_PORT ?= $(PORT)
PHOENIX_PORT ?= 6006

install:
	uv sync
	npm --prefix web install

lint:
	uv run ruff check src tests

format:
	uv run ruff format src tests
	uv run ruff check --fix src tests

test:
	uv run pytest

dev:
	PORT=$(PORT) HOST=$(HOST) uv run python -m src.main

dev-web:
	VITE_PORT=$(VITE_PORT) VITE_API_PORT=$(VITE_API_PORT) npm --prefix web run dev

build-web:
	npm --prefix web run build

phoenix-up:
	PHOENIX_PORT=$(PHOENIX_PORT) docker compose up -d phoenix

phoenix-down:
	PHOENIX_PORT=$(PHOENIX_PORT) docker compose down

phoenix-logs:
	docker compose logs -f phoenix
