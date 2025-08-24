from sqlalchemy.orm import Session
from sqlalchemy import select
from models.models_user import User

def get_user_by_email(db: Session, email: str) -> User | None:
    return db.execute(select(User).where(User.email == email)).scalar_one_or_none()

def create_user(db: Session, *, email: str, full_name: str | None, role: str, password_hash: str) -> User:
    user = User(email=email.lower(), full_name=full_name, role=role, password_hash=password_hash)
    db.add(user)
    return user

def update_user_status(db: Session, email: str, is_verified: bool) -> None:
    user = get_user_by_email(db, email)
    if user:
        user.is_verified = is_verified
        db.commit()