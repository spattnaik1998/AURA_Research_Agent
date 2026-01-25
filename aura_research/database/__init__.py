"""
AURA Research Agent - Database Module
SQL Server integration with Windows Authentication
"""

from .connection import DatabaseConnection, get_db_connection
from .repositories import (
    UserRepository,
    ResearchSessionRepository,
    PaperRepository,
    PaperAnalysisRepository,
    EssayRepository,
    ChatRepository,
    GraphRepository,
    IdeationRepository
)

__all__ = [
    'DatabaseConnection',
    'get_db_connection',
    'UserRepository',
    'ResearchSessionRepository',
    'PaperRepository',
    'PaperAnalysisRepository',
    'EssayRepository',
    'ChatRepository',
    'GraphRepository',
    'IdeationRepository'
]
