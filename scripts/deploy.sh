#!/bin/bash
# Quick deployment script for AURA Research Agent

echo "AURA Research Agent - Docker Deployment"
echo "========================================"

# Check if .env.production exists
if [ ! -f .env.production ]; then
    echo "ERROR: .env.production not found"
    echo "Please create .env.production from .env.example"
    exit 1
fi

# Build images
echo "Building Docker images..."
docker-compose build

# Start services
echo "Starting services..."
docker-compose up -d

# Wait for services to be healthy
echo "Waiting for services to start..."
sleep 10

# Check health
echo "Checking backend health..."
curl -f http://localhost:8000/health || echo "Backend not ready yet"

echo ""
echo "Deployment complete!"
echo "Frontend: http://localhost:3000"
echo "Backend API: http://localhost:8000"
echo "Health check: http://localhost:8000/health"
echo ""
echo "To view logs: docker-compose logs -f"
echo "To stop: docker-compose down"
