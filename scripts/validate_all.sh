#!/bin/bash
#
# AURA Research Agent - Complete Pipeline Validation Script
# =========================================================
#
# This script:
#   1. Checks if Docker is running
#   2. Starts docker-compose containers
#   3. Waits for services to initialize
#   4. Runs complete pipeline validation
#
# Usage: ./validate_all.sh [--stage 1-4] [--verbose]

set -e

echo ""
echo "================================================================================"
echo "  AURA Research Agent - Complete Pipeline Validation"
echo "================================================================================"
echo ""

# Check if Docker is running
echo "[1/4] Checking Docker status..."
if ! docker ps > /dev/null 2>&1; then
    echo ""
    echo "ERROR: Docker is not running!"
    echo ""
    echo "Please start Docker and try again:"
    echo "  - On Mac: Open 'Docker.app' from Applications"
    echo "  - On Linux: Run 'systemctl start docker'"
    echo "  - On Windows: Open 'Docker Desktop' from Start Menu"
    echo "  - Wait 30 seconds for Docker daemon to start"
    echo "  - Then re-run this script"
    echo ""
    exit 1
fi
echo "OK - Docker is running"
echo ""

# Change to script directory
cd "$(dirname "$0")"

# Start containers
echo "[2/4] Starting Docker containers..."
docker-compose up -d
if [ $? -ne 0 ]; then
    echo "ERROR: Failed to start containers"
    echo ""
    echo "Troubleshooting:"
    echo "  - Run: docker-compose logs backend"
    echo "  - Check .env file exists with API keys"
    echo "  - Ensure ports 3000, 8000, 1433 are available"
    echo ""
    exit 1
fi
echo "OK - Containers starting..."
echo ""

# Wait for services
echo "[3/4] Waiting for services to initialize (30 seconds)..."
sleep 30
echo "OK - Services should be ready"
echo ""

# Check if backend is healthy
echo "[4/4] Running validation tests..."
echo ""

# Run Python validation script
python3 validate_pipeline.py "$@"
if [ $? -ne 0 ]; then
    echo ""
    echo "ERROR: Validation failed"
    echo ""
    echo "Troubleshooting:"
    echo "  - Check backend is running: curl http://localhost:8000/health"
    echo "  - View logs: docker-compose logs backend"
    echo "  - Restart containers: docker-compose restart"
    echo ""
    exit 1
fi

echo ""
echo "================================================================================"
echo "  Validation Complete - Results saved to validation_results.json"
echo "================================================================================"
echo ""
