"""
Authentication Service
Handles user authentication, JWT tokens, and password hashing
"""

import os
import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import jwt
from ..database.repositories import UserRepository, AuditLogRepository


# JWT Configuration
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", secrets.token_hex(32))
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 24
JWT_REFRESH_EXPIRATION_DAYS = 7


class AuthService:
    """
    Authentication service providing user registration, login,
    and JWT token management.
    """

    _instance = None

    def __new__(cls):
        """Singleton pattern for auth service."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self.users = UserRepository()
        self.audit = AuditLogRepository()
        self._initialized = True
        print("[AuthService] Authentication service initialized")

    # ==================== Password Methods ====================

    def hash_password(self, password: str) -> str:
        """
        Hash a password using SHA-256 with salt.

        Args:
            password: Plain text password

        Returns:
            Hashed password with salt
        """
        # Generate a random salt
        salt = secrets.token_hex(16)

        # Hash password with salt
        password_hash = hashlib.sha256(
            (password + salt).encode()
        ).hexdigest()

        # Return salt:hash format
        return f"{salt}:{password_hash}"

    def verify_password(self, password: str, stored_hash: str) -> bool:
        """
        Verify a password against stored hash.

        Args:
            password: Plain text password to verify
            stored_hash: Stored hash in salt:hash format

        Returns:
            True if password matches
        """
        try:
            # Split salt and hash
            salt, expected_hash = stored_hash.split(':')

            # Hash provided password with same salt
            actual_hash = hashlib.sha256(
                (password + salt).encode()
            ).hexdigest()

            # Compare hashes
            return actual_hash == expected_hash
        except Exception:
            return False

    # ==================== JWT Token Methods ====================

    def create_access_token(
        self,
        user_id: int,
        username: str,
        role: str = "user",
        expires_delta: Optional[timedelta] = None
    ) -> str:
        """
        Create a JWT access token.

        Args:
            user_id: User ID
            username: Username
            role: User role
            expires_delta: Optional custom expiration time

        Returns:
            JWT token string
        """
        if expires_delta is None:
            expires_delta = timedelta(hours=JWT_EXPIRATION_HOURS)

        expire = datetime.utcnow() + expires_delta

        payload = {
            "sub": str(user_id),
            "username": username,
            "role": role,
            "exp": expire,
            "iat": datetime.utcnow(),
            "type": "access"
        }

        return jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)

    def create_refresh_token(self, user_id: int) -> str:
        """
        Create a JWT refresh token.

        Args:
            user_id: User ID

        Returns:
            JWT refresh token string
        """
        expire = datetime.utcnow() + timedelta(days=JWT_REFRESH_EXPIRATION_DAYS)

        payload = {
            "sub": str(user_id),
            "exp": expire,
            "iat": datetime.utcnow(),
            "type": "refresh"
        }

        return jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)

    def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """
        Verify and decode a JWT token.

        Args:
            token: JWT token string

        Returns:
            Decoded payload or None if invalid
        """
        try:
            payload = jwt.decode(
                token,
                JWT_SECRET_KEY,
                algorithms=[JWT_ALGORITHM]
            )
            return payload
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None

    def refresh_access_token(self, refresh_token: str) -> Optional[Dict[str, str]]:
        """
        Refresh an access token using a refresh token.

        Args:
            refresh_token: JWT refresh token

        Returns:
            New access token and refresh token or None if invalid
        """
        payload = self.verify_token(refresh_token)

        if not payload or payload.get("type") != "refresh":
            return None

        user_id = int(payload["sub"])
        user = self.users.get_by_id(user_id)

        if not user or not user.get("is_active"):
            return None

        # Create new tokens
        new_access_token = self.create_access_token(
            user_id=user["user_id"],
            username=user["username"],
            role=user.get("role", "user")
        )
        new_refresh_token = self.create_refresh_token(user_id)

        return {
            "access_token": new_access_token,
            "refresh_token": new_refresh_token
        }

    # ==================== User Authentication Methods ====================

    def register(
        self,
        username: str,
        email: str,
        password: str,
        full_name: Optional[str] = None,
        ip_address: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Register a new user.

        Args:
            username: Unique username
            email: User email
            password: Plain text password
            full_name: Optional full name
            ip_address: Optional IP address for audit

        Returns:
            Result with user info and tokens or error
        """
        # Validate input
        if not username or len(username) < 3:
            return {"success": False, "error": "Username must be at least 3 characters"}

        if not email or "@" not in email:
            return {"success": False, "error": "Invalid email address"}

        if not password or len(password) < 6:
            return {"success": False, "error": "Password must be at least 6 characters"}

        # Check if username exists
        if self.users.username_exists(username):
            return {"success": False, "error": "Username already exists"}

        # Check if email exists
        if self.users.email_exists(email):
            return {"success": False, "error": "Email already registered"}

        try:
            # Hash password
            password_hash = self.hash_password(password)

            # Create user
            user_id = self.users.create(
                username=username,
                email=email,
                password_hash=password_hash,
                full_name=full_name,
                role="user"
            )

            # Log registration
            self.audit.log_user_registered(
                user_id=user_id,
                username=username,
                ip_address=ip_address
            )

            # Create tokens
            access_token = self.create_access_token(
                user_id=user_id,
                username=username,
                role="user"
            )
            refresh_token = self.create_refresh_token(user_id)

            return {
                "success": True,
                "user": {
                    "user_id": user_id,
                    "username": username,
                    "email": email,
                    "full_name": full_name,
                    "role": "user"
                },
                "access_token": access_token,
                "refresh_token": refresh_token,
                "token_type": "bearer"
            }

        except Exception as e:
            return {"success": False, "error": f"Registration failed: {str(e)}"}

    def login(
        self,
        username_or_email: str,
        password: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Authenticate a user.

        Args:
            username_or_email: Username or email
            password: Plain text password
            ip_address: Optional IP address for audit
            user_agent: Optional user agent for audit

        Returns:
            Result with user info and tokens or error
        """
        # Find user by username or email
        user = self.users.get_by_username(username_or_email)
        if not user:
            user = self.users.get_by_email(username_or_email)

        if not user:
            return {"success": False, "error": "Invalid username or password"}

        # Check if user is active
        if not user.get("is_active"):
            return {"success": False, "error": "Account is deactivated"}

        # Verify password
        if not self.verify_password(password, user["password_hash"]):
            return {"success": False, "error": "Invalid username or password"}

        try:
            # Update last login
            self.users.update_last_login(user["user_id"])

            # Log login
            self.audit.log_user_login(
                user_id=user["user_id"],
                ip_address=ip_address,
                user_agent=user_agent
            )

            # Create tokens
            access_token = self.create_access_token(
                user_id=user["user_id"],
                username=user["username"],
                role=user.get("role", "user")
            )
            refresh_token = self.create_refresh_token(user["user_id"])

            return {
                "success": True,
                "user": {
                    "user_id": user["user_id"],
                    "username": user["username"],
                    "email": user["email"],
                    "full_name": user.get("full_name"),
                    "role": user.get("role", "user")
                },
                "access_token": access_token,
                "refresh_token": refresh_token,
                "token_type": "bearer"
            }

        except Exception as e:
            return {"success": False, "error": f"Login failed: {str(e)}"}

    def logout(
        self,
        user_id: int,
        ip_address: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Log out a user (audit only, token invalidation not implemented).

        Args:
            user_id: User ID
            ip_address: Optional IP address for audit

        Returns:
            Success result
        """
        try:
            # Log logout
            self.audit.log_user_logout(user_id=user_id, ip_address=ip_address)

            return {"success": True, "message": "Logged out successfully"}

        except Exception as e:
            return {"success": False, "error": f"Logout failed: {str(e)}"}

    def get_current_user(self, token: str) -> Optional[Dict[str, Any]]:
        """
        Get current user from token.

        Args:
            token: JWT access token

        Returns:
            User info or None if invalid
        """
        payload = self.verify_token(token)

        if not payload or payload.get("type") != "access":
            return None

        user_id = int(payload["sub"])
        user = self.users.get_by_id(user_id)

        if not user or not user.get("is_active"):
            return None

        return {
            "user_id": user["user_id"],
            "username": user["username"],
            "email": user["email"],
            "full_name": user.get("full_name"),
            "role": user.get("role", "user")
        }

    def change_password(
        self,
        user_id: int,
        current_password: str,
        new_password: str
    ) -> Dict[str, Any]:
        """
        Change user password.

        Args:
            user_id: User ID
            current_password: Current password
            new_password: New password

        Returns:
            Success result
        """
        user = self.users.get_by_id(user_id)
        if not user:
            return {"success": False, "error": "User not found"}

        # Verify current password
        if not self.verify_password(current_password, user["password_hash"]):
            return {"success": False, "error": "Current password is incorrect"}

        # Validate new password
        if len(new_password) < 6:
            return {"success": False, "error": "New password must be at least 6 characters"}

        try:
            # Hash new password
            new_hash = self.hash_password(new_password)

            # Update password
            self.users.update_password(user_id, new_hash)

            return {"success": True, "message": "Password changed successfully"}

        except Exception as e:
            return {"success": False, "error": f"Password change failed: {str(e)}"}


# Global auth service instance
_auth_service: Optional[AuthService] = None


def get_auth_service() -> AuthService:
    """Get the global auth service instance."""
    global _auth_service
    if _auth_service is None:
        _auth_service = AuthService()
    return _auth_service
