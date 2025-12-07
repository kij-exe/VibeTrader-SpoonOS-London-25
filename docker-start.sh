#!/bin/bash

# VibeTrader Docker Quick Start Script
# This script helps you set up and run VibeTrader with Docker

set -e

echo "🐳 VibeTrader Docker Setup"
echo "=========================="
echo ""

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker first:"
    echo "   https://docs.docker.com/get-docker/"
    exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose is not installed. Please install Docker Compose first:"
    echo "   https://docs.docker.com/compose/install/"
    exit 1
fi

echo "✅ Docker and Docker Compose are installed"
echo ""

# Check if .env file exists
if [ ! -f "backend/.env" ]; then
    echo "⚠️  Environment file not found!"
    echo ""
    echo "Creating backend/.env from template..."
    cp backend/.env.example backend/.env
    echo ""
    echo "📝 Please edit backend/.env and add your API keys:"
    echo "   - ANTHROPIC_API_KEY"
    echo "   - BINANCE_API_KEY"
    echo "   - BINANCE_API_SECRET"
    echo ""
    read -p "Press Enter after you've added your API keys..." 
fi

echo ""
echo "🚀 Starting VibeTrader..."
echo ""

# Build and start containers
docker-compose up --build -d

echo ""
echo "⏳ Waiting for services to start..."
sleep 5

# Check if services are running
if docker-compose ps | grep -q "Up"; then
    echo ""
    echo "✅ VibeTrader is running!"
    echo ""
    echo "📍 Access points:"
    echo "   Frontend:  http://localhost:5173"
    echo "   Backend:   http://localhost:8000"
    echo "   API Docs:  http://localhost:8000/docs"
    echo ""
    echo "📋 Useful commands:"
    echo "   View logs:     docker-compose logs -f"
    echo "   Stop:          docker-compose down"
    echo "   Restart:       docker-compose restart"
    echo ""
    echo "📚 Full documentation: DOCKER_SETUP.md"
    echo ""
    
    # Ask if user wants to see logs
    read -p "View logs now? (y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        docker-compose logs -f
    fi
else
    echo ""
    echo "❌ Services failed to start. Checking logs..."
    echo ""
    docker-compose logs
    exit 1
fi
