from fastapi import FastAPI, Depends, HTTPException, Depends, Header, Query, Path, Request, Body
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
import random, string
from typing import Optional
import os
import psycopg2
from fastapi.responses import JSONResponse
import boto3
from google.oauth2 import service_account
import gspread
from fastapi.responses import JSONResponse
import json
from sqlalchemy import cast, Integer, text, Float
from sqlalchemy.exc import SQLAlchemyError
import logging

from models.models import (
    Program,Service, Scholarship, LeadIn, LeadOut, Booking, BookingCreate, AustraliaScholarship, UniversityModel 
)
from db import Base, engine, get_db
from models.models_user import User
from models.schemas_user import UserRegister, UserLogin, UserVerify, UserOut, TokenResponse
from utils.crud_user import get_user_by_email, create_user
from utils.auth_utils import hash_password, verify_password, create_token, decode_token
from utils.email_service import send_otp, smtp_diagnostics
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO)
logging.info("App starting with DATABASE_URL")

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

SERVICES = [
    Service(code="peer", name="Peer Counselling", category="counselling", description="Connect with current international students."),
    Service(code="rep", name="University Representative", category="counselling", description="Official sessions with university reps."),
    Service(code="visa", name="Visa Guidance", category="compliance", description="Checklist & mock interviews."),
    Service(code="scholarship", name="Scholarship Assistance", category="funding", description="Identify & apply for scholarships."),
]

SCHOLARSHIPS = [
    Scholarship(id=1, name="Global Excellence Scholarship", country="Canada", amount="$10,000", level="Masters", deadline="2025-11-01"),
    Scholarship(id=2, name="STEM Innovators Grant", country="USA", amount="$8,000", level="Bachelors", deadline="2025-12-15"),
    Scholarship(id=3, name="EU Research Fellowship", country="Germany", amount="€12,000", level="PhD", deadline="2026-01-20"),
]

LEADS: list[LeadOut] = []
BOOKINGS: list[Booking] = [
    Booking(id=1, topic="Peer Counselling", scheduled_for=datetime.utcnow()+timedelta(days=3), status="upcoming"),
]

Base.metadata.create_all(bind=engine)

DB_URL = os.environ.get("DATABASE_URL")
session = boto3.session.Session()

logging.basicConfig(level=logging.INFO)

def generate_otp(length: int = 6) -> str:
    return "".join(random.choices(string.digits, k=length))

@app.post("/auth/register", response_model=dict, tags=["auth"], summary="Register & send OTP")
def register(payload: UserRegister, db_session=Depends(get_db)):
    db: Session
    with db_session as db:
        existing = get_user_by_email(db, payload.email.lower())
        if existing:
            if existing.is_verified:
                raise HTTPException(status_code=400, detail="Email already registered")
            user = existing
            user.full_name = payload.full_name
            user.role = payload.role
            user.password_hash = hash_password(payload.password)
        else:
            user = create_user(
                db,
                email=payload.email,
                full_name=payload.full_name,
                role=payload.role,
                password_hash=hash_password(payload.password),
            )
        code = generate_otp()
        user.set_otp(code)
        if not send_otp(user.email, code):
            raise HTTPException(status_code=500, detail="Could not send verification email (check SMTP settings)")
        return {"message": "OTP sent to email for verification"}

@app.post("/auth/verify", response_model=TokenResponse, tags=["auth"], summary="Verify OTP & get token")
def verify_otp(payload: UserVerify, db_session=Depends(get_db)):
    db: Session
    with db_session as db:
        user = get_user_by_email(db, payload.email.lower())
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        if user.is_verified:
            return TokenResponse(access_token=create_token(str(user.id)))
        if not user.otp_code or not user.otp_expires:
            raise HTTPException(status_code=400, detail="No OTP pending")
        if datetime.utcnow() > user.otp_expires:
            raise HTTPException(status_code=400, detail="OTP expired")
        if payload.code != user.otp_code:
            raise HTTPException(status_code=400, detail="Invalid OTP")
        user.is_verified = True
        user.otp_code = None
        user.otp_expires = None
        return TokenResponse(access_token=create_token(str(user.id)))

@app.post("/auth/login", response_model=TokenResponse, tags=["auth"], summary="Login (requires verified)")
def login(payload: UserLogin, db_session=Depends(get_db)):
    db: Session
    with db_session as db:
        user = get_user_by_email(db, payload.email.lower())
        if not user or not verify_password(payload.password, user.password_hash):
            raise HTTPException(status_code=401, detail="Invalid credentials")
        if not user.is_verified:
            raise HTTPException(status_code=403, detail="Email not verified")
        return TokenResponse(access_token=create_token(str(user.id)))

