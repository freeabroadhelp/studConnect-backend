from fastapi import FastAPI, Depends, HTTPException, Depends, Header, Query, Path, Request, Body
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime, timedelta
from sqlalchemy import and_
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
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests

from models.models import (
    Program,Service, Scholarship, LeadIn, LeadOut, Booking, BookingCreate, AustraliaScholarship, UniversityModel ,ResetPasswordRequest,ForgotPasswordRequest,
    PeerCounsellor, PeerCounsellorAvailability,PeerCounsellorBooking
)
from db import Base, engine, get_db
from models.models_user import User
from models.schemas_user import UserRegister, UserLogin, UserVerify, UserOut, TokenResponse
from utils.crud_user import get_user_by_email, create_user
from utils.auth_utils import hash_password, verify_password, create_token, decode_token
from utils.email_service import send_otp, smtp_diagnostics, send_email  # Make sure send_email is imported
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
    except Exception as e:
        logging.error(f"Token decode failed: {e}")
        raise HTTPException(status_code=401, detail=f"Invalid token: {e}")
    user_id = data.get("sub")
    db: Session
    with db_session as db:
        user = db.get(User, user_id)
        if not user:
            logging.error(f"User not found for id: {user_id}")
            raise HTTPException(status_code=401, detail=f"User not found for id: {user_id}")
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
            data.get("preferred_destination", ""),      # <-- Added
            data.get("preferred_study_level", ""),      # <-- Added
            data.get("preferred_start_year", ""),       # <-- Added
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


@app.post("/auth/forgot-password", tags=["auth"], summary="Request password reset (send OTP)")
def forgot_password(payload: ForgotPasswordRequest, db_session=Depends(get_db)):
    db: Session
    with db_session as db:
        user = get_user_by_email(db, payload.email.lower())
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        code = generate_otp()
        user.set_otp(code)
        if not send_otp(user.email, code):
            raise HTTPException(status_code=500, detail="Could not send reset email (check SMTP settings)")
        return {"message": "Password reset OTP sent to email"}

@app.post("/auth/reset-password", tags=["auth"], summary="Reset password using OTP")
def reset_password(payload: ResetPasswordRequest, db_session=Depends(get_db)):
    db: Session
    with db_session as db:
        user = get_user_by_email(db, payload.email.lower())
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        if not user.otp_code or not user.otp_expires:
            raise HTTPException(status_code=400, detail="No OTP pending")
        if datetime.utcnow() > user.otp_expires:
            raise HTTPException(status_code=400, detail="OTP expired")
        if payload.code != user.otp_code:
            raise HTTPException(status_code=400, detail="Invalid OTP")
        user.password_hash = hash_password(payload.new_password)
        user.otp_code = None
        user.otp_expires = None
        return {"message": "Password reset successful"}

@app.post("/api/auth/google", tags=["auth"], summary="Google OAuth login/register")
def google_oauth_login(
    payload: dict = Body(...),
    db_session=Depends(get_db)
):
    token = payload.get("token")
    if not token:
        raise HTTPException(status_code=400, detail="Missing Google token")

    GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID")
    if not GOOGLE_CLIENT_ID:
        raise HTTPException(status_code=500, detail="Google client ID not configured")

    try:
        idinfo = id_token.verify_oauth2_token(token, google_requests.Request(), GOOGLE_CLIENT_ID)
        email = idinfo.get("email")
        full_name = idinfo.get("name", "")
        if not email:
            raise HTTPException(status_code=400, detail="Google token missing email")
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Invalid Google token: {str(e)}")

    db: Session
    with db_session as db:
        user = get_user_by_email(db, email.lower())
        if not user:
            random_password = ''.join(random.choices(string.ascii_letters + string.digits, k=32))
            user = create_user(
                db,
                email=email,
                full_name=full_name,
                role="student",
                password_hash=hash_password(random_password),
            )
            user.is_verified = True
        elif not user.is_verified:
            user.is_verified = True

        access_token = create_token(str(user.id))
        return {"access_token": access_token}

