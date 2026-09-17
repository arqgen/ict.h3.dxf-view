SHELL := /bin/bash

.PHONY: install lint format test dev dev-web dev-all build-web phoenix-up phoenix-down phoenix-logs clean

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

dev-all: phoenix-up
	@BACKEND_PID=; WEB_PID=; \
	cleanup() { \
		STATUS=$$1; \
		trap - INT TERM EXIT; \
		if [[ -n "$$BACKEND_PID" ]]; then kill "$$BACKEND_PID" 2>/dev/null || true; fi; \
		if [[ -n "$$WEB_PID" ]]; then kill "$$WEB_PID" 2>/dev/null || true; fi; \
		wait "$$BACKEND_PID" "$$WEB_PID" 2>/dev/null || true; \
		PHOENIX_PORT=$(PHOENIX_PORT) docker compose down; \
		exit $$STATUS; \
	}; \
	trap 'cleanup 0' INT TERM; \
	trap 'cleanup $$?' EXIT; \
	PORT=$(PORT) HOST=$(HOST) COLLECTOR_ENDPOINT=http://localhost:$(PHOENIX_PORT) uv run python -m src.main & \
	BACKEND_PID=$$!; \
	VITE_PORT=$(VITE_PORT) VITE_API_PORT=$(VITE_API_PORT) npm --prefix web run dev & \
	WEB_PID=$$!; \
	wait -n "$$BACKEND_PID" "$$WEB_PID"

build-web:
	npm --prefix web run build

phoenix-up:
	PHOENIX_PORT=$(PHOENIX_PORT) docker compose up -d phoenix

phoenix-down:
	PHOENIX_PORT=$(PHOENIX_PORT) docker compose down

phoenix-logs:
	docker compose logs -f phoenix

clean:
	rm -rf .pytest_cache .ruff_cache .mypy_cache
	find . -type d -name "__pycache__" -prune -exec rm -rf {} +
	find . -type d -name ".ipynb_checkpoints" -prune -exec rm -rf {} +
