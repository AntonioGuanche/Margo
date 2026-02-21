"""Authentication request/response schemas."""

from datetime import datetime

from pydantic import BaseModel, EmailStr


class LoginRequest(BaseModel):
    email: EmailStr


class LoginResponse(BaseModel):
    message: str


class VerifyRequest(BaseModel):
    token: str


class VerifyResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenPayload(BaseModel):
    restaurant_id: int
    email: str
    exp: datetime