@app.get("/peer-counsellors/{counsellor_id}/available-slots", tags=["peer-counsellors"])
def get_available_slots(
    counsellor_id: int,
    db_session=Depends(get_db),
    days: int = Query(30, ge=1, le=60, description="Number of days to look ahead for available slots (default 30, max 60)")
):
    """
    Returns available 30-min slots for the next `days` days (default 30) for a given peer counsellor,
    excluding slots already booked for a specific date.
    """
    db: Session
    with db_session as db:
        availabilities = db.query(PeerCounsellorAvailability).filter_by(counsellor_id=counsellor_id).all()
        now = datetime.utcnow()
        end_date = now + timedelta(days=days)
        bookings = db.query(PeerCounsellorBooking).filter(
            PeerCounsellorBooking.counsellor_id == counsellor_id,
            PeerCounsellorBooking.slot_date >= now,
            PeerCounsellorBooking.slot_date < end_date,
            PeerCounsellorBooking.payment_status == "paid"
        ).all()
        booked = set((b.slot_date.date(), b.slot_id) for b in bookings)
        result = []
        for day_offset in range(days):
            day = now.date() + timedelta(days=day_offset)
            weekday = day.strftime("%A")
            for av in availabilities:
                if av.day_of_week == weekday:
                    if (day, av.id) not in booked:
                        result.append({
                            "slot_id": av.id,
                            "date": day.isoformat(),
                            "start_time": av.start_time,
                            "end_time": av.end_time,
                        })
        return result

@app.get("/peer-counsellors", tags=["peer-counsellors"])
def list_peer_counsellors(db_session=Depends(get_db)):
   
    db: Session
    with db_session as db:
        peers = db.query(PeerCounsellor).all()
        result = []
        for peer in peers:
            result.append({
                "id": peer.id,
                "email": peer.email,
                "name": peer.name,
                "phone": peer.phone,
                "contact_method": peer.contact_method,
                "university": peer.university,
                "program": peer.program,
                "location": peer.location,
                "languages": peer.languages,
                "profile_image_url": peer.profile_image_url,
                "about": peer.about,
                "expertise": peer.expertise,
                "work_experience": peer.work_experience,
                "peer_support_experience": peer.peer_support_experience,
                "projects": peer.projects,
                "journey": peer.journey,
                "created_at": peer.created_at,
                "charges": peer.charges
            })
        return result

from fastapi import status

@app.post("/peer-counsellors/upsert", tags=["peer-counsellors"], status_code=status.HTTP_201_CREATED)
def upsert_peer_counsellor(
    payload: dict = Body(...),
    db_session=Depends(get_db)
):
   
    db: Session
    with db_session as db:
        email = payload.get("email")
        if not email:
            raise HTTPException(status_code=400, detail="Email is required")
        peer = db.query(PeerCounsellor).filter_by(email=email).first()
        if peer:
            for field in [
                "name", "phone", "contact_method", "university", "program", "location",
                "languages", "profile_image_url", "about", "expertise", "work_experience",
                "peer_support_experience", "projects", "journey", "charges"
            ]:
                if field in payload:
                    setattr(peer, field, payload[field])
        else:
            peer = PeerCounsellor(**payload)
            db.add(peer)
        db.commit()
        db.refresh(peer)
        return {
            "id": peer.id,
            "email": peer.email,
            "name": peer.name,
            "phone": peer.phone,
            "contact_method": peer.contact_method,
            "university": peer.university,
            "program": peer.program,
            "location": peer.location,
            "languages": peer.languages,
            "profile_image_url": peer.profile_image_url,
            "about": peer.about,
            "expertise": peer.expertise,
            "work_experience": peer.work_experience,
            "peer_support_experience": peer.peer_support_experience,
            "projects": peer.projects,
            "journey": peer.journey,
            "created_at": peer.created_at,
            "charges": peer.charges
        }


@app.post("/peer-counsellors/{counsellor_id}/availability/upsert", tags=["peer-counsellors"])
def upsert_peer_availability(
    counsellor_id: int,
    slots: list[dict] = Body(...),
    db_session=Depends(get_db)
):
    db: Session
    with db_session as db:
        db.query(PeerCounsellorAvailability).filter_by(counsellor_id=counsellor_id).delete()
      
        for slot in slots:
            db.add(PeerCounsellorAvailability(
                counsellor_id=counsellor_id,
                day_of_week=slot["day_of_week"],
                start_time=slot["start_time"],
                end_time=slot["end_time"]
            ))
        db.commit()
        return {"status": "ok", "count": len(slots)}

