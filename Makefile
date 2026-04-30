# APTRANSCO SFRA platform — top-level developer entry points.
# All targets are wrappers around uv-managed Python or shell scripts so the
# behaviour is reproducible on a fresh substation laptop.

PY ?= uv run

.PHONY: help install setup-external sync lint format typecheck test analyse \
        validate-catalogue clean clean-data dev backend frontend

help:
	@echo "APTRANSCO SFRA platform — make targets"
	@echo ""
	@echo "  make install            Install Python deps via uv (creates .venv)"
	@echo "  make setup-external     Clone read-only external/SFRA dependency"
	@echo "  make sync               install + setup-external + pre-commit install"
	@echo ""
	@echo "  make lint               ruff + black --check"
	@echo "  make format             ruff --fix + black"
	@echo "  make typecheck          mypy on src/sfra_full"
	@echo "  make test               pytest with coverage"
	@echo "  make validate-catalogue Verify IEEE C57.149 combination counts"
	@echo ""
	@echo "  make analyse FIXTURE=<path>"
	@echo "                          Phase 0 gate: run a one-shot analysis on a CSV"
	@echo ""
	@echo "  make dev                uvicorn --reload (Phase 2+ once API exists)"
	@echo "  make clean              rm caches and build artefacts"
	@echo "  make clean-data         WIPE data/transformers/ — destructive, asks"

install:
	uv sync --extra dev

setup-external:
	bash scripts/setup_external.sh

sync: install setup-external
	$(PY) pre-commit install

lint:
	$(PY) ruff check src tests scripts
	$(PY) black --check src tests scripts

format:
	$(PY) ruff check --fix src tests scripts
	$(PY) black src tests scripts

typecheck:
	$(PY) mypy src/sfra_full

test:
	$(PY) pytest

validate-catalogue:
	$(PY) python scripts/validate_catalogue.py

# Phase 0 gate from spec §10.
# Example: make analyse FIXTURE=tests/fixtures/synthetic/good_vs_good.csv
analyse:
ifndef FIXTURE
	@echo "Usage: make analyse FIXTURE=<path-to-csv>"; exit 1
endif
	$(PY) python -m sfra_full.cli analyse "$(FIXTURE)"

dev:
	$(PY) uvicorn sfra_full.api.app:app --reload --port 8000

clean:
	rm -rf .pytest_cache .mypy_cache .ruff_cache .coverage htmlcov build dist
	find . -type d -name __pycache__ -prune -exec rm -rf {} +

# Destructive — never silently invoked.
clean-data:
	@read -p "About to DELETE all transformer trace data under data/transformers/. Continue? [y/N] " yn; \
	if [ "$$yn" = "y" ] || [ "$$yn" = "Y" ]; then \
	    rm -rf data/transformers/* data/*.db data/*.db-journal; \
	    echo "data/ wiped."; \
	else \
	    echo "Aborted."; \
	fi
