.PHONY: help up down restart logs ps build rebuild dev install test lint clean up-home down-home logs-home up-remote down-remote logs-remote

BACKEND_DIR := backend

help:
	@echo "up        - start dev stack (alias for 'make dev', docker compose up -d; override auto-loads)"
	@echo "down      - stop dev stack (alias for 'make dev' stack)"
	@echo "restart   - restart dev stack (alias for 'make dev' stack)"
	@echo "logs      - follow dev stack backend container logs"
	@echo "ps        - show container status"
	@echo "build     - build dev stack docker images (override auto-loads)"
	@echo "rebuild   - build --no-cache + up (dev stack)"
	@echo "dev       - start dev stack with hot reload (docker compose up, base + override)"
	@echo "install   - uv sync (with dev deps) in backend/"
	@echo "test      - run pytest in backend/"
	@echo "clean     - remove backend .venv and caches"
	@echo "up-home     - start LAN self-hosted stack (backend+frontend+caddy on :8080)"
	@echo "down-home   - stop LAN self-hosted stack"
	@echo "logs-home   - follow logs for the LAN self-hosted stack"
	@echo "up-remote   - start remote-server stack (backend:8011, frontend:3010, no caddy)"
	@echo "down-remote - stop remote-server stack"
	@echo "logs-remote - follow logs for the remote-server stack"

up:
	docker compose up -d

down:
	docker compose down

restart: down up

logs:
	docker compose logs -f backend

ps:
	docker compose ps

build:
	docker compose build

rebuild:
	docker compose build --no-cache
	docker compose up -d

dev:
	docker compose up

install:
	cd $(BACKEND_DIR) && uv sync

test:
	cd $(BACKEND_DIR) && uv run pytest

clean:
	rm -rf $(BACKEND_DIR)/.venv $(BACKEND_DIR)/.pytest_cache

up-home:
	docker compose -f docker-compose.yml -f docker-compose.prod-home.yml up -d

down-home:
	docker compose -f docker-compose.yml -f docker-compose.prod-home.yml down

logs-home:
	docker compose -f docker-compose.yml -f docker-compose.prod-home.yml logs -f

up-remote:
	docker compose -f docker-compose.yml -f docker-compose.prod-remote.yml up -d

down-remote:
	docker compose -f docker-compose.yml -f docker-compose.prod-remote.yml down

logs-remote:
	docker compose -f docker-compose.yml -f docker-compose.prod-remote.yml logs -f
