"""
Base Repository Class
Abstract base class for all database repositories
"""

from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any
from ..connection import DatabaseConnection, get_db_connection, to_json, from_json


class BaseRepository(ABC):
    """
    Base repository class providing common database operations.
    All entity-specific repositories should inherit from this class.
    """

    def __init__(self, db: Optional[DatabaseConnection] = None):
        """Initialize repository with database connection."""
        self.db = db or get_db_connection()

    @property
    @abstractmethod
    def table_name(self) -> str:
        """Return the table name for this repository."""
        pass

    @property
    @abstractmethod
    def primary_key(self) -> str:
        """Return the primary key column name."""
        pass

    def get_by_id(self, id: int) -> Optional[Dict[str, Any]]:
        """Get a single record by primary key."""
        query = f"SELECT * FROM {self.table_name} WHERE {self.primary_key} = ?"
        return self.db.fetch_one(query, (id,))

    def get_all(self, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """Get all records with pagination."""
        query = f"""
            SELECT * FROM {self.table_name}
            ORDER BY {self.primary_key} DESC
            OFFSET ? ROWS FETCH NEXT ? ROWS ONLY
        """
        return self.db.fetch_all(query, (offset, limit))

    def delete_by_id(self, id: int) -> bool:
        """Delete a record by primary key."""
        query = f"DELETE FROM {self.table_name} WHERE {self.primary_key} = ?"
        rows_affected = self.db.execute(query, (id,))
        return rows_affected > 0

    def count(self) -> int:
        """Get total count of records."""
        query = f"SELECT COUNT(*) as count FROM {self.table_name}"
        result = self.db.fetch_one(query)
        return result['count'] if result else 0

    def exists(self, id: int) -> bool:
        """Check if a record exists by primary key."""
        query = f"SELECT 1 FROM {self.table_name} WHERE {self.primary_key} = ?"
        result = self.db.fetch_one(query, (id,))
        return result is not None

    @staticmethod
    def to_json(data: Any) -> Optional[str]:
        """Convert data to JSON string."""
        return to_json(data)

    @staticmethod
    def from_json(json_str: Optional[str]) -> Any:
        """Parse JSON string to Python object."""
        return from_json(json_str)
