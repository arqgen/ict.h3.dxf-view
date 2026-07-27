.PHONY: install lint format test dev dev-web build-web

PORT ?= 8787
HOST ?= 0.0.0.0
VITE_PORT ?= 5173
VITE_API_PORT ?= $(PORT)

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
