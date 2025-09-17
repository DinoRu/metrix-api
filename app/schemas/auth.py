from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, validator, ConfigDict

from app.models.user import UserRole


class LoginRequest(BaseModel):
    username: str = Field(..., min_length=3)
    password: str = Field(..., min_length=6)

class RegisterRequest(BaseModel):
    username: str = Field(..., min_length=3)
    password: str = Field(..., min_length=8)
    full_name: Optional[str] = None
    role: UserRole = UserRole.CONTROLLER

    @validator("password")
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        if not any(char.isdigit() for char in v):
            raise ValueError("Password must contain at least")
        return v

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"

class UserResponse(BaseModel):
    id: UUID
    username: str
    full_name: Optional[str]
    role: UserRole
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


class UserProfileResponse(BaseModel):
    id: UUID
    username: str
    full_name: Optional[str]
    role: UserRole
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class LoginResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserResponse


# Pydantic schema for password change
class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str

# Pydantic schema for updating profile
class UpdateProfileRequest(BaseModel):
    username: Optional[str] = None
    full_name: Optional[str] = None
    role: Optional[UserRole] = None

    model_config = ConfigDict(from_attributes=True)