@app.post("/peer-counsellors/book-slot", tags=["peer-counsellors"])
def book_peer_counsellor_slot(
    payload: dict = Body(...),
    db_session=Depends(get_db)
):
    """
    Book a session with a peer counsellor.
    Expects JSON body:
    {
      "user_id": <int>,
      "user_email": <str>,
      "counsellor_id": <int>,
      "counsellor_email": <str>,
      "slot_id": <int>,
      "slot_date": <ISO datetime string>,
      "payment_status": <str, e.g. "pending" or "paid">,
      "meeting_link": <str, optional>
    }
    """
    db: Session
    with db_session as db:
        slot_date = datetime.fromisoformat(payload["slot_date"])
        existing_paid = db.query(PeerCounsellorBooking).filter_by(
            counsellor_id=payload["counsellor_id"],
            slot_id=payload["slot_id"],
            slot_date=slot_date,
            payment_status="paid"
        ).first()
        if existing_paid:
            raise HTTPException(status_code=409, detail="Slot already booked and paid for this date/time")

        if payload.get("payment_status") == "paid":
            existing_any = db.query(PeerCounsellorBooking).filter_by(
                counsellor_id=payload["counsellor_id"],
                slot_id=payload["slot_id"],
                slot_date=slot_date
            ).filter(PeerCounsellorBooking.payment_status.in_(["paid", "pending"])).first()
            if existing_any:
                raise HTTPException(status_code=409, detail="Slot already reserved or paid for this date/time")

        booking = PeerCounsellorBooking(
            user_id=payload["user_id"],
            user_email=payload["user_email"],
            counsellor_id=payload["counsellor_id"],
            counsellor_email=payload["counsellor_email"],
            slot_id=payload["slot_id"],
            slot_date=slot_date,
            payment_status=payload.get("payment_status", "pending"),
            meeting_link=payload.get("meeting_link")
        )
        db.add(booking)
        db.commit()
        db.refresh(booking)
        return {
            "id": booking.id,
            "user_id": booking.user_id,
            "user_email": booking.user_email,
            "counsellor_id": booking.counsellor_id,
            "counsellor_email": booking.counsellor_email,
            "slot_id": booking.slot_id,
            "slot_date": booking.slot_date.isoformat(),
            "payment_status": booking.payment_status,
            "meeting_link": booking.meeting_link,
            "created_at": booking.created_at.isoformat()
        }

