"""
User Repository
Database operations for Users table
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
from .base_repository import BaseRepository


class UserRepository(BaseRepository):
    """Repository for user management operations."""

    @property
    def table_name(self) -> str:
        return "Users"

    @property
    def primary_key(self) -> str:
        return "user_id"

    def create(
        self,
        username: str,
        email: str,
        password_hash: str,
        full_name: Optional[str] = None,
        role: str = "user"
    ) -> int:
        """Create a new user and return the user_id."""
        query = """
            INSERT INTO Users (username, email, password_hash, full_name, role)
            VALUES (?, ?, ?, ?, ?)
        """
        return self.db.insert_and_get_id(
            query,
            (username, email, password_hash, full_name, role)
        )

    def get_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        """Get user by username."""
        try:
            query = "SELECT * FROM Users WHERE username = ?"
            return self.db.fetch_one(query, (username,))
        except Exception as e:
            import logging
            logging.getLogger('aura.database').error(f"Error getting user by username: {str(e)}", exc_info=True)
            return None

    def get_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Get user by email."""
        try:
            query = "SELECT * FROM Users WHERE email = ?"
            return self.db.fetch_one(query, (email,))
        except Exception as e:
            import logging
            logging.getLogger('aura.database').error(f"Error getting user by email: {str(e)}", exc_info=True)
            return None

    def update_last_login(self, user_id: int) -> bool:
        """Update user's last login timestamp."""
        query = "UPDATE Users SET last_login = GETDATE() WHERE user_id = ?"
        rows_affected = self.db.execute(query, (user_id,))
        return rows_affected > 0

    def update_password(self, user_id: int, password_hash: str) -> bool:
        """Update user's password."""
        query = """
            UPDATE Users
            SET password_hash = ?, updated_at = GETDATE()
            WHERE user_id = ?
        """
        rows_affected = self.db.execute(query, (password_hash, user_id))
        return rows_affected > 0

    def deactivate(self, user_id: int) -> bool:
        """Deactivate a user account."""
        query = "UPDATE Users SET is_active = 0, updated_at = GETDATE() WHERE user_id = ?"
        rows_affected = self.db.execute(query, (user_id,))
        return rows_affected > 0

    def get_active_users(self) -> List[Dict[str, Any]]:
        """Get all active users."""
        query = "SELECT * FROM Users WHERE is_active = 1 ORDER BY created_at DESC"
        return self.db.fetch_all(query)

    def username_exists(self, username: str) -> bool:
        """Check if username already exists."""
        query = "SELECT 1 FROM Users WHERE username = ?"
        result = self.db.fetch_one(query, (username,))
        return result is not None

    def email_exists(self, email: str) -> bool:
        """Check if email already exists."""
        query = "SELECT 1 FROM Users WHERE email = ?"
        result = self.db.fetch_one(query, (email,))
        return result is not None
