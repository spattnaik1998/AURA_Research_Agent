"""
Database Connection Module
SQL Server connection using Windows Authentication
"""

import pyodbc
from typing import Optional, Any, List, Dict
from contextlib import contextmanager
import json
import logging
from datetime import datetime
from ..utils.config import DB_SERVER, DB_DATABASE, DB_DRIVER

# Setup logger
logger = logging.getLogger('aura.database')


class DatabaseConnection:
    """
    SQL Server database connection manager using Windows Authentication.
    Configuration loaded from environment variables.
    """

    _instance: Optional['DatabaseConnection'] = None
    _connection: Optional[pyodbc.Connection] = None

    # Connection configuration from environment
    SERVER = DB_SERVER
    DATABASE = DB_DATABASE
    DRIVER = DB_DRIVER

    def __new__(cls):
        """Singleton pattern for database connection."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @property
    def connection_string(self) -> str:
        """Build connection string - supports both Windows and SQL auth."""
        import os
        use_sql_auth = os.getenv("DB_USE_SQL_AUTH", "false").lower() == "true"

        if use_sql_auth:
            # Docker/Production: SQL Authentication
            username = os.getenv("DB_USERNAME")
            password = os.getenv("DB_PASSWORD")
            return (
                f"Driver={self.DRIVER};"
                f"Server={self.SERVER};"
                f"Database={self.DATABASE};"
                f"Uid={username};"
                f"Pwd={password};"
            )
        else:
            # Development: Windows Authentication
            return (
                f"Driver={self.DRIVER};"
                f"Server={self.SERVER};"
                f"Database={self.DATABASE};"
                f"Trusted_Connection=yes;"
            )

    def connect(self) -> pyodbc.Connection:
        """Establish database connection."""
        if self._connection is None or self._is_connection_closed():
            try:
                self._connection = pyodbc.connect(
                    self.connection_string,
                    autocommit=False
                )
                logger.info(f"Connected to {self.DATABASE} on {self.SERVER}")
            except pyodbc.Error as e:
                logger.error(f"Connection error: {e}")
                raise
        return self._connection

    def _is_connection_closed(self) -> bool:
        """Check if connection is closed."""
        if self._connection is None:
            return True
        try:
            # Try a simple query to check connection
            self._connection.execute("SELECT 1")
            return False
        except:
            return True

    def disconnect(self):
        """Close database connection."""
        if self._connection is not None:
            try:
                self._connection.close()
                logger.info("Connection closed")
            except Exception as e:
                logger.warning(f"Error closing connection: {e}")
            finally:
                self._connection = None

    @contextmanager
    def get_cursor(self):
        """Context manager for database cursor with auto-commit/rollback."""
        connection = self.connect()
        cursor = connection.cursor()
        try:
            yield cursor
            connection.commit()
        except Exception as e:
            connection.rollback()
            raise e
        finally:
            cursor.close()

    @contextmanager
    def get_cursor_no_commit(self):
        """Context manager for read-only operations (no commit)."""
        connection = self.connect()
        cursor = connection.cursor()
        try:
            yield cursor
        finally:
            cursor.close()

    def execute(self, query: str, params: tuple = None) -> int:
        """Execute a query and return affected row count."""
        with self.get_cursor() as cursor:
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            return cursor.rowcount

    def execute_many(self, query: str, params_list: List[tuple]) -> int:
        """Execute a query for multiple parameter sets."""
        with self.get_cursor() as cursor:
            cursor.executemany(query, params_list)
            return cursor.rowcount

    def fetch_one(self, query: str, params: tuple = None) -> Optional[Dict[str, Any]]:
        """Fetch a single row as dictionary."""
        with self.get_cursor_no_commit() as cursor:
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            row = cursor.fetchone()
            if row:
                columns = [column[0] for column in cursor.description]
                return dict(zip(columns, row))
            return None

    def fetch_all(self, query: str, params: tuple = None) -> List[Dict[str, Any]]:
        """Fetch all rows as list of dictionaries."""
        with self.get_cursor_no_commit() as cursor:
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            rows = cursor.fetchall()
            if rows:
                columns = [column[0] for column in cursor.description]
                return [dict(zip(columns, row)) for row in rows]
            return []

    def insert_and_get_id(self, query: str, params: tuple = None) -> int:
        """Insert a row and return the generated ID."""
        with self.get_cursor() as cursor:
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            cursor.execute("SELECT SCOPE_IDENTITY()")
            result = cursor.fetchone()
            return int(result[0]) if result and result[0] else 0

    def test_connection(self) -> bool:
        """Test if database connection works."""
        try:
            result = self.fetch_one("SELECT 1 as test")
            return result is not None and result.get('test') == 1
        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            return False


# Global database connection instance
_db_instance: Optional[DatabaseConnection] = None


def get_db_connection() -> DatabaseConnection:
    """Get the global database connection instance."""
    global _db_instance
    if _db_instance is None:
        _db_instance = DatabaseConnection()
    return _db_instance


# Utility functions for JSON handling
def to_json(data: Any) -> Optional[str]:
    """Convert Python object to JSON string for storage."""
    if data is None:
        return None
    try:
        return json.dumps(data, default=str)
    except:
        return None


def from_json(json_str: Optional[str]) -> Any:
    """Parse JSON string from database."""
    if json_str is None:
        return None
    try:
        return json.loads(json_str)
    except:
        return None


def format_datetime(dt: Optional[datetime]) -> Optional[str]:
    """Format datetime for display."""
    if dt is None:
        return None
    return dt.strftime("%Y-%m-%d %H:%M:%S")
