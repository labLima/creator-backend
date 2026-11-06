.PHONY: install format format-check lint typecheck test e2e migrate-check dependency-audit secrets security check ci run worker dev/start dev/stop dev/clean dev/logs snapshot-contract

PYTHON ?= $(or $(shell command -v python3 2>/dev/null),$(shell command -v python 2>/dev/null),python)
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
	$(PYTEST) -m "not e2e"

migrate-check:
	$(PYTHON) scripts/check_migrations.py

snapshot-contract:
	$(PYTHON) scripts/snapshot_contract.py

e2e:
	$(PYTEST) -m e2e --no-cov

dependency-audit:
	$(PYTHON) -m pip_audit . \
		--ignore-vuln PYSEC-2026-311 \
		--ignore-vuln PYSEC-2026-3813 \
		--ignore-vuln PYSEC-2026-3814 \
		--ignore-vuln PYSEC-2026-3815

secrets:
	$(PYTHON) scripts/run_gitleaks.py

security: dependency-audit secrets

check: lint format-check typecheck test migrate-check

ci: check security e2e

run:
	uvicorn creator.main:app --host 0.0.0.0 --port 8000 --reload

worker:
	creator-worker all

dev/start: dev-start
dev-start:
	$(PYTHON) scripts/dev_compose.py start

dev/stop: dev-stop
dev-stop:
	$(PYTHON) scripts/dev_compose.py stop

dev/clean: dev-clean
dev-clean:
	$(PYTHON) scripts/dev_compose.py clean "$(CONFIRM)"

dev/logs:
	$(PYTHON) scripts/dev_compose.py logs
