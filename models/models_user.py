import uuid
from datetime import datetime, timedelta
from sqlalchemy import Column, String, Boolean, DateTime
from sqlalchemy.dialects.postgresql import UUID
from db import Base
import os

class User(Base):
    __tablename__ = "users"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, index=True, nullable=False)
    full_name = Column(String(255))
    role = Column(String(32), nullable=False, default="student")
    password_hash = Column(String(255), nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)
    otp_code = Column(String(10), nullable=True)
    otp_expires = Column(DateTime(timezone=False), nullable=True)
    created_at = Column(DateTime(timezone=False), default=datetime.utcnow, nullable=False)

    def set_otp(self, code: str, minutes_valid: int | None = None):
        mv = minutes_valid or int(os.getenv("OTP_EXP_MIN", "5"))
        self.otp_code = code
        self.otp_expires = datetime.utcnow() + timedelta(minutes=mv)
