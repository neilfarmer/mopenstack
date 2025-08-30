.PHONY: help install dev-install clean test lint format type-check build run bootstrap docker-build docker-run docker-stop docker-clean all-checks integration-test

# Default target
help: ## Show this help message
	@echo "MockOpenStack - Local OpenStack API Mock Environment"
	@echo ""
	@echo "Available targets:"
	@awk 'BEGIN {FS = ":.*##"} /^[a-zA-Z_-]+:.*##/ { printf "  %-20s %s\n", $$1, $$2 }' $(MAKEFILE_LIST)

# Development setup
install: ## Install dependencies
	poetry install

dev-install: ## Install with development dependencies
	poetry install --with dev

clean: ## Clean up temporary files and caches
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	rm -rf .pytest_cache
	rm -rf .coverage
	rm -rf dist/
	rm -rf build/
	rm -f mopenstack.db*

# Code quality
lint: ## Run linting
	poetry run flake8 mopenstack/ tests/

format: ## Format code with black and isort
	poetry run black mopenstack/ tests/
	poetry run isort mopenstack/ tests/

type-check: ## Run type checking
	poetry run mypy mopenstack/

all-checks: lint type-check ## Run all code quality checks

# Testing
test: ## Run tests
	poetry run pytest

test-verbose: ## Run tests with verbose output
	poetry run pytest -v

test-coverage: ## Run tests with coverage report
	poetry run pytest --cov=mopenstack --cov-report=html --cov-report=term-missing

integration-test: ## Run integration tests (requires running server)
	@echo "Running integration tests..."
	poetry run pytest tests/integration/ -v

# Application management
bootstrap: ## Bootstrap the database with default data
	poetry run mopenstack-bootstrap

run: ## Run the development server
	poetry run mopenstack

run-debug: ## Run server with debug logging
	DEBUG=true poetry run mopenstack

# Docker operations
docker-build: ## Build Docker image
	docker-compose build

docker-run: ## Run with Docker Compose
	docker-compose up -d

docker-stop: ## Stop Docker containers
	docker-compose down

docker-clean: ## Clean Docker containers and images
	docker-compose down -v --rmi all

docker-logs: ## Show Docker logs
	docker-compose logs -f

# Development workflow
dev-setup: clean install bootstrap ## Complete development setup
	@echo "Development environment ready!"
	@echo "Run 'make run' to start the server"

dev-reset: clean dev-setup ## Reset development environment
	@echo "Development environment reset complete!"

# Build and package
build: ## Build the package
	poetry build

# Quick start for new developers
quick-start: dev-setup ## Quick start for new developers
	@echo ""
	@echo "🚀 MockOpenStack is ready!"
	@echo ""
	@echo "Quick commands:"
	@echo "  make run          - Start the development server"
	@echo "  make test         - Run tests"
	@echo "  make docker-run   - Run with Docker"
	@echo ""
	@echo "Default admin credentials:"
	@echo "  Username: admin"
	@echo "  Password: password"
	@echo "  Project: admin"
	@echo ""

# Full validation
validate: all-checks test ## Run full validation suite
	@echo "✅ All validation checks passed!"

# CI/CD targets
ci-install: ## Install dependencies for CI
	poetry install --with dev

ci-test: all-checks test ## Run CI test suite
	@echo "✅ CI tests completed successfully!"

# Health check
health-check: ## Check if the service is running
	@curl -f http://localhost:5000/health > /dev/null 2>&1 && echo "✅ Service is healthy" || echo "❌ Service is not responding"

# Port management
check-port: ## Check what's using port 5000
	@echo "Checking what's using port 5000..."
	@lsof -ti:5000 || echo "Port 5000 is free"

kill-port: ## Kill processes using port 5000
	@echo "Killing processes using port 5000..."
	@lsof -ti:5000 | xargs kill -9 || echo "No processes to kill on port 5000"

run-clean: kill-port run ## Kill port conflicts and run

# Show service endpoints
endpoints: ## Show all service endpoints
	@echo "MockOpenStack Service Endpoints:"
	@echo "  Identity (Keystone):  http://localhost:5000/v3"
	@echo "  Compute (Nova):       http://localhost:8774/v2.1"
	@echo "  Network (Neutron):    http://localhost:9696/v2.0"
	@echo "  Image (Glance):       http://localhost:9292/v2"
	@echo "  Block Storage (Cinder): http://localhost:8776/v3"
	@echo "  Object Storage (Swift): http://localhost:8080/v1"
	@echo "  Load Balancer (Octavia): http://localhost:9876/v2"
	@echo "  DNS (Designate):      http://localhost:9001/v2"
	@echo ""
	@echo "  API Documentation:    http://localhost:5000/docs"
	@echo "  Health Check:         http://localhost:5000/health"