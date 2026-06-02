.PHONY: help setup dev stop test migrate seed clean

help:
	@echo "Available commands:"
	@echo "  make setup   - First-time setup (build + start + seed)"
	@echo "  make dev     - Start all services"
	@echo "  make stop    - Stop all services"
	@echo "  make test    - Run tests"
	@echo "  make migrate - Run DB migrations"
	@echo "  make seed    - Seed demo data"
	@echo "  make clean   - Remove containers and volumes"
	@echo "  make logs    - Tail API logs"
	@echo "  make shell   - Shell into API container"

setup:
	@cp -n backend/.env.example backend/.env 2>/dev/null || true
	@docker compose up -d --build
	@echo "Waiting for services to start..."
	@sleep 20
	@docker compose exec api python seed.py
	@echo ""
	@echo "✅ Setup complete!"
	@echo "   App:      http://localhost"
	@echo "   API Docs: http://localhost:8000/api/docs"
	@echo "   Farmer:   9000000001 / farmer123"
	@echo "   Buyer:    9000000002 / buyer123"

dev:
	docker compose up --build

stop:
	docker compose down

test:
	docker compose exec api pytest app/tests/ -v --tb=short

migrate:
	docker compose exec api alembic upgrade head

seed:
	docker compose exec api python seed.py

logs:
	docker compose logs api -f

shell:
	docker compose exec api bash

shell-db:
	docker compose exec postgres psql -U agriuser -d agridb

clean:
	docker compose down -v --rmi local
