"""
AURA - Autonomous Unified Research Assistant
FastAPI Backend Server
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .routes import chat, research, graph, ideation, auth
from .utils.config import validate_env_vars
from .utils.logging_config import setup_logging, get_logger
from .database.connection import get_db_connection
import uvicorn

# Setup structured logging
setup_logging()
logger = get_logger('aura.api')

app = FastAPI(
    title="AURA Research Assistant",
    description="Autonomous multi-agent research system with RAG chatbot and user authentication",
    version="2.0.0"
)

# CORS middleware for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure based on frontend URL in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
    """Detailed health check"""
    # Check database connection
    db_status = "unknown"
    try:
        db = get_db_connection()
        if db.test_connection():
            db_status = "connected"
        else:
            db_status = "disconnected"
    except Exception as e:
        db_status = f"error: {str(e)}"

    return {
        "status": "healthy",
        "services": {
            "api": "running",
            "agents": "ready",
            "rag": "ready",
            "database": db_status,
            "auth": "ready"
        }
    }

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
    uvicorn.run("aura_research.main:app", host="0.0.0.0", port=8000, reload=True)