@app.post("/peer-counsellors/confirm-payment", tags=["peer-counsellors"])
def confirm_peer_counsellor_payment(
    payload: dict = Body(...),
    db_session=Depends(get_db)
):
    """
    Confirm payment for a peer counsellor booking.
    Expects JSON body:
    {
      "booking_id": <int>,
      "meeting_link": <str, optional>
    }
    Sets payment_status to "paid" and (optionally) updates meeting_link.
    """
    db: Session
    with db_session as db:
        booking_id = payload.get("booking_id")
        if not booking_id:
            raise HTTPException(status_code=400, detail="booking_id is required")
        booking = db.query(PeerCounsellorBooking).filter_by(id=booking_id).first()
        if not booking:
            raise HTTPException(status_code=404, detail="Booking not found")
        if booking.payment_status == "paid":
            raise HTTPException(status_code=409, detail="Booking already marked as paid")

        existing_paid = db.query(PeerCounsellorBooking).filter(
            PeerCounsellorBooking.counsellor_id == booking.counsellor_id,
            PeerCounsellorBooking.slot_id == booking.slot_id,
            PeerCounsellorBooking.slot_date == booking.slot_date,
            PeerCounsellorBooking.payment_status == "paid",
            PeerCounsellorBooking.id != booking.id
        ).first()
        if existing_paid:
            raise HTTPException(status_code=409, detail="Slot already paid for by another user")

        booking.payment_status = "paid"
        if "meeting_link" in payload:
            booking.meeting_link = payload["meeting_link"]
        db.commit()
        db.refresh(booking)

        try:
            slot_time = booking.slot_date.strftime("%A, %d %B %Y at %H:%M")
            subject = "Your Peer Counselling Session is Confirmed"
            message = (
                f"Dear {booking.user_email},\n\n"
                f"Your session with peer counsellor ({booking.counsellor_email}) has been booked.\n"
                f"Date & Time: {slot_time}\n"
                f"Meeting Link: {booking.meeting_link or 'Will be shared soon'}\n\n"
                f"Please join the meeting 5 minutes prior to your scheduled time.\n\n"
                f"Thank you for booking with us!\n"
            )
            send_email(
                to_email=booking.user_email,
                subject=subject,
                message=message
            )
        except Exception as e:
            logging.error(f"Failed to send confirmation email: {e}")

        try:
            slot_time = booking.slot_date.strftime("%A, %d %B %Y at %H:%M")
            subject = "A Session Has Been Booked With You"
            message = (
                f"Dear {booking.counsellor_email},\n\n"
                f"A student ({booking.user_email}) has booked a session with you.\n"
                f"Date & Time: {slot_time}\n"
                f"Meeting Link: {booking.meeting_link or 'Will be shared soon'}\n\n"
                f"Please be ready and join the meeting 5 minutes prior to the scheduled time.\n\n"
                f"Thank you for supporting students!\n"
            )
            send_email(
                to_email=booking.counsellor_email,
                subject=subject,
                message=message
            )
        except Exception as e:
            logging.error(f"Failed to send confirmation email to counsellor: {e}")

        return {
            "id": booking.id,
            "user_id": booking.user_id,
            "user_email": booking.user_email,
            "counsellor_id": booking.counsellor_id,
            "counsellor_email": booking.counsellor_email,
            "slot_id": booking.slot_id,
            "slot_date": booking.slot_date.isoformat(),
            "payment_status": booking.payment_status,
            "meeting_link": booking.meeting_link,
            "created_at": booking.created_at.isoformat()
        }

@app.get("/peer-counsellors/bookings", tags=["peer-counsellors"])
def list_peer_counsellor_bookings(
    db_session=Depends(get_db),
    current_user: UserOut = Depends(auth_user),
    status_filter: Optional[str] = Query(None, description="Filter by payment status: pending, paid, failed"),
    days_ahead: int = Query(30, ge=1, le=90, description="Number of days ahead to fetch bookings (default 30, max 90)")
):
   
    db: Session
    with db_session as db:
        query = db.query(PeerCounsellorBooking)
        
        if current_user.role == "student":
            query = query.filter(PeerCounsellorBooking.user_id == current_user.id)
        elif current_user.role == "counsellor":
            counsellor = db.query(PeerCounsellor).filter_by(email=current_user.email).first()
            if counsellor:
                query = query.filter(PeerCounsellorBooking.counsellor_id == counsellor.id)
            else:
                return [] 
            
            query = query.filter(PeerCounsellorBooking.payment_status == status_filter)
        
        now = datetime.utcnow()
        end_date = now + timedelta(days=days_ahead)
        query = query.filter(
            PeerCounsellorBooking.slot_date >= now,
            PeerCounsellorBooking.slot_date <= end_date
        )
        
        query = query.order_by(PeerCounsellorBooking.slot_date)
        
        bookings = query.all()
        
        result = []
        for booking in bookings:
            availability = db.query(PeerCounsellorAvailability).filter_by(id=booking.slot_id).first()
            counsellor = db.query(PeerCounsellor).filter_by(id=booking.counsellor_id).first()
            
            result.append({
                "booking_id": booking.id,
                "user_id": booking.user_id,
                "user_email": booking.user_email,
                "counsellor_id": booking.counsellor_id,
                "counsellor_email": booking.counsellor_email,
                "counsellor_name": counsellor.name if counsellor else None,
                "slot_id": booking.slot_id,
                "slot_date": booking.slot_date.isoformat(),
                "slot_day": booking.slot_date.strftime("%A"),
                "start_time": availability.start_time if availability else None,
                "end_time": availability.end_time if availability else None,
                "payment_status": booking.payment_status,
                "meeting_link": booking.meeting_link,
                "created_at": booking.created_at.isoformat(),
                "charges": counsellor.charges if counsellor else None
            })
        
        return result

