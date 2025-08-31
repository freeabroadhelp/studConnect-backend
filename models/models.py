from itertools import count
import json
from pydantic import BaseModel, EmailStr, constr
from datetime import datetime
from typing import List, Optional, Any
from sqlalchemy import JSON, Column, Integer, String, Text, DateTime, ForeignKey, Float
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Session, relationship
import boto3
import os
from sqlalchemy.ext.mutable import MutableDict
import re
import mimetypes
from urllib.parse import urlparse, unquote
import requests
from db import Base

class AustraliaScholarship(Base):
    __tablename__ = "australia_scholarships"
    __table_args__ = {'extend_existing': True}  # Ensures CREATE TABLE IF NOT EXISTS behavior
    id = Column(Integer, primary_key=True, autoincrement=True)
    university = Column(String, nullable=False, unique=True)
    state = Column(String)
    type = Column(String)
    scholarships = Column(JSONB)
    common_programs = Column(JSONB)
    updated_at = Column(String)


class Service(BaseModel):
    code: str
    name: str
    category: str
    description: str


class University(BaseModel):
    id: int
    name: str
    country: str
    tuition: int
    programs: List[str]


class Scholarship(BaseModel):
    id: int
    name: str
    country: str
    amount: str
    level: str
    deadline: str


class ShortlistPreference(BaseModel):
    country: Optional[str] = None
    budget: Optional[int] = None
    program: Optional[str] = None


class ShortlistItem(BaseModel):
    university: str
    country: str
    match_score: float
    tuition: int
    programs: List[str]


class LeadIn(BaseModel):
    name: str
    email: EmailStr
    message: str


class LeadOut(LeadIn):
    id: int
    created_at: datetime


class Booking(BaseModel):
    id: int
    topic: str
    scheduled_for: datetime
    status: str


class BookingCreate(BaseModel):
    topic: str
    scheduled_for: datetime


class ForgotPasswordRequest(BaseModel):
    email: EmailStr
class ResetPasswordRequest(BaseModel):
    email: EmailStr
    code: str
    new_password: constr(min_length=6)


class ProgramDetail(Base):
    __tablename__ = "program_details"
    id = Column(String, primary_key=True)
    attributes = Column(JSONB)
    school = Column(JSONB)
    program = Column(JSONB)
    program_requirements = Column(JSONB)
    school_id = Column(Integer)
    program_basic = Column(JSONB)

    @classmethod
    def upsert(cls, db: Session, entry: dict):
        obj = db.query(cls).get(entry['id'])
        if obj:
            obj.attributes = entry.get('attributes')
            obj.school = entry.get('school')
            obj.program = entry.get('program')
            obj.program_requirements = entry.get('program_requirements')
            obj.school_id = entry.get('school_id')
            obj.program_basic = entry.get('program_basic')
        else:
            obj = cls(
                id=entry['id'],
                attributes=entry.get('attributes'),
                school=entry.get('school'),
                program=entry.get('program'),
                program_requirements=entry.get('program_requirements'),
                school_id=entry.get('school_id'),
                program_basic=entry.get('program_basic')
            )
            db.add(obj)
        db.flush()
        return obj

    @classmethod
    def get_by_id(cls, db: Session, id_: str) -> Optional["ProgramDetail"]:
        return db.query(cls).filter_by(id=id_).first()


def create_program_details_table_and_upload(db: Session, data: list[dict]):
    for entry in data:
        ProgramDetail.upsert(db, entry)
        db.commit()


class Program(Base):
    __tablename__ = "programs"
    id = Column(String, primary_key=True)
    type = Column(String)
    attributes = Column(JSONB)

    @classmethod
    def upsert(cls, db: Session, entry: dict):
        # Fetch school_id from attributes['school']['id'] if available
        attributes = entry.get('attributes', {})
        school = attributes.get('school', {})
        school_id = school.get('id')
        obj = db.query(cls).get(entry['id'])
        if obj:
            obj.type = entry.get('type')
            obj.attributes = attributes
        else:
            obj = cls(
                id=entry['id'],
                type=entry.get('type'),
                attributes=attributes,
            )
            db.add(obj)
        db.flush()
        return obj

    @classmethod
    def get_by_id(cls, db: Session, id_: str) -> Optional["Program"]:
        return db.query(cls).filter_by(id=id_).first()


class UniversityModel(Base):
    __tablename__ = "universities"
    id = Column(String, primary_key=True)
    type = Column(String)
    attributes = Column(JSONB)
    relationships = Column(JSONB)
    included = Column(JSONB)

    @classmethod
    def upsert(cls, db: Session, entry: dict):
        obj = db.query(cls).get(entry['id'])
        if obj:
            obj.type = entry.get('type')
            obj.attributes = entry.get('attributes')
            obj.relationships = entry.get('relationships')
            obj.included = entry.get('included')
        else:
            obj = cls(
                id=entry['id'],
                type=entry.get('type'),
                attributes=entry.get('attributes'),
                relationships=entry.get('relationships'),
                included=entry.get('included')
            )
            db.add(obj)
        return obj


