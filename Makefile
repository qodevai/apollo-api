# Makefile for apollo-client - Development tasks
# Prerequisites: uv (https://docs.astral.sh/uv/)

.PHONY: help
help:
	@printf "\nApollo Client Development Commands:\n\n"
	@awk '/^#/{c=substr($$0,3);next}c&&/^[[:alpha:]][[:alnum:]_-]+:/{printf "  \033[36m%-20s\033[0m %s\n", substr($$1,1,index($$1,":")-1),c}1{c=0}' $(MAKEFILE_LIST)
	@printf "\nRun 'make install' to get started!\n\n"

###############
# Setup Tasks #
###############

.PHONY: install
# Install all dependencies (including dev)
install:
	@command -v uv >/dev/null 2>&1 || { echo "uv is required. See https://docs.astral.sh/uv/"; exit 1; }
	uv sync --all-extras

.PHONY: install-hooks
# Install pre-commit hooks
install-hooks:
	@command -v uvx >/dev/null 2>&1 || { echo "uv is required."; exit 1; }
	uvx pre-commit install
	@echo "Pre-commit hooks installed!"

#############
# Testing   #
#############

.PHONY: test
# Run tests with coverage
test:
	uv run pytest --cov=apollo --cov-report=term --cov-report=html

.PHONY: test-fast
# Run tests without coverage
test-fast:
	uv run pytest

#####################
# Code Quality      #
#####################

.PHONY: check
# Run all checks (lint, format, typecheck, typos)
check: lint format-check typecheck typos

.PHONY: lint
# Lint code with ruff
lint:
	uv run ruff check src/ tests/

.PHONY: lint-fix
# Lint and auto-fix issues
lint-fix:
	uv run ruff check --fix src/ tests/

.PHONY: format
# Format code with ruff
format:
	uv run ruff format src/ tests/

.PHONY: format-check
# Check code formatting
format-check:
	uv run ruff format --check src/ tests/

.PHONY: typecheck
# Run type checking with pyright
typecheck:
	uv run pyright src/

.PHONY: typos
# Check for typos
typos:
	@command -v uvx >/dev/null 2>&1 || { echo "uv is required."; exit 1; }
	uvx typos

.PHONY: typos-fix
# Fix typos automatically
typos-fix:
	@command -v uvx >/dev/null 2>&1 || { echo "uv is required."; exit 1; }
	uvx typos --write-changes

##############
# Cleanup    #
##############

.PHONY: clean
# Clean up generated files
clean:
	rm -rf .pytest_cache .ruff_cache .mypy_cache .coverage htmlcov
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
