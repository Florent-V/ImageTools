BACKEND_DIR := backend
DEV_COMP    := docker compose
PROD_COMP   := docker compose -f docker-compose.yml -f docker-compose.prod-remote.yml

# Variables that must be set in .env before starting a stack (see .env.example)
REQUIRED_ENV := OAUTH_ISSUER OAUTH_CLIENT_ID OAUTH_CLIENT_SECRET PUBLIC_ORIGIN

.DEFAULT_GOAL := help
.PHONY: help env-check dev up down restart logs ps build rebuild install test audit clean \
        prod-check prod-build prod-up prod-deploy prod-down prod-restart prod-logs prod-ps

## —— Help ——————————————————————————————————————————————————————————————
help: ## List the commands
	@grep -E '(^[a-zA-Z_-]+:.*?## .*$$)|(^## )' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "\033[32m%-14s\033[0m %s\n", $$1, $$2}' | sed -e 's/\[32m## /\n[33m/'

env-check: ## Check that .env exists and holds every OAuth variable
	@test -f .env || (echo "Missing .env: cp .env.example .env, then fill it (docs/deploiement.md)." && exit 1)
	@set -a; . ./.env; set +a; missing=""; \
	for v in $(REQUIRED_ENV); do eval "val=\$${$$v:-}"; [ -n "$$val" ] || missing="$$missing $$v"; done; \
	if [ -n "$$missing" ]; then echo "Empty in .env:$$missing" && exit 1; fi

## —— Dev (hot reload, http://localhost:FRONTEND_PORT) ———————————————————
dev: env-check ## Start the dev stack in the foreground (Ctrl+C to stop)
	@$(DEV_COMP) up --build

up: env-check ## Start the dev stack in the background
	@$(DEV_COMP) up -d --build

down: ## Stop the dev stack
	@$(DEV_COMP) down

restart: down up ## Restart the dev stack

logs: ## Follow the dev stack logs
	@$(DEV_COMP) logs -f

ps: ## Dev containers status
	@$(DEV_COMP) ps

build: ## Build the dev images
	@$(DEV_COMP) build

rebuild: ## Rebuild the dev images from scratch, then start
	@$(DEV_COMP) build --no-cache
	@$(DEV_COMP) up -d

install: ## uv sync (with dev deps) in backend/
	cd $(BACKEND_DIR) && uv sync

test: ## Run the backend tests
	cd $(BACKEND_DIR) && uv run pytest

audit: ## pnpm audit (high+ severity) in frontend/
	cd frontend && pnpm audit --audit-level=high

clean: ## Remove backend .venv and caches
	rm -rf $(BACKEND_DIR)/.venv $(BACKEND_DIR)/.pytest_cache

## —— Production (frontend on 127.0.0.1:REMOTE_FRONTEND_PORT, behind Caddy) ——
prod-check: env-check ## Check .env for production (no dev-only values)
	@set -a; . ./.env; set +a; \
	case "$$PUBLIC_ORIGIN" in https://*) ;; *) echo "PUBLIC_ORIGIN must be https:// in production" && exit 1;; esac; \
	case "$$OAUTH_ISSUER" in https://*) ;; *) echo "OAUTH_ISSUER must be https:// in production" && exit 1;; esac; \
	[ "$${APP_ENV:-prod}" = prod ] || (echo "APP_ENV must be prod in production" && exit 1)

prod-build: prod-check ## Build the production images
	@$(PROD_COMP) build --pull

prod-up: prod-check ## Start (or update) production
	@$(PROD_COMP) up -d --wait

prod-deploy: prod-check ## Deploy an update: git pull, build, restart
	@git pull --ff-only
	@$(MAKE) --no-print-directory prod-build prod-up
	@$(PROD_COMP) ps

prod-down: ## Stop production
	@$(PROD_COMP) down

prod-restart: ## Restart production (no rebuild)
	@$(PROD_COMP) restart

prod-logs: ## Follow production logs
	@$(PROD_COMP) logs --tail=200 -f

prod-ps: ## Production containers status
	@$(PROD_COMP) ps
