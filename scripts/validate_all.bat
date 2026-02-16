@echo off
REM AURA Research Agent - Complete Pipeline Validation Batch Script
REM =================================================================
REM
REM This script:
REM   1. Checks if Docker is running
REM   2. Starts docker-compose containers
REM   3. Waits for services to initialize
REM   4. Runs complete pipeline validation
REM
REM Usage: validate_all.bat [--stage 1-4] [--verbose]

echo.
echo ================================================================================
echo  AURA Research Agent - Complete Pipeline Validation
echo ================================================================================
echo.

REM Check if Docker is running
echo [1/4] Checking Docker status...
docker ps >nul 2>&1
if errorlevel 1 (
    echo.
    echo ERROR: Docker is not running!
    echo.
    echo Please start Docker Desktop and try again:
    echo   - On Windows: Open "Docker Desktop" from Start Menu
    echo   - Wait 30 seconds for Docker daemon to start
    echo   - Then re-run this script
    echo.
    pause
    exit /b 1
)
echo OK - Docker is running
echo.

REM Start containers
echo [2/4] Starting Docker containers...
cd /d "%~dp0"
docker-compose up -d
if errorlevel 1 (
    echo ERROR: Failed to start containers
    echo.
    echo Troubleshooting:
    echo   - Run: docker-compose logs backend
    echo   - Check .env file exists with API keys
    echo   - Ensure ports 3000, 8000, 1433 are available
    echo.
    pause
    exit /b 1
)
echo OK - Containers starting...
echo.

REM Wait for services
echo [3/4] Waiting for services to initialize (30 seconds)...
timeout /t 30 /nobreak
echo OK - Services should be ready
echo.

REM Check if backend is healthy
echo [4/4] Running validation tests...
echo.

REM Run Python validation script
python validate_pipeline.py %*
if errorlevel 1 (
    echo.
    echo ERROR: Validation failed
    echo.
    echo Troubleshooting:
    echo   - Check backend is running: curl http://localhost:8000/health
    echo   - View logs: docker-compose logs backend
    echo   - Restart containers: docker-compose restart
    echo.
)

echo.
echo ================================================================================
echo  Validation Complete - Results saved to validation_results.json
echo ================================================================================
echo.
pause
