.PHONY: help up down build logs seed test lint format clean

# Default target
help:
	@echo ""
	@echo "Enterprise Procurement Copilot — Developer Commands"
	@echo "──────────────────────────────────────────────────────"
	@echo "  make up        Start all services (Docker Compose)"
	@echo "  make down      Stop all services"
	@echo "  make build     Rebuild Docker images"
	@echo "  make logs      Tail backend logs"
	@echo "  make seed      Seed the database with sample data"
	@echo "  make test      Run backend tests"
	@echo "  make lint      Run Ruff linter"
	@echo "  make format    Run Ruff formatter"
	@echo "  make clean     Remove all containers, volumes, and cache"
	@echo ""

up:
	docker compose up -d
	@echo "Services running:"
	@echo "  Backend  → http://localhost:8000"
	@echo "  Frontend → http://localhost:5173"
	@echo "  API docs → http://localhost:8000/docs"

down:
	docker compose down

build:
	docker compose build --no-cache

logs:
	docker compose logs -f backend

seed:
	docker compose exec backend python -m app.db.seed

test:
	docker compose exec backend pytest tests/ -v --tb=short

lint:
	docker compose exec backend ruff check app/ tests/

format:
	docker compose exec backend ruff format app/ tests/

# Local dev without Docker (requires local postgres + chromadb or env overrides)
install:
	cd backend && pip install -r requirements.txt
	cd frontend && npm install

dev-backend:
	cd backend && uvicorn app.main:app --reload --port 8000

dev-frontend:
	cd frontend && npm run dev

clean:
	docker compose down -v --remove-orphans
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete 2>/dev/null || true
