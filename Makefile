.PHONY: install format format-check lint typecheck test e2e dependency-audit secrets security check ci run worker dev/start dev/stop dev/clean dev/logs

PYTHON ?= python
ifeq ($(OS),Windows_NT)
ifneq ($(wildcard .venv313/Scripts/python.exe),)
PYTHON := .venv313/Scripts/python.exe
endif
endif

RUFF := $(PYTHON) -m ruff
MYPY := $(PYTHON) -m mypy
PYTEST := $(PYTHON) -m pytest
RUFF_TARGETS := src tests migrations

install:
	$(PYTHON) -m pip install -e '.[dev]'

format:
	$(RUFF) format $(RUFF_TARGETS)

format-check:
	$(RUFF) format --check $(RUFF_TARGETS)

lint:
	$(RUFF) check $(RUFF_TARGETS)

typecheck:
	$(MYPY) src

test:
	$(PYTEST)

e2e:
	$(PYTEST) -m e2e --no-cov

dependency-audit:
	$(PYTHON) -m pip_audit \
		--ignore-vuln PYSEC-2026-311 \
		--ignore-vuln PYSEC-2026-3813 \
		--ignore-vuln PYSEC-2026-3814 \
		--ignore-vuln PYSEC-2026-3815

secrets:
	gitleaks detect --source . --no-banner --redact --config .gitleaks.toml

security: dependency-audit secrets

check: lint format-check typecheck test

ci: check security e2e

run:
	uvicorn creator.main:app --host 0.0.0.0 --port 8000 --reload

worker:
	creator-worker all

dev/start: dev-start
dev-start:
	@if [ ! -f .env ]; then cp .env.example .env; fi
	@if ! grep -Eq '^AUTH_JWT_SECRET=.+' .env; then \
		secret=$$(python3 -c "import secrets; print(secrets.token_urlsafe(48))"); \
		if grep -q '^AUTH_JWT_SECRET=' .env; then \
			sed -i.bak "s|^AUTH_JWT_SECRET=.*|AUTH_JWT_SECRET=$$secret|" .env; rm -f .env.bak; \
		else \
			echo "AUTH_JWT_SECRET=$$secret" >> .env; \
		fi; \
	fi
	docker compose up -d --build --wait
	docker compose ps

dev/stop: dev-stop
dev-stop:
	AUTH_JWT_SECRET=$${AUTH_JWT_SECRET:-unused-for-stop} docker compose stop
	@echo "Serviços parados; containers e volumes preservados."

dev/clean: dev-clean
dev-clean:
	@if [ "$(CONFIRM)" != "yes" ]; then \
		echo "Operação destrutiva. Execute: make dev/clean CONFIRM=yes"; \
		exit 1; \
	fi
	AUTH_JWT_SECRET=$${AUTH_JWT_SECRET:-unused-for-clean} docker compose down --volumes --remove-orphans --rmi local
	docker image prune -f
	@echo "Containers, volumes e imagens locais do projeto removidos."

dev/logs:
	AUTH_JWT_SECRET=$${AUTH_JWT_SECRET:-unused-for-logs} docker compose logs -f --tail=200