class ScholarshipModel(Base):
    __tablename__ = "scholarships"
    id = Column(Integer, primary_key=True)
    externalId = Column(String)
    title = Column(String)
    description = Column(String)
    awardAmountCurrencyCode = Column(String)
    awardAmountCurrencySymbol = Column(String)
    awardAmountFrom = Column(String)
    awardAmountTo = Column(String)
    awardAmountType = Column(String)
    automaticallyApplied = Column(String)
    eligibleLevels = Column(JSONB)
    eligibleNationalities = Column(JSONB)
    marketCode = Column(String)
    path = Column(String)
    schoolGroupId = Column(Integer)
    schoolGroupName = Column(String)
    slug = Column(String)
    sourceUrl = Column(String)
    updatedAt = Column(String)

    @classmethod
    def upsert(cls, db: Session, entry: dict):
        valid_fields = {k: entry.get(k) for k in cls.__table__.columns.keys()}
        obj = db.query(cls).get(valid_fields['id'])
        if obj:
            for field, value in valid_fields.items():
                setattr(obj, field, value)
        else:
            obj = cls(**valid_fields)
            db.add(obj)
        return obj


def upload_public_url_to_r2_and_get_url(public_url: str, key_prefix: str = "uploads/") -> str:
    r2_bucket = os.getenv("R2_BUCKET")
    r2_access_key = os.getenv("R2_ACCESS_KEY")
    r2_secret_key = os.getenv("R2_SECRET_KEY")
    r2_endpoint = os.getenv("R2_ENDPOINT")
    r2_public_url = os.getenv("R2_PUBLIC_URL")

    if not all([r2_bucket, r2_access_key, r2_secret_key, r2_endpoint, r2_public_url]):
        raise Exception("Missing R2 configuration in environment variables.")

    resp = requests.get(public_url, stream=True, timeout=30)
    if resp.status_code != 200:
        raise Exception(f"Failed to download file from {public_url}")

    parsed = urlparse(public_url)
    filename = unquote(os.path.basename(parsed.path))

    root, ext = os.path.splitext(filename)
    if not ext:
        ctype = resp.headers.get("Content-Type", "").split(";")[0]
        ext = mimetypes.guess_extension(ctype) or ".bin"

    root = re.sub(r"[^A-Za-z0-9._-]+", "-", root).strip("-._")
    filename = f"{root}{ext}"

    key = f"{key_prefix}{filename}"

    session = boto3.session.Session()
    s3 = session.client(
        service_name="s3",
        endpoint_url=r2_endpoint,
        aws_access_key_id=r2_access_key,
        aws_secret_access_key=r2_secret_key,
    )

    s3.put_object(
        Bucket=r2_bucket,
        Key=key,
        Body=resp.content,
        ContentType=resp.headers.get("Content-Type", "application/octet-stream"),
    )

    return f"{r2_public_url.rstrip('/')}/{key}"

class PeerCounsellor(Base):
    __tablename__ = "peer_counsellors"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, nullable=False)
    name = Column(String, nullable=False)
    phone = Column(String)
    contact_method = Column(String)
    university = Column(String)
    program = Column(String)
    location = Column(String)
    languages = Column(String)
    profile_image_url = Column(String)
    about = Column(Text)
    expertise = Column(Text)
    work_experience = Column(Text)
    peer_support_experience = Column(Text)
    projects = Column(Text)
    journey = Column(Text)
    charges = Column(Float)  # New column for charges per slot
    created_at = Column(DateTime, default=datetime.utcnow)

    availabilities = relationship("PeerCounsellorAvailability", back_populates="counsellor", cascade="all, delete-orphan")

class PeerCounsellorAvailability(Base):
    __tablename__ = "peer_counsellor_availability"
    id = Column(Integer, primary_key=True, index=True)
    counsellor_id = Column(Integer, ForeignKey("peer_counsellors.id"), nullable=False)
    day_of_week = Column(String, nullable=False)  # e.g. "Monday"
    start_time = Column(String, nullable=False)   # e.g. "09:00"
    end_time = Column(String, nullable=False)     # e.g. "11:00"

    counsellor = relationship("PeerCounsellor", back_populates="availabilities")
    counsellor = relationship("PeerCounsellor", back_populates="availabilities")

class PeerCounsellorBooking(Base):
    __tablename__ = "peer_counsellor_bookings"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, nullable=False)
    user_email = Column(String, nullable=False)
    counsellor_id = Column(Integer, ForeignKey("peer_counsellors.id"), nullable=False)
    counsellor_email = Column(String, nullable=False)
    slot_id = Column(Integer, ForeignKey("peer_counsellor_availability.id"), nullable=False)
    slot_date = Column(DateTime, nullable=False)
    payment_status = Column(String, default="pending")  # pending, paid, failed
    meeting_link = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)

    counsellor = relationship("PeerCounsellor")
    slot = relationship("PeerCounsellorAvailability")
