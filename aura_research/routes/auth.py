"""
Authentication API Routes
Handles user registration, login, and token management
"""

from fastapi import APIRouter, HTTPException, Request, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr
from typing import Optional, Dict, Any
from ..services.auth_service import get_auth_service

router = APIRouter(prefix="/auth", tags=["authentication"])
security = HTTPBearer(auto_error=False)


# ==================== Request/Response Models ====================

class RegisterRequest(BaseModel):
    """User registration request"""
    username: str
    email: str
    password: str
    full_name: Optional[str] = None


class LoginRequest(BaseModel):
    """User login request"""
    username_or_email: str
    password: str


class TokenRefreshRequest(BaseModel):
    """Token refresh request"""
    refresh_token: str


class PasswordChangeRequest(BaseModel):
    """Password change request"""
    current_password: str
    new_password: str


class UserResponse(BaseModel):
    """User info response"""
    user_id: int
    username: str
    email: str
    full_name: Optional[str] = None
    role: str


class AuthResponse(BaseModel):
    """Authentication response with tokens"""
    success: bool
    user: Optional[UserResponse] = None
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    token_type: Optional[str] = None
    error: Optional[str] = None


class MessageResponse(BaseModel):
    """Simple message response"""
    success: bool
    message: Optional[str] = None
    error: Optional[str] = None


# ==================== Helper Functions ====================

def get_client_ip(request: Request) -> Optional[str]:
    """Extract client IP from request."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else None


def get_user_agent(request: Request) -> Optional[str]:
    """Extract user agent from request."""
    return request.headers.get("User-Agent")


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> Optional[Dict[str, Any]]:
    """
    Dependency to get current user from JWT token.
    Returns None if no token or invalid token.
    """
    if not credentials:
        return None

    auth_service = get_auth_service()
    user = auth_service.get_current_user(credentials.credentials)
    return user


async def require_auth(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> Dict[str, Any]:
    """
    Dependency that requires valid authentication.
    Raises 401 if not authenticated.
    """
    if not credentials:
        raise HTTPException(
            status_code=401,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"}
        )

    auth_service = get_auth_service()
    user = auth_service.get_current_user(credentials.credentials)

    if not user:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"}
        )

    return user


async def require_admin(user: Dict[str, Any] = Depends(require_auth)) -> Dict[str, Any]:
    """
    Dependency that requires admin role.
    """
    if user.get("role") != "admin":
        raise HTTPException(
            status_code=403,
            detail="Admin access required"
        )
    return user


# ==================== Auth Routes ====================

@router.post("/register", response_model=AuthResponse)
async def register(request: RegisterRequest, http_request: Request):
    """
    Register a new user account

    Args:
        request: Registration details

    Returns:
        User info and authentication tokens

    Example:
        ```
        POST /auth/register
        {
            "username": "researcher1",
            "email": "researcher@example.com",
            "password": "securepassword123",
            "full_name": "John Researcher"
        }
        ```
    """
    auth_service = get_auth_service()
    ip_address = get_client_ip(http_request)

    result = auth_service.register(
        username=request.username,
        email=request.email,
        password=request.password,
        full_name=request.full_name,
        ip_address=ip_address
    )

    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])

    return AuthResponse(
        success=True,
        user=UserResponse(**result["user"]),
        access_token=result["access_token"],
        refresh_token=result["refresh_token"],
        token_type=result["token_type"]
    )


@router.post("/login", response_model=AuthResponse)
async def login(request: LoginRequest, http_request: Request):
    """
    Authenticate user and get tokens

    Args:
        request: Login credentials

    Returns:
        User info and authentication tokens

    Example:
        ```
        POST /auth/login
        {
            "username_or_email": "researcher1",
            "password": "securepassword123"
        }
        ```
    """
    auth_service = get_auth_service()
    ip_address = get_client_ip(http_request)
    user_agent = get_user_agent(http_request)

    result = auth_service.login(
        username_or_email=request.username_or_email,
        password=request.password,
        ip_address=ip_address,
        user_agent=user_agent
    )

    if not result["success"]:
        raise HTTPException(status_code=401, detail=result["error"])

    return AuthResponse(
        success=True,
        user=UserResponse(**result["user"]),
        access_token=result["access_token"],
        refresh_token=result["refresh_token"],
        token_type=result["token_type"]
    )


@router.post("/logout", response_model=MessageResponse)
async def logout(
    http_request: Request,
    user: Dict[str, Any] = Depends(require_auth)
):
    """
    Log out current user

    Args:
        user: Current authenticated user

    Returns:
        Success message

    Example:
        ```
        POST /auth/logout
        Authorization: Bearer <token>
        ```
    """
    auth_service = get_auth_service()
    ip_address = get_client_ip(http_request)

    result = auth_service.logout(
        user_id=user["user_id"],
        ip_address=ip_address
    )

    if not result["success"]:
        raise HTTPException(status_code=500, detail=result["error"])

    return MessageResponse(success=True, message=result["message"])


@router.post("/refresh", response_model=AuthResponse)
async def refresh_token(request: TokenRefreshRequest):
    """
    Refresh access token using refresh token

    Args:
        request: Refresh token

    Returns:
        New access and refresh tokens

    Example:
        ```
        POST /auth/refresh
        {
            "refresh_token": "<refresh_token>"
        }
        ```
    """
    auth_service = get_auth_service()

    result = auth_service.refresh_access_token(request.refresh_token)

    if not result:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    return AuthResponse(
        success=True,
        access_token=result["access_token"],
        refresh_token=result["refresh_token"],
        token_type="bearer"
    )


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(user: Dict[str, Any] = Depends(require_auth)):
    """
    Get current authenticated user info

    Returns:
        Current user details

    Example:
        ```
        GET /auth/me
        Authorization: Bearer <token>
        ```
    """
    return UserResponse(**user)


@router.post("/change-password", response_model=MessageResponse)
async def change_password(
    request: PasswordChangeRequest,
    user: Dict[str, Any] = Depends(require_auth)
):
    """
    Change current user's password

    Args:
        request: Current and new password

    Returns:
        Success message

    Example:
        ```
        POST /auth/change-password
        Authorization: Bearer <token>
        {
            "current_password": "oldpassword",
            "new_password": "newpassword123"
        }
        ```
    """
    auth_service = get_auth_service()

    result = auth_service.change_password(
        user_id=user["user_id"],
        current_password=request.current_password,
        new_password=request.new_password
    )

    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])

    return MessageResponse(success=True, message=result["message"])


@router.get("/verify")
async def verify_token(user: Dict[str, Any] = Depends(get_current_user)):
    """
    Verify if current token is valid

    Returns:
        Token validity status and user info

    Example:
        ```
        GET /auth/verify
        Authorization: Bearer <token>
        ```
    """
    if user:
        return {
            "valid": True,
            "user": UserResponse(**user)
        }
    else:
        return {
            "valid": False,
            "user": None
        }