def auth_user(authorization: str | None = Header(default=None), db_session=Depends(get_db)) -> UserOut:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Missing token")
    token = authorization.split(" ",1)[1]
    try:
        data = decode_token(token)
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")
    user_id = data.get("sub")
    db: Session
    with db_session as db:
        user = db.get(User, user_id)
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        payload = {
            "id": str(user.id),
            "email": user.email,
            "full_name": user.full_name,
            "role": user.role,
            "is_verified": user.is_verified,
            "created_at": user.created_at
        }
        return UserOut.model_validate(payload)

@app.get("/users/me", response_model=UserOut, tags=["users"], summary="Current user")
def me(current: UserOut = Depends(auth_user)):
    return current


@app.get("/health", tags=["meta"], summary="Health check")
def health():
    return {"status": "ok"}


@app.get("/services", response_model=list[Service], tags=["services"], summary="List services")
def list_services(category: str | None = None):
    if category:
        return [s for s in SERVICES if s.category == category]
    return SERVICES

    

@app.get("/scholarships", response_model=list[Scholarship], tags=["scholarships"], summary="List scholarships")
def list_scholarships(country: Optional[str] = None, level: Optional[str] = None):
    data = SCHOLARSHIPS
    if country:
        data = [s for s in data if s.country.lower() == country.lower()]
    if level:
        data = [s for s in data if s.level.lower() == level.lower()]
    return data



@app.post("/leads", response_model=LeadOut, status_code=201, tags=["leads"], summary="Create lead")
def create_lead(payload: LeadIn):
    lead = LeadOut(id=len(LEADS)+1, created_at=datetime.utcnow(), **payload.dict())
    LEADS.append(lead)
    return lead


@app.get("/bookings", response_model=list[Booking], tags=["bookings"], summary="List bookings (static demo)")
def list_bookings():
    return BOOKINGS


@app.post("/bookings", response_model=Booking, status_code=201, tags=["bookings"], summary="Create booking (static in-memory)")
def create_booking(payload: BookingCreate):
    b = Booking(id=len(BOOKINGS)+1, topic=payload.topic, scheduled_for=payload.scheduled_for, status="upcoming")
    BOOKINGS.append(b)
    return b


@app.get("/debug/smtp", tags=["meta"], summary="SMTP diagnostics (protected)")
def smtp_debug(current: UserOut = Depends(auth_user)):
    if current.role != "counsellor":
        raise HTTPException(status_code=403, detail="Not authorized")
    return smtp_diagnostics()


