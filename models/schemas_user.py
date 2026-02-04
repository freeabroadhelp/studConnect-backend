from pydantic import BaseModel, EmailStr, constr
from datetime import datetime

class UserRegister(BaseModel):
    email: EmailStr
    password: constr(min_length=6)
    full_name: str | None = None
    role: str = "student"

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserVerify(BaseModel):
    email: EmailStr
    code: str

class UserOut(BaseModel):
    id: str
    email: EmailStr
    full_name: str | None
    role: str
    is_verified: bool
    created_at: datetime
    avatar_url: str | None = None
    phone: str | None = None
    gender: str | None = None
    date_of_birth: str | None = None
    address: str | None = None
    city: str | None = None
    postal_code: str | None = None
    country: str | None = None
    class Config:
        from_attributes = True

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
