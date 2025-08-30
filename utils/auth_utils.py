import os, bcrypt, jwt
from datetime import datetime, timedelta
from typing import Any

JWT_SECRET = os.getenv("JWT_SECRET", "dev_secret_change_me")
JWT_ALG = "HS256"
JWT_EXP_MIN = 60 * 24 

def hash_password(raw: str) -> str:
    return bcrypt.hashpw(raw.encode(), bcrypt.gensalt()).decode()

def verify_password(raw: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(raw.encode(), hashed.encode())
    except Exception:
        return False

def create_token(sub: str, expires_delta: timedelta = timedelta(days=7)) -> str:
    to_encode = {
        "sub": sub,
        "iat": datetime.utcnow(),
        "exp": datetime.utcnow() + expires_delta,
    }
    return jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALG)

def decode_token(token: str) -> dict:
    return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALG])
