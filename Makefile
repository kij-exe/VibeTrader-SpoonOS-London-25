# VibeTrader Makefile - Simplified Docker Commands

.PHONY: help start stop restart logs build clean status shell-backend shell-frontend health

# Default target
help:
	@echo "🐳 VibeTrader Docker Commands"
	@echo "=============================="
	@echo ""
	@echo "  make start          - Start all services"
	@echo "  make stop           - Stop all services"
	@echo "  make restart        - Restart all services"
	@echo "  make logs           - View all logs (real-time)"
	@echo "  make build          - Rebuild containers"
	@echo "  make clean          - Stop and remove everything"
	@echo "  make status         - Check service status"
	@echo "  make shell-backend  - Open backend shell"
	@echo "  make shell-frontend - Open frontend shell"
	@echo "  make health         - Check backend health"
	@echo ""
	@echo "📚 Documentation: DOCKER_README.md"

# Start all services
start:
	@echo "🚀 Starting VibeTrader..."
	docker-compose up -d
	@echo "✅ Services started!"
	@echo "   Frontend: http://localhost:5173"
	@echo "   Backend:  http://localhost:8000"

# Start with build
start-build:
	@echo "🏗️  Building and starting VibeTrader..."
	docker-compose up -d --build
	@echo "✅ Services started!"

# Stop all services
stop:
	@echo "⏹️  Stopping VibeTrader..."
	docker-compose down
	@echo "✅ Services stopped!"

# Restart all services
restart:
	@echo "🔄 Restarting VibeTrader..."
	docker-compose restart
	@echo "✅ Services restarted!"

# View logs in real-time
logs:
	docker-compose logs -f

# View backend logs only
logs-backend:
	docker-compose logs -f backend

# View frontend logs only
logs-frontend:
	docker-compose logs -f frontend

# Build containers
build:
	@echo "🏗️  Building containers..."
	docker-compose build
	@echo "✅ Build complete!"

# Build without cache
build-clean:
	@echo "🏗️  Building containers (no cache)..."
	docker-compose build --no-cache
	@echo "✅ Build complete!"

# Stop and remove everything
clean:
	@echo "🧹 Cleaning up..."
	docker-compose down -v
	@echo "✅ Cleanup complete!"

# Check service status
status:
	@echo "📊 Service Status:"
	@docker-compose ps

# Open backend shell
shell-backend:
	@echo "🐚 Opening backend shell..."
	docker-compose exec backend /bin/bash

# Open frontend shell
shell-frontend:
	@echo "🐚 Opening frontend shell..."
	docker-compose exec frontend /bin/sh

# Check backend health
health:
	@echo "🏥 Checking backend health..."
	@curl -s http://localhost:8000/health | python -m json.tool || echo "❌ Backend not responding"

# Setup environment
setup:
	@echo "⚙️  Setting up environment..."
	@if [ ! -f backend/.env ]; then \
		cp backend/.env.example backend/.env; \
		echo "✅ Created backend/.env"; \
		echo "⚠️  Please edit backend/.env and add your API keys"; \
	else \
		echo "✅ backend/.env already exists"; \
	fi

# Full reset and start
reset:
	@echo "🔄 Full reset..."
	$(MAKE) clean
	$(MAKE) build-clean
	$(MAKE) start
	@echo "✅ Reset complete!"

# Install (setup + build + start)
install:
	@echo "📦 Installing VibeTrader..."
	$(MAKE) setup
	$(MAKE) build
	$(MAKE) start
	@echo ""
	@echo "✅ Installation complete!"
	@echo "   Frontend: http://localhost:5173"
	@echo "   Backend:  http://localhost:8000"
	@echo ""
	@echo "⚠️  Don't forget to add API keys to backend/.env"
