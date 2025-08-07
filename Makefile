.PHONY: help install test run clean init-db lint format

help: ## Show this help message
	@echo "Healthcare Provider Registration API - Available Commands:"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: ## Install dependencies
	pip install -r requirements.txt

test: ## Run tests with coverage
	pytest

test-watch: ## Run tests in watch mode
	pytest-watch

run: ## Start the development server
	python run.py

run-prod: ## Start the production server
	uvicorn app.main:app --host 0.0.0.0 --port 8000

init-db: ## Initialize database and create sample data
	python scripts/init_db.py

clean: ## Clean up temporary files
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	rm -rf .pytest_cache
	rm -rf htmlcov
	rm -rf .coverage

lint: ## Run linting checks
	flake8 app tests
	black --check app tests
	isort --check-only app tests

format: ## Format code with black and isort
	black app tests
	isort app tests

migrate: ## Run database migrations
	alembic upgrade head

migrate-create: ## Create a new migration
	@read -p "Enter migration message: " message; \
	alembic revision --autogenerate -m "$$message"

docker-build: ## Build Docker image
	docker build -t healthcare-provider-api .

docker-run: ## Run Docker container
	docker run -p 8000:8000 healthcare-provider-api

setup: install init-db ## Complete setup (install + init-db)
	@echo "✅ Setup completed! Run 'make run' to start the server." 