@app.post("/api/consultation-excel")
async def consultation_to_excel(request: Request):
    try:
        data = await request.json()
        if "timestamp" not in data:
            data["timestamp"] = datetime.utcnow().isoformat()

        row = [
            data.get("first_name", ""),
            data.get("last_name", ""),
            data.get("email", ""),
            data.get("phone", ""),
            data.get("dial_code", ""),
            data.get("nationality", ""),
            data.get("timestamp", "")
        ]

        GOOGLE_SERVICE_ACCOUNT_FILE = os.environ.get("GOOGLE_SERVICE_ACCOUNT_FILE")
        SPREADSHEET_ID = os.environ.get("EXCEL_FILE_ID")

        creds = service_account.Credentials.from_service_account_file(
            GOOGLE_SERVICE_ACCOUNT_FILE,
            scopes=["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        )

        gc = gspread.authorize(creds)

        sh = gc.open_by_key(SPREADSHEET_ID)

        worksheet = sh.sheet1

        worksheet.append_row(row)

        return {"status": "ok", "message": "Consultation saved to Google Sheet"}

    except Exception as e:
        import traceback
        return JSONResponse(status_code=500, content={"error": str(e), "trace": traceback.format_exc()})



@app.post("/api/accommodation-excel")
async def accommodation_to_excel(request: Request):
    try:
        data = await request.json()
        if "timestamp" not in data:
            data["timestamp"] = datetime.utcnow().isoformat()

        row = [
            data.get("name", ""),
            data.get("email", ""),
            data.get("phone", ""),
            data.get("message", ""),
            data.get("timestamp", "")
        ]

        GOOGLE_SERVICE_ACCOUNT_FILE = os.environ.get("GOOGLE_SERVICE_ACCOUNT_FILE")
        ACCOMMODATION_SPREADSHEET_ID = os.environ.get("ACCOMMODATION_FILE_ID")

        creds = service_account.Credentials.from_service_account_file(
            GOOGLE_SERVICE_ACCOUNT_FILE,
            scopes=["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        )

        gc = gspread.authorize(creds)
        sh = gc.open_by_key(ACCOMMODATION_SPREADSHEET_ID)
        worksheet = sh.sheet1
        worksheet.append_row(row)

        return {"status": "ok", "message": "Accommodation data saved to Google Sheet"}

    except Exception as e:
        import traceback
        return JSONResponse(status_code=500, content={"error": str(e), "trace": traceback.format_exc()})

@app.get("/universities/{school_id}")
def get_university_by_school_id(
    school_id: str,
    db_session=Depends(get_db)
):
   
    db: Session
    with db_session as db:
        uni = db.query(UniversityModel).filter(UniversityModel.id == str(school_id)).first()
        if not uni:
            raise HTTPException(status_code=404, detail="University not found")
        return {
            "id": uni.id,
            "type": uni.type,
            "attributes": uni.attributes,
            "relationships": uni.relationships,
            "included": getattr(uni, "included", None)
        }

@app.get("/scholarships/{school_id}")
def get_scholarships_by_school_id(
    school_id: str,
    db_session=Depends(get_db)
):

    db: Session
    with db_session as db:
        from models.models import ScholarshipModel
        scholarships = db.query(ScholarshipModel).filter(ScholarshipModel.schoolGroupId == int(school_id)).all()
        return [
            {
                "id": sch.id,
                "title": sch.title,
                "description": sch.description,
                "awardAmountFrom": sch.awardAmountFrom,
                "awardAmountTo": sch.awardAmountTo,
                "awardAmountType": sch.awardAmountType,
                "schoolGroupId": sch.schoolGroupId,
                "schoolGroupName": sch.schoolGroupName,
                "sourceUrl": sch.sourceUrl,
                "updatedAt": sch.updatedAt,
            }
            for sch in scholarships
        ]

@app.get("/api/programs/{program_id}")
def get_programs_by_school_id(
    program_id: str,
    db_session=Depends(get_db)
):
    try:
        db: Session
        with db_session as db:
            from models.models import ProgramDetail
            prog = db.query(ProgramDetail).filter(ProgramDetail.id == str(program_id)).first()
            if not prog:
                return JSONResponse(status_code=200, content={})
            return {
                "id": prog.id,
                "attributes": prog.attributes,
                "school": prog.school,
                "program": prog.program,
                "program_requirements": prog.program_requirements,
                "school_id": prog.school_id,
                "program_basic": getattr(prog, "program_basic", None)
            }
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.get("/api/program-details", tags=["programs"], summary="List programs from program_details table")
def list_program_details(
    university_name: Optional[str] = Query(None, description="University name (partial match)"),
    program_name: Optional[str] = Query(None, description="Program name (partial match)"),
    country: Optional[str] = Query(None, description="Country code (partial match)"),
    min_fees: Optional[int] = Query(None, description="Minimum tuition fee"),
    max_fees: Optional[int] = Query(None, description="Maximum tuition fee"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db_session=Depends(get_db),
):
    try:
        from models.models import ProgramDetail
        from sqlalchemy import cast, Integer
        with db_session as db:
            query = db.query(ProgramDetail)

            if university_name:
                query = query.filter(
                    ProgramDetail.school["name"].astext.ilike(f"%{university_name}%")
                )

            if program_name:
                query = query.filter(
                    ProgramDetail.attributes["name"].astext.ilike(f"%{program_name}%")
                )

            if country:
                query = query.filter(
                    ProgramDetail.school["country"].astext.ilike(f"%{country}%")
                )

            if min_fees is not None:
                query = query.filter(
                    cast(ProgramDetail.attributes["tuition"].astext, Float) >= min_fees
                )
            if max_fees is not None:
                query = query.filter(
                    cast(ProgramDetail.attributes["tuition"].astext, Float) <= max_fees
                )

            total = query.count()
            offset = (page - 1) * page_size
            results = query.offset(offset).limit(page_size).all()
            items = [
                {
                    "id": prog.id,
                    "attributes": prog.attributes,
                    "school": prog.school,
                    "program": prog.program,
                    "program_requirements": prog.program_requirements,
                    "school_id": prog.school_id,
                    "program_basic": getattr(prog, "program_basic", None),
                }
                for prog in results
            ]
            return {
                "items": items,
                "total": total,
                "page": page,
                "page_size": page_size,
                "total_pages": (total + page_size - 1) // page_size,
            }
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

