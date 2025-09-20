# Travel Legal Alert System - Makefile

.PHONY: help build up down logs shell db-shell migrate clean test lint format install dev-up prod-up

# Default target
help:
	@echo "Travel Legal Alert System - Available commands:"
	@echo ""
	@echo "Development Commands:"
	@echo "  make dev-up      - Start development environment"
	@echo "  make install     - Install Python dependencies"
	@echo "  make migrate     - Run database migrations"
	@echo "  make seed        - Seed database with sample data"
	@echo "  make shell       - Access application shell"
	@echo "  make db-shell    - Access database shell"
	@echo ""
	@echo "Production Commands:"
	@echo "  make prod-up     - Start production environment"
	@echo ""
	@echo "Docker Commands:"
	@echo "  make build       - Build Docker images"
	@echo "  make up          - Start all services"
	@echo "  make down        - Stop all services"
	@echo "  make logs        - View logs"
	@echo ""
	@echo "Development Tools:"
	@echo "  make test        - Run tests"
	@echo "  make lint        - Run linting"
	@echo "  make format      - Format code"
	@echo "  make clean       - Clean up containers and volumes"

# Development environment
dev-up:
	@echo "Starting development environment..."
	docker-compose --profile development up -d
	@echo "Services started! API available at http://localhost:8000"
	@echo "PgAdmin available at http://localhost:5050 (admin@example.com / admin)"

# Production environment
prod-up:
	@echo "Starting production environment..."
	docker-compose --profile production up -d
	@echo "Production services started!"

# Install dependencies locally
install:
	@echo "Installing Python dependencies..."
	pip install -r requirements.txt

# Docker commands
build:
	@echo "Building Docker images..."
	docker-compose build

up:
	@echo "Starting services..."
	docker-compose up -d

down:
	@echo "Stopping services..."
	docker-compose down

logs:
	@echo "Showing logs..."
	docker-compose logs -f

# Database operations
migrate:
	@echo "Running database migrations..."
	docker-compose exec app alembic upgrade head

seed:
	@echo "Seeding database with sample data..."
	docker-compose exec app python scripts/seed_database.py

db-shell:
	@echo "Connecting to database..."
	docker-compose exec postgres psql -U postgres -d travel_alerts

# Application shell
shell:
	@echo "Starting application shell..."
	docker-compose exec app /bin/bash

# Testing
test:
	@echo "Running tests..."
	docker-compose exec app pytest

# Code quality
lint:
	@echo "Running linting..."
	docker-compose exec app flake8 app/
	docker-compose exec app mypy app/

format:
	@echo "Formatting code..."
	docker-compose exec app black app/
	docker-compose exec app isort app/

# Cleanup
clean:
	@echo "Cleaning up Docker resources..."
	docker-compose down -v
	docker system prune -f
	docker volume prune -f

# Quick setup for new developers
setup: build dev-up migrate seed
	@echo ""
	@echo "🎉 Setup complete!"
	@echo ""
	@echo "Your Travel Legal Alert System is ready!"
	@echo "API Documentation: http://localhost:8000/docs"
	@echo "Health Check: http://localhost:8000/health"
	@echo "PgAdmin: http://localhost:5050"
	@echo ""
	@echo "Sample data has been loaded with:"
	@echo "  • 20 countries, 5 users, 10 sources"
	@echo "  • 10 sample alerts with various risk levels"
	@echo ""
	@echo "Useful commands:"
	@echo "  make logs        - View application logs"
	@echo "  make shell       - Access application shell"
	@echo "  make test        - Run tests"