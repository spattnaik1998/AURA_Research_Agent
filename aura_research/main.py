"""
AURA - Autonomous Unified Research Assistant
FastAPI Backend Server
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .routes import chat, research
import uvicorn

app = FastAPI(
    title="AURA Research Assistant",
    description="Autonomous multi-agent research system with RAG chatbot",
    version="1.0.0"
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
app.include_router(chat.router)
app.include_router(research.router)

@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "status": "active",
        "message": "AURA Research Assistant API is running",
        "version": "1.0.0"
    }

@app.get("/health")
async def health_check():
    """Detailed health check"""
    return {
        "status": "healthy",
        "services": {
            "api": "running",
            "agents": "ready",
            "rag": "ready"
        }
    }

if __name__ == "__main__":
    uvicorn.run("aura_research.main:app", host="0.0.0.0", port=8000, reload=True)
