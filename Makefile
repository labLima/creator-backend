.PHONY: install format format-check lint typecheck test dependency-audit secrets security check run worker

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

dependency-audit:
	pip-audit \
		--ignore-vuln PYSEC-2026-311 \
		--ignore-vuln PYSEC-2026-3813 \
		--ignore-vuln PYSEC-2026-3814 \
		--ignore-vuln PYSEC-2026-3815

secrets:
	gitleaks detect --source . --no-banner --redact --config .gitleaks.toml

security: dependency-audit secrets

check: lint format-check typecheck test

run:
	uvicorn creator.main:app --host 0.0.0.0 --port 8000 --reload

worker:
	creator-worker image-generation
