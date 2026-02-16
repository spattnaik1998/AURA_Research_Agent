"""
Pytest Configuration and Fixtures
Provides shared test fixtures and configuration for the test suite.
"""

import pytest
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from unittest.mock import Mock, MagicMock, patch
import bcrypt


@pytest.fixture
def sample_user():
    """Sample user for testing."""
    return {
        "user_id": 1,
        "username": "testuser",
        "email": "testuser@example.com",
        "password_hash": bcrypt.hashpw(b"TestPassword123!", bcrypt.gensalt()),
        "full_name": "Test User",
        "role": "user",
        "is_active": True,
        "created_at": "2026-02-16T00:00:00",
        "last_login": "2026-02-16T00:00:00"
    }


@pytest.fixture
def sample_session():
    """Sample research session for testing."""
    return {
        "session_id": 1,
        "session_code": "20260216_000000",
        "query": "machine learning in healthcare",
        "user_id": 1,
        "status": "completed",
        "progress": 100,
        "created_at": "2026-02-16T00:00:00",
        "completed_at": "2026-02-16T00:05:00"
    }


@pytest.fixture
def sample_paper():
    """Sample research paper for testing."""
    return {
        "paper_id": 1,
        "session_id": 1,
        "title": "Deep Learning in Healthcare: A Systematic Review",
        "authors": "Smith, J.; Johnson, M.; Williams, L.",
        "abstract": "This paper reviews deep learning applications in healthcare...",
        "publication_year": 2023,
        "source": "IEEE Transactions on Medical Imaging",
        "url": "https://example.com/paper1",
        "citation_count": 42,
        "category": "Machine Learning"
    }


@pytest.fixture
def sample_essay():
    """Sample generated essay for testing."""
    return {
        "essay_id": 1,
        "session_id": 1,
        "essay": "Machine learning has revolutionized healthcare...",
        "word_count": 2500,
        "quality_score": 8.5,
        "citation_count": 15,
        "papers_synthesized": 10,
        "status": "completed"
    }


@pytest.fixture
def mock_user_repository():
    """Mock UserRepository for testing."""
    repo = MagicMock()
    repo.create = MagicMock(return_value=1)
    repo.get_by_username = MagicMock(return_value=None)
    repo.get_by_email = MagicMock(return_value=None)
    repo.update_password = MagicMock(return_value=True)
    repo.update_last_login = MagicMock(return_value=True)
    return repo


@pytest.fixture
def mock_audit_repository():
    """Mock AuditLogRepository for testing."""
    repo = MagicMock()
    repo.log_user_registered = MagicMock(return_value=True)
    repo.log_user_login = MagicMock(return_value=True)
    repo.log_user_logout = MagicMock(return_value=True)
    return repo


@pytest.fixture
def mock_session_repository():
    """Mock ResearchSessionRepository for testing."""
    repo = MagicMock()
    repo.create = MagicMock(return_value=1)
    repo.get_by_session_code = MagicMock(return_value=None)
    repo.get_by_id = MagicMock(return_value=None)
    repo.update_status = MagicMock(return_value=True)
    repo.mark_completed = MagicMock(return_value=True)
    return repo


@pytest.fixture
def mock_db_connection():
    """Mock database connection for testing."""
    conn = MagicMock()
    conn.connect = MagicMock(return_value=True)
    conn.test_connection = MagicMock(return_value=True)
    conn.execute = MagicMock(return_value=1)
    conn.fetch_one = MagicMock(return_value=None)
    conn.fetch_many = MagicMock(return_value=[])
    return conn


@pytest.fixture
def test_client():
    """Create a FastAPI test client."""
    from fastapi.testclient import TestClient
    from aura_research.main import app

    return TestClient(app)


@pytest.fixture
def valid_user_credentials():
    """Valid user credentials for testing."""
    return {
        "username": "testuser",
        "email": "testuser@example.com",
        "password": "TestPassword123!",
        "full_name": "Test User"
    }


@pytest.fixture
def invalid_user_credentials():
    """Invalid user credentials for testing."""
    return {
        "username": "invalid",
        "email": "invalid@example.com",
        "password": "weak",  # Too weak
    }


@pytest.fixture
def jwt_token():
    """Sample JWT token for testing."""
    return "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxIiwidXNlcm5hbWUiOiJ0ZXN0dXNlciIsInJvbGUiOiJ1c2VyIiwiZXhwIjoxNzcxMzAzNDk3fQ.test_signature"


# Pytest configuration
def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers", "unit: mark test as a unit test"
    )
    config.addinivalue_line(
        "markers", "integration: mark test as an integration test"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )
