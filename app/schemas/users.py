import re
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class UserBase(BaseModel):
    """Base schema with user common data."""

    email: EmailStr = Field(
        ...,
        description="The user's email address",
        examples=["user@example.org"],
    )
    username: str = Field(
        ...,
        min_length=3,
        max_length=50,
        description="Unique username",
        examples=["john_doe"],
    )

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str) -> str:
        """Validate username format."""
        v = v.strip()
        if not re.match(r"^[a-zA-Z0-9_-]+$", v):
            raise ValueError(
                """Username can only contain letters,
                numbers, underscores, and hyphens."""
            )
        return v


# ================================
# Request Schemas
# ================================


class UserCreate(UserBase):
    """Schema for creating a new user."""

    password: str = Field(
        ...,
        min_length=8,
        max_length=128,
        description="User's password (will be hashed)",
        examples=["strong_password_123"],
    )

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        """Validate password strength."""
        if not re.search(r"[A-Z]", v):
            raise ValueError(
                "Password must contain at least one uppercase letter."
            )
        if not re.search(r"[a-z]", v):
            raise ValueError(
                "Password must contain at least one lowercase letter."
            )
        if not re.search(r"[0-9]", v):
            raise ValueError("Password must contain at least one digit.")
        if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", v):
            raise ValueError(
                "Password must contain at least one special character."
            )
        return v

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "email": "john.doe@example.org",
                "username": "john_doe",
                "password": "strong_password_123",
            }
        }
    )


class UserProfileEnhance(BaseModel):
    """Schema for enhancing user profile."""

    avatar_url: str | None = Field(
        None,
        max_length=255,
        description="URL to the user's avatar image",
        examples=["https://example.org/avatars/john_doe.png"],
    )
    status: str | None = Field(
        None,
        max_length=500,
        description="User's status message",
        examples=["Feeling happy today!"],
    )

    @field_validator("avatar_url")
    @classmethod
    def validate_avatar_url(cls, v: str | None) -> str | None:
        """Validate avatar URL format."""
        if v is None:
            return v
        if not v.startswith(("http://", "https://")):
            raise ValueError("Avatar URL must start with http:// or https://")
        return v

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "avatar_url": "https://example.com/avatars/john.jpg",
                "status": "Feeling happy today!",
            }
        }
    )


class UserLogin(BaseModel):
    """
    Schema for user login request, allowing either email or username.
    """

    username_or_email: str = Field(
        ..., description="Username or email for login"
    )
    password: str = Field(..., description="User's password")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "username_or_email": "john_doe",
                "password": "strong_password_123",
            }
        }
    )


# ================================
# Response Schemas
# ================================


class UserResponse(BaseModel):
    """
    Schema for user data in responses (excludes password and activation token).
    """

    id: UUID = Field(..., description="Unique identifier for the user")
    email: EmailStr = Field(..., description="The user's email address")
    username: str = Field(..., description="Unique username")
    avatar_url: str | None = Field(
        None, description="URL to the user's avatar image"
    )
    status: str | None = Field(None, description="User's status message")
    last_seen: datetime | None = Field(
        None, description="Timestamp of the user's last activity"
    )
    is_active: bool = Field(..., description="Indicates if the user is active")
    created_at: datetime = Field(
        ..., description="Timestamp when the user was created"
    )
    updated_at: datetime = Field(
        ..., description="Timestamp when the user was last updated"
    )
    is_deleted: bool = Field(..., description="Indicates if the user is deleted")

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "email": "john.doe@example.com",
                "username": "john_doe",
                "avatar_url": "https://example.com/avatars/john.jpg",
                "status": "Hey there! I'm using MINA",
                "last_seen": "2024-01-25T09:15:00Z",
                "is_active": True,
                "created_at": "2024-01-15T10:30:00Z",
                "updated_at": "2024-01-20T14:45:00Z",
                "is_deleted": False,
            }
        },
    )


class TokenResponse(BaseModel):
    """JWT token response schema."""

    access_token: str = Field(..., description="JWT access token")
    refresh_token: str | None = Field(None, description="JWT refresh token")
    token_type: str = Field(default="bearer", description="Token type")
    expires_in: int = Field(..., description="Token expiration time in seconds")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "token_type": "bearer",
                "expires_in": 3600,
            }
        }
    )


class LoginResponse(BaseModel):
    """Response after successful login."""

    user: UserResponse = Field(..., description="User information")
    token: TokenResponse = Field(..., description="Authentication tokens")

    model_config = ConfigDict(from_attributes=True)
