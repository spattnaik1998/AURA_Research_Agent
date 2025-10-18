"""
Configuration and file storage paths for AURA
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Base directory
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Storage directories
STORAGE_DIR = BASE_DIR / "aura_research" / "storage"
ESSAYS_DIR = STORAGE_DIR / "essays"
ANALYSIS_DIR = STORAGE_DIR / "analysis"
VECTOR_STORE_DIR = STORAGE_DIR / "vector_store"

# Create storage directories if they don't exist
STORAGE_DIR.mkdir(exist_ok=True)
ESSAYS_DIR.mkdir(exist_ok=True)
ANALYSIS_DIR.mkdir(exist_ok=True)
VECTOR_STORE_DIR.mkdir(exist_ok=True)

# API Keys
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
SERPER_API_KEY = os.getenv("SERPER_API_KEY")

# Agent Configuration
MAX_SUBORDINATE_AGENTS = 5
BATCH_SIZE = 10  # Papers per agent

# Model Configuration
GPT_MODEL = "gpt-4o"
EMBEDDING_MODEL = "text-embedding-3-small"

# RAG Configuration
VECTOR_STORE_PATH = str(VECTOR_STORE_DIR / "faiss_index")
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200

def get_storage_paths():
    """Return all storage paths as a dictionary"""
    return {
        "base": str(BASE_DIR),
        "storage": str(STORAGE_DIR),
        "essays": str(ESSAYS_DIR),
        "analysis": str(ANALYSIS_DIR),
        "vector_store": str(VECTOR_STORE_DIR)
    }

def validate_env_vars():
    """Validate that required environment variables are set"""
    if not OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY not found in environment variables")
    if not SERPER_API_KEY:
        raise ValueError("SERPER_API_KEY not found in environment variables")
    return True