import httpx
from pydantic import BaseModel

DODO_API_KEY = os.getenv("DODO_API_KEY")

class Customer(BaseModel):
    name: str
    email: str
    phone: str = None

class PaymentRequest(BaseModel):
    amount: float
    customer: Customer
    booking_id: str

FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")

@app.post("/api/create-dodo-session", tags=["payments"])
async def create_dodo_session(request: PaymentRequest):
    try:
        logging.info(f"Creating payment session for booking {request.booking_id}. Amount: ₹{request.amount}")
        
        if not request.booking_id or not request.amount or request.amount <= 0:
            raise HTTPException(status_code=400, detail="Invalid booking ID or amount")
        
        if not request.customer.email or not request.customer.name:
            raise HTTPException(status_code=400, detail="Customer email and name are required")
        
        # Only attempt real Dodo if we have valid API key
        if DODO_API_KEY and DODO_API_KEY.strip() and len(DODO_API_KEY) > 10:
            try:
                logging.info("Attempting real Dodo Payments API...")
                
                # Use the correct Dodo API endpoint (check Dodo documentation)
                DODO_URL = "https://api.dodopayments.com/v1/sessions"
                
                payload = {
                    "amount": int(request.amount * 100),  # Convert to paisa
                    "currency": "INR",
                    "customer": {
                        "name": request.customer.name,
                        "email": request.customer.email,
                        "phone": request.customer.phone
                    },
                    "product": {
                        "name": "Peer Counselling Session",
                        "description": f"StudConnect - Booking #{request.booking_id}"
                    },
                    "success_url": f"{FRONTEND_URL}/payment-success?bookingId={request.booking_id}",
                    "cancel_url": f"{FRONTEND_URL}/payment-cancel?bookingId={request.booking_id}",
                    "webhook_url": f"{os.getenv('BACKEND_URL', 'https://studconnect-backend.onrender.com')}/webhook/dodo",
                    "metadata": {"bookingId": request.booking_id}
                }

                headers = {
                    "Authorization": f"Bearer {DODO_API_KEY}",
                    "Content-Type": "application/json"
                }

                async with httpx.AsyncClient(timeout=10.0) as client:
                    resp = await client.post(DODO_URL, json=payload, headers=headers)
                    
                    logging.info(f"Dodo API response: {resp.status_code}")
                    if resp.status_code != 200:
                        logging.error(f"Dodo API error: {resp.text}")
                        raise Exception(f"Dodo API failed with status {resp.status_code}")
                    
                    data = resp.json()
                    checkout_url = data.get("checkout_url") or data.get("url")
                    
                    if checkout_url:
                        logging.info(f"Real Dodo session created successfully for booking {request.booking_id}")
                        logging.info(f"Checkout URL: {checkout_url}")
                        return {
                            "checkout_url": checkout_url,
                            "booking_id": request.booking_id,
                            "status": "success",
                            "payment_type": "dodo"
                        }
                    else:
                        raise Exception("No checkout URL in Dodo response")
                        
            except Exception as e:
                logging.error(f"Dodo API failed: {e}")
                # Don't fall back to mock if we have a real API key - this helps debug
                raise HTTPException(status_code=500, detail=f"Payment gateway error: {str(e)}")
        
        # Fallback to mock payment only if no API key
        logging.info("No Dodo API key configured, using mock payment")
        mock_checkout_url = f"{FRONTEND_URL}/mock-payment?booking_id={request.booking_id}&amount={request.amount}&email={request.customer.email}&name={request.customer.name}"
        
        return {
            "checkout_url": mock_checkout_url,
            "booking_id": request.booking_id,
            "amount": request.amount,
            "status": "success",
            "payment_type": "mock"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Unexpected error creating payment session: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Payment session creation failed: {str(e)}")

@app.post("/webhook/dodo", tags=["payments"])
async def dodo_webhook(request: Request, db_session=Depends(get_db)):
   
    try:
        event = await request.json()
        logging.info(f"Received Dodo webhook: {event}")
        
        # Check webhook signature if Dodo provides one (recommended for security)
        # signature = request.headers.get("dodo-signature")
        # if not verify_webhook_signature(event, signature):
        #     raise HTTPException(status_code=400, detail="Invalid webhook signature")
        
        event_type = event.get("type") or event.get("event_type")
        
        if event_type == "payment.succeeded" or event_type == "payment_success":
            # Extract booking ID from metadata
            metadata = event.get("metadata", {})
            booking_id = metadata.get("bookingId") or event.get("reference")
            
            if not booking_id:
                logging.warning("No booking ID in webhook payload")
                return {"status": "ok", "message": "No booking ID"}
            
            db: Session
            with db_session as db:
                booking = db.query(PeerCounsellorBooking).filter_by(id=int(booking_id)).first()
                if not booking:
                    logging.warning(f"Booking {booking_id} not found")
                    return {"status": "ok", "message": "Booking not found"}
                
                if booking.payment_status == "paid":
                    logging.info(f"Booking {booking_id} already marked as paid")
                    return {"status": "ok", "message": "Already processed"}
                
                # Update booking status
                booking.payment_status = "paid"
                db.commit()
                logging.info(f"Booking {booking_id} marked as paid via Dodo webhook")
                
                # Send confirmation emails
                try:
                    slot_time = booking.slot_date.strftime("%A, %d %B %Y at %H:%M")
                    
                    # Email to student
                    user_subject = "Payment Confirmed - Your Peer Counselling Session"
                    user_message = (
                        f"Dear {booking.user_email},\n\n"
                        f"Your payment has been successfully processed!\n\n"
                        f"Session Details:\n"
                        f"Date & Time: {slot_time}\n"
                        f"Counsellor: {booking.counsellor_email}\n"
                        f"Meeting Link: {booking.meeting_link or 'Will be shared soon'}\n\n"
                        f"Please join the meeting 5 minutes prior to your scheduled time.\n\n"
                        f"Thank you for choosing StudConnect!\n"
                    )
                    send_email(booking.user_email, user_subject, user_message)
                    
                    # Email to counsellor
                    counsellor_subject = "New Session Booked - Payment Confirmed"
                    counsellor_message = (
                        f"Dear {booking.counsellor_email},\n\n"
                        f"A new session has been booked with you and payment is confirmed.\n\n"
                        f"Session Details:\n"
                        f"Date & Time: {slot_time}\n"
                        f"Student: {booking.user_email}\n"
                        f"Meeting Link: {booking.meeting_link or 'Please set up meeting link'}\n\n"
                        f"Please be ready 5 minutes before the scheduled time.\n\n"
                        f"StudConnect Team\n"
                    )
                    send_email(booking.counsellor_email, counsellor_subject, counsellor_message)
                    
                except Exception as e:
                    logging.error(f"Failed to send confirmation emails: {e}")
                
                return {"status": "ok", "message": "Payment processed successfully"}
        
        elif event_type == "payment.failed" or event_type == "payment_failed":
            # Handle failed payment
            metadata = event.get("metadata", {})
            booking_id = metadata.get("bookingId")
            
            if booking_id:
                db: Session
                with db_session as db:
                    booking = db.query(PeerCounsellorBooking).filter_by(id=int(booking_id)).first()
                    if booking:
                        booking.payment_status = "failed"
                        db.commit()
                        logging.info(f"Booking {booking_id} marked as failed")
        
        return {"status": "ok", "message": "Webhook processed"}
        
    except Exception as e:
        logging.error(f"Webhook processing error: {e}")
        # Return 200 to avoid Dodo retrying the webhook
        return {"status": "error", "message": str(e)}

@app.get("/debug/payment/{booking_id}", tags=["payments"])
def debug_payment_status(booking_id: str, db_session=Depends(get_db)):
    db: Session
    with db_session as db:
        booking = db.query(PeerCounsellorBooking).filter_by(id=int(booking_id)).first()
        if not booking:
            return {"error": "Booking not found"}
        return {
            "booking_id": booking.id,
            "payment_status": booking.payment_status,
            "user_email": booking.user_email,
            "amount": "Check counsellor charges",
            "slot_date": booking.slot_date.isoformat()
        }


