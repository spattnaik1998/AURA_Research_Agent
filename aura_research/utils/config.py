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
AUDIO_DIR = STORAGE_DIR / "audio"

# Create storage directories if they don't exist
STORAGE_DIR.mkdir(exist_ok=True)
ESSAYS_DIR.mkdir(exist_ok=True)
ANALYSIS_DIR.mkdir(exist_ok=True)
VECTOR_STORE_DIR.mkdir(exist_ok=True)
AUDIO_DIR.mkdir(exist_ok=True)

# API Keys
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
SERPER_API_KEY = os.getenv("SERPER_API_KEY")

# ElevenLabs Configuration
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
ELEVENLABS_API_URL = "https://api.elevenlabs.io/v1"
ELEVENLABS_DEFAULT_VOICE_ID = "21m00Tcm4TlvDq8ikWAM"  # Rachel voice

# Database Configuration
DB_SERVER = os.getenv("DB_SERVER", "LAPTOP-FO95TROJ")
DB_DATABASE = os.getenv("DB_DATABASE", "AURA_Research")
DB_DRIVER = os.getenv("DB_DRIVER", "{ODBC Driver 17 for SQL Server}")

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

# Academic Rigor & Quality Control Configuration
# Paper Validation
CROSSREF_API_URL = "https://api.crossref.org/works"
OPENALEX_API_URL = "https://api.openalex.org/works"
MIN_VALID_PAPERS = 5
VALIDATION_CACHE_HOURS = 24

# Source Sufficiency
MIN_UNIQUE_VENUES = 3
MIN_RECENT_PAPERS = 2
MIN_EFFECTIVE_COUNT = 4.0

# Quality Scoring
MIN_QUALITY_SCORE = 5.0
FLAG_QUALITY_SCORE = 6.5
EXCELLENT_QUALITY_SCORE = 8.0
CITATION_DENSITY_TARGET = 0.0057  # 1 per 175 words
MAX_ESSAY_REGENERATION_ATTEMPTS = 2

# Citation Verification
MIN_CITATION_ACCURACY = 1.0  # 100% required

# Fact Checking
FACT_CHECK_TOP_N_CLAIMS = 10
MIN_SUPPORTED_CLAIMS_PCT = 0.85

# Academic Rigor Settings
STRICT_MODE = True
ALLOW_MOCK_DATA = False  # CRITICAL: Must remain False

def get_storage_paths():
    """Return all storage paths as a dictionary"""
    return {
        "base": str(BASE_DIR),
        "storage": str(STORAGE_DIR),
        "essays": str(ESSAYS_DIR),
        "analysis": str(ANALYSIS_DIR),
        "vector_store": str(VECTOR_STORE_DIR),
        "audio": str(AUDIO_DIR)
    }

def validate_env_vars():
    """Validate that required environment variables are set"""
    if not OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY not found in environment variables")
    if not SERPER_API_KEY:
        raise ValueError("SERPER_API_KEY not found in environment variables")
    if not ELEVENLABS_API_KEY:
        raise ValueError("ELEVENLABS_API_KEY not found in environment variables")
    return True
