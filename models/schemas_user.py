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
    class Config:
        from_attributes = True

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
