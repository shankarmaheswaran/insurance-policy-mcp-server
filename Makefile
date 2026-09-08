.PHONY: help install dev lint format test run clean

help:
	@echo "Insurance Policy MCP Server"
	@echo ""
	@echo "Available commands:"
	@echo "  make install    Install dependencies"
	@echo "  make dev        Install dev dependencies"
	@echo "  make run        Run the MCP server"
	@echo "  make test       Run tests"
	@echo "  make lint       Run linter"
	@echo "  make format     Format code"
	@echo "  make mypy       Type check"
	@echo "  make clean      Clean up generated files"

install:
	pip install -e .

dev:
	pip install -e ".[dev]"

run:
	python -m src.server

test:
	pytest tests/ -v

lint:
	pylint src/ tests/

format:
	black .
	isort .

mypy:
	mypy src/ --strict

clean:
	find . -type f -name '*.pyc' -delete
	find . -type d -name '__pycache__' -delete
	find . -type d -name '*.egg-info' -exec rm -rf {} +
	rm -rf .pytest_cache .mypy_cache .dmypy.json
