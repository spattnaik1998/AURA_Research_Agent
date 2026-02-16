"""
AURA - Autonomous Unified Research Assistant
FastAPI Backend Server
"""

import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi.errors import RateLimitExceeded
from fastapi.responses import JSONResponse
from .routes import chat, research, graph, ideation, auth
from .utils.config import validate_env_vars
from .utils.logging_config import setup_logging, get_logger
from .utils.rate_limiter import limiter
from .database.connection import get_db_connection
import uvicorn

# Setup structured logging
setup_logging()
logger = get_logger('aura.api')

# Initialize Sentry for error tracking (optional)
sentry_dsn = os.getenv('SENTRY_DSN')
if sentry_dsn:
    import sentry_sdk
    from sentry_sdk.integrations.fastapi import FastApiIntegration
    from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration

    sentry_sdk.init(
        dsn=sentry_dsn,
        integrations=[
            FastApiIntegration(),
            SqlalchemyIntegration(),
        ],
        environment=os.getenv('SENTRY_ENVIRONMENT', 'local'),
        traces_sample_rate=float(os.getenv('SENTRY_TRACES_SAMPLE_RATE', '0.1')),
        debug=False
    )
    logger.info("Sentry error tracking initialized", extra={
        'environment': os.getenv('SENTRY_ENVIRONMENT', 'local')
    })

app = FastAPI(
    title="AURA Research Assistant",
    description="Autonomous multi-agent research system with RAG chatbot and user authentication",
    version="2.0.0"
)

# Register the shared rate limiter
app.state.limiter = limiter

# Custom exception handler for rate limit exceeded
@app.exception_handler(RateLimitExceeded)
async def rate_limit_exceeded_handler(request, exc):
    return JSONResponse(
        status_code=429,
        content={"detail": "Too many requests. Please try again later."}
    )

# CORS middleware for frontend integration
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)

# Add rate limiting middleware
app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)

# Add Prometheus metrics instrumentation
from prometheus_fastapi_instrumentator import Instrumentator

# Configure Prometheus metrics
Instrumentator().instrument(app).expose(app)

# Include routers
app.include_router(auth.router)  # Authentication routes
app.include_router(chat.router)
app.include_router(research.router)
app.include_router(graph.router)
app.include_router(ideation.router)

@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "status": "active",
        "message": "AURA Research Assistant API is running",
        "version": "2.0.0",
        "features": [
            "Multi-agent research",
            "RAG chatbot",
            "Knowledge graph",
            "Research ideation",
            "User authentication",
            "SQL Server integration"
        ]
    }

@app.get("/health")
async def health_check():
    """Comprehensive health check with detailed diagnostics"""
    from .services.health_service import get_health_service
    health_service = get_health_service()
    return health_service.get_health_status()

@app.get("/readiness")
async def readiness_check():
    """Lightweight readiness check for load balancers and orchestrators"""
    from .services.health_service import get_health_service
    from fastapi.responses import JSONResponse

    health_service = get_health_service()
    status = health_service.get_readiness_status()

    # Return 503 Service Unavailable if not ready
    if not status["ready"]:
        return JSONResponse(status_code=503, content=status)

    return status

@app.on_event("startup")
async def startup_event():
    """Validate environment and test connections on startup"""
    try:
        validate_env_vars()
        logger.info("[AURA] Environment variables validated successfully")
    except ValueError as e:
        logger.error(f"[AURA] ERROR: {str(e)}")
        logger.error("[AURA] Please check your .env file and ensure API keys are set")

    # Test database connection
    try:
        db = get_db_connection()
        if db.test_connection():
            logger.info("[AURA] Database connection established successfully")
        else:
            logger.warning("[AURA] Database connection test failed")
    except Exception as e:
        logger.warning(f"[AURA] Database connection error: {str(e)}")
        logger.warning("[AURA] The application will run but database features may be limited")

    logger.info("[AURA] Backend server started and ready")

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    try:
        db = get_db_connection()
        db.disconnect()
        logger.info("[AURA] Database connection closed")
    except Exception:
        pass
    logger.info("[AURA] Backend server shutting down")

if __name__ == "__main__":
    import os
    environment = os.getenv("ENVIRONMENT", "development")

    if environment == "production":
        uvicorn.run(
            "aura_research.main:app",
            host="0.0.0.0",
            port=8000,
            reload=False,
            workers=4,
            log_level="info"
        )
    else:
        uvicorn.run(
            "aura_research.main:app",
            host="0.0.0.0",
            port=8000,
            reload=True
        )
