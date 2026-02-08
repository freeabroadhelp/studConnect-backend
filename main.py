from fastapi import FastAPI, Depends, HTTPException, Depends, Header, Query, Path, Request, Body, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime, timedelta
from recommendation.routes import router as recommendation_router
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
from db import Base, engine, get_db  # engine used only at startup for create_all
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

app.include_router(recommendation_router)

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


@app.on_event("startup")
def startup_create_tables():
    """Create DB tables on startup; avoids connection at import time (Neon-friendly)."""
    Base.metadata.create_all(bind=engine)


DB_URL = os.environ.get("DATABASE_URL")
session = boto3.session.Session()

logging.basicConfig(level=logging.INFO)

def generate_otp(length: int = 6) -> str:
    return "".join(random.choices(string.digits, k=length))

@app.post("/auth/register", response_model=dict, tags=["auth"], summary="Register & send OTP")
def register(payload: UserRegister, db_session=Depends(get_db)):
    """Register a new user or resend OTP for unverified user."""
    email = payload.email.lower().strip()
    
    db: Session
    with db_session as db:
        existing = get_user_by_email(db, email)
        
        if existing:
            if existing.is_verified:
                raise HTTPException(status_code=400, detail="Email already registered")
            # Update existing unverified user
            user = existing
            user.full_name = payload.full_name
            user.role = payload.role
            user.password_hash = hash_password(payload.password)
            logging.info(f"[REGISTER] Updated existing unverified user: {email}")
        else:
            # Create new user
            user = create_user(
                db,
                email=email,
                full_name=payload.full_name,
                role=payload.role,
                password_hash=hash_password(payload.password),
            )
            logging.info(f"[REGISTER] Created new user: {email}")
        
        # Generate and set OTP
        code = generate_otp()
        user.set_otp(code)
        logging.info(f"[REGISTER] OTP generated for: {email}")
        
        # Commit user + OTP to database
        db.commit()
        logging.info(f"[REGISTER] Commit successful for: {email}, user_id={user.id}")
    
    # Send OTP email (after commit, outside transaction)
    email_sent = send_otp(user.email, code)
    logging.info(f"[REGISTER] Email send result for {email}: {email_sent}")
    
    if not email_sent:
        raise HTTPException(status_code=500, detail="Could not send verification email (check SMTP settings)")
    
    return {"message": "OTP sent to email for verification"}

@app.post("/auth/verify-otp", response_model=dict, tags=["auth"], summary="Verify OTP")
def verify_otp_route(payload: UserVerify, db_session=Depends(get_db)):
    """Verify OTP and mark user as verified."""
    email = payload.email.lower().strip()
    
    db: Session
    with db_session as db:
        logging.info(f"[VERIFY-OTP] Verification attempt for: {email}")
        
        # Find user
        user = get_user_by_email(db, email)
        if not user:
            logging.warning(f"[VERIFY-OTP] User not found: {email}")
            raise HTTPException(status_code=404, detail="User not found")
        
        # Already verified
        if user.is_verified:
            logging.info(f"[VERIFY-OTP] Already verified: {email}")
            return {"message": "Email already verified", "verified": True}
        
        # No OTP pending
        if not user.otp_code or not user.otp_expires:
            logging.warning(f"[VERIFY-OTP] No OTP pending for: {email}")
            raise HTTPException(status_code=400, detail="No OTP pending. Please request a new one.")
        
        # OTP expired
        if datetime.utcnow() > user.otp_expires:
            logging.warning(f"[VERIFY-OTP] OTP expired for: {email}")
            raise HTTPException(status_code=400, detail="OTP expired. Please request a new one.")
        
        # Invalid OTP
        if payload.code.strip() != user.otp_code:
            logging.warning(f"[VERIFY-OTP] Invalid OTP for: {email}")
            raise HTTPException(status_code=400, detail="Invalid OTP")
        
        # Valid OTP - update user
        try:
            user.is_verified = True
            user.otp_code = None
            user.otp_expires = None
            db.commit()
            db.refresh(user)
            logging.info(f"[VERIFY-OTP] Commit successful, user verified: {email}, user_id={user.id}")
        except Exception as e:
            db.rollback()
            logging.error(f"[VERIFY-OTP] Commit failed for {email}: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail="Verification failed. Please try again.")
    
    return {"message": "Email verified successfully", "verified": True}

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
            "created_at": user.created_at,
            "avatar_url": user.avatar_url,
            "phone": user.phone,
            "gender": user.gender,
            "date_of_birth": user.date_of_birth,
            "address": user.address,
            "city": user.city,
            "postal_code": user.postal_code,
            "country": user.country
        }
        return UserOut.model_validate(payload)

@app.get("/users/me", response_model=UserOut, tags=["users"], summary="Current user")
def me(current: UserOut = Depends(auth_user)):
    return current


@app.put("/users/update", response_model=UserOut, tags=["users"], summary="Update user profile")
async def update_user_profile(
    user_update: dict = Body(...),
    current_user: UserOut = Depends(auth_user),
    db_session=Depends(get_db)
):
    from fastapi import HTTPException
    from sqlalchemy.orm import Session
    from models.models_user import User
    from db_mongo import users_collection
    from bson import ObjectId
    
    # Update user record in MongoDB
    mongo_user_data = {
        "full_name": user_update.get("full_name"),
        "first_name": user_update.get("first_name"),
        "last_name": user_update.get("last_name"),
        "phone": user_update.get("phone"),
        "gender": user_update.get("gender"),
        "date_of_birth": user_update.get("date_of_birth"),
        "address": user_update.get("address"),
        "city": user_update.get("city"),
        "postal_code": user_update.get("postal_code"),
        "country": user_update.get("country"),
        "avatar_url": user_update.get("avatar_url"),
        "updated_at": datetime.utcnow()
    }
    
    # Remove None values
    mongo_user_data = {k: v for k, v in mongo_user_data.items() if v is not None}
    
    # Update user in MongoDB collection
    result = await users_collection.update_one(
        {"user_id": current_user.id},
        {"$set": mongo_user_data},
        upsert=True
    )
    
    # Also update in PostgreSQL for consistency
    db: Session
    with db_session as db:
        user = db.query(User).filter(User.id == current_user.id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Update fields if they exist in the request
        if "full_name" in user_update:
            user.full_name = user_update["full_name"]
        if "phone" in user_update:
            user.phone = user_update.get("phone")
        if "gender" in user_update:
            user.gender = user_update.get("gender")
        if "date_of_birth" in user_update:
            user.date_of_birth = user_update.get("date_of_birth")
        if "address" in user_update:
            user.address = user_update.get("address")
        if "city" in user_update:
            user.city = user_update.get("city")
        if "postal_code" in user_update:
            user.postal_code = user_update.get("postal_code")
        if "country" in user_update:
            user.country = user_update.get("country")
        if "avatar_url" in user_update:
            user.avatar_url = user_update.get("avatar_url")
        
        db.commit()
        db.refresh(user)
        
        # Return updated user data
        return UserOut(
            id=str(user.id),
            email=user.email,
            full_name=user.full_name,
            role=user.role,
            is_verified=user.is_verified,
            created_at=user.created_at,
            avatar_url=user.avatar_url
        )


@app.post("/users/upload-avatar", response_model=dict, tags=["users"], summary="Upload user avatar")
async def upload_avatar(
    file: UploadFile = File(...),
    current_user: UserOut = Depends(auth_user),
    db_session=Depends(get_db)
):
    from fastapi import HTTPException
    from sqlalchemy.orm import Session
    from models.models_user import User
    from db_mongo import users_collection
    import uuid
    import os
    from urllib.parse import quote
    from bson import ObjectId
    
    # Validate file type
    allowed_types = ["image/jpeg", "image/png", "image/gif", "image/webp"]
    if file.content_type not in allowed_types:
        raise HTTPException(status_code=400, detail="Invalid file type. Only JPEG, PNG, GIF, and WEBP are allowed.")
    
    # Validate file size (max 5MB)
    # Read the file to check size
    content = await file.read()
    if len(content) > 5 * 1024 * 1024:  # 5MB
        raise HTTPException(status_code=400, detail="File size exceeds 5MB limit")
    
    # Reset file pointer after reading
    await file.seek(0)
    
    # Generate unique filename
    ext = os.path.splitext(file.filename)[1]
    unique_filename = f"avatars/{current_user.id}_{uuid.uuid4()}{ext}"
    
    # For now, we'll simulate storing the URL in the MongoDB
    avatar_url = f"/uploads/{unique_filename}"
    
    # Update user record in MongoDB
    user_data = {
        "avatar_url": avatar_url,
        "updated_at": datetime.utcnow()
    }
    
    # Update user in MongoDB collection
    result = await users_collection.update_one(
        {"user_id": current_user.id},
        {"$set": user_data},
        upsert=True
    )
    
    # Also update in PostgreSQL for consistency
    db: Session
    with db_session as db:
        user = db.query(User).filter(User.id == current_user.id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        user.avatar_url = avatar_url
        db.commit()
        db.refresh(user)
        
        return {"avatar_url": user.avatar_url}


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
    school_id: int,
    db_session=Depends(get_db)
):
   
    db: Session
    with db_session as db:
        uni = db.query(UniversityModel).filter(UniversityModel.id == school_id).first()
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
    school_id: Optional[int] = Query(None, description="Filter by school ID"),
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
        from sqlalchemy import cast, Float, func
        with db_session as db:
            query = db.query(ProgramDetail)

            if school_id is not None:
                query = query.filter(ProgramDetail.school_id == school_id)

            if university_name:
                query = query.filter(
                    func.jsonb_extract_path_text(ProgramDetail.school, 'name').ilike(f"%{university_name}%")
                )

            if program_name:
                query = query.filter(
                    func.jsonb_extract_path_text(ProgramDetail.attributes, 'name').ilike(f"%{program_name}%")
                )

            if country:
                query = query.filter(
                    func.jsonb_extract_path_text(ProgramDetail.school, 'country').ilike(f"%{country}%")
                )

            if min_fees is not None:
                query = query.filter(
                    func.jsonb_extract_path_text(ProgramDetail.attributes, 'tuition') != None
                ).filter(
                    cast(func.jsonb_extract_path_text(ProgramDetail.attributes, 'tuition'), Float) >= min_fees
                )

            if max_fees is not None:
                query = query.filter(
                    func.jsonb_extract_path_text(ProgramDetail.attributes, 'tuition') != None
                ).filter(
                    cast(func.jsonb_extract_path_text(ProgramDetail.attributes, 'tuition'), Float) <= max_fees
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
    # Support both new 'code' flow and legacy 'token' flow for backward compatibility during transition
    code = payload.get("code")
    token = payload.get("token")
    redirect_uri = payload.get("redirect_uri")

    GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID")
    GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET")
    
    # DEBUG LOGGING
    logging.info(f"OAuth Payload: {payload}")
    logging.info(f"Redirect URI from payload: {redirect_uri}")
    logging.info(f"GOOGLE_CLIENT_ID present: {bool(GOOGLE_CLIENT_ID)}")
    if GOOGLE_CLIENT_ID:
        logging.info(f"GOOGLE_CLIENT_ID (masked): ...{GOOGLE_CLIENT_ID[-4:]}")
    logging.info(f"GOOGLE_CLIENT_SECRET present: {bool(GOOGLE_CLIENT_SECRET)}")

    if not GOOGLE_CLIENT_ID:
        raise HTTPException(status_code=500, detail="Google client ID not configured")

    id_token_str = None

    # 1. New Flow: Server-side Code Exchange
    if code:
        if not GOOGLE_CLIENT_SECRET:
            raise HTTPException(status_code=500, detail="Google client secret not configured")
        
        try:
            # Exchange auth code for tokens
            token_endpoint = "https://oauth2.googleapis.com/token"
            token_data = {
                "code": code,
                "client_id": GOOGLE_CLIENT_ID,
                "client_secret": GOOGLE_CLIENT_SECRET,
                "redirect_uri": redirect_uri if redirect_uri else "postmessage", # 'postmessage' is often used for SPA or infer from header
                "grant_type": "authorization_code",
            }

            print("DEBUG redirect_uri:", token_data["redirect_uri"])
            print("DEBUG GOOGLE_CLIENT_ID:", token_data["client_id"])
            print("DEBUG CLIENT_SECRET_PRESENT:", bool(token_data["client_secret"]))
            
            import requests # Import here to ensure it's available
            response = requests.post(token_endpoint, data=token_data)
            
            if not response.ok:
                logging.error(f"Google token exchange failed: {response.text}")
                raise HTTPException(status_code=401, detail="Failed to exchange authorization code")
                
            tokens = response.json()
            id_token_str = tokens.get("id_token")
            
        except Exception as e:
            logging.error(f"Google OAuth error: {str(e)}")
            raise HTTPException(status_code=401, detail=f"Google OAuth failed: {str(e)}")

    # 2. Legacy Flow: Client-side Token (Deprecating)
    elif token:
        id_token_str = token
    
    else:
         raise HTTPException(status_code=400, detail="Missing Google code or token")

    if not id_token_str:
        raise HTTPException(status_code=401, detail="No ID token obtained")

    # 3. Verify ID Token
    try:
        idinfo = id_token.verify_oauth2_token(id_token_str, google_requests.Request(), GOOGLE_CLIENT_ID)
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
            for field, value in payload.items():
                if hasattr(peer, field) and value is not None:
                    setattr(peer, field, value)
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
        existing_slots = db.query(PeerCounsellorAvailability).filter_by(counsellor_id=counsellor_id).all()
        slot_ids = [slot.id for slot in existing_slots]
        referenced_slot_ids = set(
            r[0] for r in db.query(PeerCounsellorBooking.slot_id)
            .filter(PeerCounsellorBooking.counsellor_id == counsellor_id)
            .filter(PeerCounsellorBooking.slot_id.in_(slot_ids))
            .all()
        )
        deletable_slot_ids = set(slot_ids) - referenced_slot_ids
        if deletable_slot_ids:
            db.query(PeerCounsellorAvailability).filter(
                PeerCounsellorAvailability.counsellor_id == counsellor_id,
                PeerCounsellorAvailability.id.in_(deletable_slot_ids)
            ).delete(synchronize_session=False)
        for slot in slots:
            db.add(PeerCounsellorAvailability(
                counsellor_id=counsellor_id,
                day_of_week=slot["day_of_week"],
                start_time=slot["start_time"],
                end_time=slot["end_time"]
            ))
        db.commit()
        return {
            "status": "ok",
            "count": len(slots),
            "skipped_existing_slots": list(referenced_slot_ids)
        }

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

        try:
            subject = "Your Peer Counselling Booking Request"
            message = (
                f"Dear {booking.user_email},\n\n"
                f"Your booking request has been received for {booking.slot_date.strftime('%A, %d %B %Y at %H:%M')}.\n"
                f"Status: {booking.payment_status}\n"
                f"Peer Counsellor: {booking.counsellor_email}\n\n"
                f"Thank you for booking with us!\n"
            )
            send_email(
                to_email=booking.user_email,
                subject=subject,
                message=message
            )
        except Exception as e:
            logging.error(f"Failed to send booking email to candidate: {e}")

        try:
            subject = "A New Booking Has Been Made With You"
            message = (
                f"Dear {booking.counsellor_email},\n\n"
                f"A student ({booking.user_email}) has booked a session with you.\n"
                f"Date & Time: {booking.slot_date.strftime('%A, %d %B %Y at %H:%M')}\n"
                f"Status: {booking.payment_status}\n\n"
                f"Please check your dashboard for details.\n\n"
                f"Thank you for supporting students!\n"
            )
            send_email(
                to_email=booking.counsellor_email,
                subject=subject,
                message=message
            )
        except Exception as e:
            logging.error(f"Failed to send booking email to peer counsellor: {e}")

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


import httpx
import os
import json
import logging
from fastapi import HTTPException
from pydantic import BaseModel
import socket
import asyncio

logging.basicConfig(level=logging.INFO)

DODO_API_KEY = os.getenv("DODO_PAYMENTS_API_KEY")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")
BACKEND_URL = os.getenv("BACKEND_URL", "https://studconnect-backend.onrender.com")

class Customer(BaseModel):
    name: str
    email: str
    phone: str = None

class PaymentRequest(BaseModel):
    amount: float
    customer: Customer
    booking_id: str
    discount_code: str = None

def _resolve_host(host: str) -> tuple[bool, str | None]:
    try:
        ip = socket.gethostbyname(host)
        return True, ip
    except Exception as e:
        return False, str(e)

def _dodo_base_urls() -> list[str]:
    return ["https://live.dodopayments.com"]

async def _http_post_with_retry(
    url: str,
    headers: dict,
    payload: dict,
    attempts: int = 3
) -> httpx.Response:
   
    for attempt in range(1, attempts + 1):
        try:
            timeout = httpx.Timeout(
                connect=10.0,
                read=25.0,
                write=10.0,
                pool=10.0
            )
            limits = httpx.Limits(max_keepalive_connections=5, max_connections=10)
            async with httpx.AsyncClient(timeout=timeout, limits=limits, follow_redirects=True) as client:
                return await client.post(url, json=payload, headers=headers)
        except (httpx.TimeoutException, httpx.ConnectError) as e:
            if attempt == attempts:
                raise
            backoff = 2 ** (attempt - 1)
            logging.warning(f"[Dodo LIVE] attempt {attempt} failed ({e}); retrying in {backoff}s")
            await asyncio.sleep(backoff)

@app.post("/api/create-dodo-session", tags=["payments"])
async def create_dodo_session(request: PaymentRequest):
    """
    Live-only Dodo checkout session creation.
    - Requires a live API key (sk_live_*)
    - Single endpoint: https://live.dodopayments.com/checkouts
    """
    try:
        if not request.booking_id or not request.amount or request.amount <= 0:
            raise HTTPException(status_code=400, detail="Invalid booking ID or amount")
        if not request.customer.email or not request.customer.name:
            raise HTTPException(status_code=400, detail="Customer email and name are required")
        api_key = DODO_API_KEY
        if not api_key or len(api_key) < 10:
            raise HTTPException(status_code=500, detail="Payment gateway not configured (missing API key)")
        if api_key.startswith("sk_test_"):
            raise HTTPException(status_code=400, detail="Test API key provided. Set a live key (sk_live_...).")

        discount = 0
        if request.discount_code and request.discount_code.lower() == "save50":
            discount = 50
        final_amount = max(request.amount - discount, 0)

        base_url = _dodo_base_urls()[0]  # live only
        host = base_url.replace("https://", "").split("/")[0]
        ok_dns, dns_msg = _resolve_host(host)
        if not ok_dns:
            raise HTTPException(
                status_code=503,
                detail=f"DNS resolution failed for {host}: {dns_msg}\n"
                       "Resolution steps:\n"
                       "  1. Verify outbound DNS/network access to live.dodopayments.com:443\n"
                       "  2. Ensure no firewall blocks egress\n"
                       "  3. Retry after network stabilization\n"
                       "  4. Contact hosting + Dodo support with this message"
            )

        payload = {
            "product_cart": [
                {
                    "product_id": "pdt_isuaGsszAodjHrUaplbG4",
                    "quantity": 1
                }
            ],
            "customer": {
                "email": request.customer.email,
                "name": request.customer.name
            },
            "billing_address": {
                "city": "Delhi",
                "country": "IN",
                "state": "Delhi",
                "street": "100, New Park",
                "zipcode": "110001"
            },
            "billing_currency": "INR",
            "return_url": f"{FRONTEND_URL}/payment-status?bookingId={request.booking_id}",
            "metadata": {
                "bookingId": str(request.booking_id),
                "service": "peer_counselling",
                "platform": "studconnect",
                "amount": str(final_amount),
                "discount_code": request.discount_code or "",
                "customer_phone": request.customer.phone or "",
                "customer_email": request.customer.email,
                "customer_name": request.customer.name
            },
            "confirm": True,
            "allowed_payment_method_types": ["credit","debit","upi_collect","upi_intent","apple_pay","cashapp","google_pay"],
            "show_saved_payment_methods": False
        }

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "StudConnect/1.0"
        }

        endpoint = f"{base_url}/checkouts"
        logging.info(f"[Dodo LIVE] POST {endpoint}")

        resp = await _http_post_with_retry(endpoint, headers, payload, attempts=3)
        body_text = resp.text
        logging.info(f"[Dodo LIVE] Status {resp.status_code}")

        if resp.status_code in (200, 201):
            try:
                data = resp.json()
            except json.JSONDecodeError:
                raise HTTPException(status_code=502, detail="Invalid JSON from payment gateway")

            checkout_url = (
                data.get("checkout_url") or
                data.get("url") or
                data.get("payment_url") or
                data.get("redirect_url")
            )
            session_id = (
                data.get("session_id") or
                data.get("id") or
                data.get("checkout_session_id")
            )
            if not checkout_url:
                raise HTTPException(status_code=502, detail="Missing checkout_url in gateway response")

            return {
                "checkout_url": checkout_url,
                "session_id": session_id,
                "booking_id": request.booking_id,
                "amount": final_amount,
                "status": "success",
                "payment_type": "dodo",
                "environment": "live",
                "discount_applied": discount
            }

        if resp.status_code == 401:
            raise HTTPException(status_code=500, detail="Gateway authentication failed. Verify live API key.")
        if resp.status_code == 400:
            try:
                err_json = resp.json()
                msg = err_json.get("message") or err_json.get("error") or body_text[:200]
            except:
                msg = body_text[:200]
            raise HTTPException(status_code=400, detail=f"Gateway validation error: {msg}")

        raise HTTPException(
            status_code=502,
            detail=f"Unexpected gateway status {resp.status_code}: {body_text[:250]}"
        )

    except HTTPException:
        raise
    except (httpx.TimeoutException, httpx.ConnectError) as e:
        raise HTTPException(
            status_code=503,
            detail=f"Network error reaching Dodo live endpoint: {e}\n"
                   "Check outbound connectivity, firewall, and retry."
        )
    except Exception as e:
        logging.error(f"[Dodo LIVE] Unhandled exception: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal payment processing error: {e}")

@app.get("/debug/dodo-status", tags=["payments"])
def dodo_status():
    key = DODO_API_KEY or ""
    return {
        "api_key_present": bool(key),
        "api_key_prefix": key[:10] + "..." if key else None,
        "is_live_key": key.startswith("sk_live_"),
        "warning": None if (key and key.startswith("sk_live_")) else "Provide a live key (sk_live_*) for production.",
        "endpoint_used": "https://live.dodopayments.com/checkouts",
        "product_id": "pdt_isuaGsszAodjHrUaplbG4",
        "timestamp": datetime.utcnow().isoformat()
    }

import base64

ZOOM_ACCOUNT_ID = os.getenv("ZOOM_ACCOUNT_ID")
ZOOM_CLIENT_ID = os.getenv("ZOOM_CLIENT_ID")
ZOOM_CLIENT_SECRET = os.getenv("ZOOM_CLIENT_SECRET")

_zoom_cache = {"token": None, "exp": None}

async def get_zoom_token() -> str:
    if not (ZOOM_ACCOUNT_ID and ZOOM_CLIENT_ID and ZOOM_CLIENT_SECRET):
        raise RuntimeError("Zoom credentials missing")
    now = datetime.utcnow()
    if _zoom_cache["token"] and _zoom_cache["exp"] and now < _zoom_cache["exp"]:
        return _zoom_cache["token"]
    auth_bytes = f"{ZOOM_CLIENT_ID}:{ZOOM_CLIENT_SECRET}".encode()
    auth_header = base64.b64encode(auth_bytes).decode()
    url = f"https://zoom.us/oauth/token?grant_type=account_credentials&account_id={ZOOM_ACCOUNT_ID}"
    async with httpx.AsyncClient(timeout=15.0) as client:
        r = await client.post(url, headers={"Authorization": f"Basic {auth_header}"})
        if r.status_code != 200:
            raise RuntimeError(f"Zoom token error {r.status_code}: {r.text[:150]}")
        data = r.json()
        _zoom_cache["token"] = data.get("access_token")
        _zoom_cache["exp"] = now + timedelta(seconds=data.get("expires_in", 3600) - 60)
        return _zoom_cache["token"]

async def create_zoom_meeting(slot_dt: datetime, student_email: str, counsellor_email: str) -> dict:
    token = await get_zoom_token()
    payload = {
        "topic": "Peer Counselling Session",
        "type": 2,
        "start_time": slot_dt.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "duration": 30,
        "timezone": "UTC",
        "agenda": f"Session: {student_email} with {counsellor_email}",
        "settings": {"host_video": True, "participant_video": True, "waiting_room": True}
    }
    async with httpx.AsyncClient(timeout=20.0) as client:
        r = await client.post("https://api.zoom.us/v2/users/me/meetings",
                              headers={"Authorization": f"Bearer {token}",
                                       "Content-Type": "application/json"},
                              json=payload)
        if r.status_code not in (200, 201):
            raise RuntimeError(f"Zoom meeting error {r.status_code}: {r.text[:200]}")
        jd = r.json()
        return {"join_url": jd.get("join_url"), "start_url": jd.get("start_url"), "id": jd.get("id")}

@app.post("/webhook/dodo", tags=["payments"])
async def dodo_webhook(request: Request, db_session=Depends(get_db)):
    
    try:
        raw = await request.body()
        logging.info(f"[Dodo WEBHOOK] Raw: {raw[:500].decode(errors='ignore')}")
        try:
            event = json.loads(raw.decode())
        except json.JSONDecodeError:
            return {"status": "error", "message": "Invalid JSON"}
        event_type = event.get("event") or event.get("type")
        data = event.get("data") or {}
        metadata = data.get("metadata") or {}
        booking_id = metadata.get("bookingId") or metadata.get("booking_id")
        if not booking_id:
            return {"status": "ignored", "message": "No bookingId in metadata"}

        if event_type not in ("checkout.session.completed", "payment.succeeded"):
            return {"status": "ignored", "message": f"Event {event_type} not processed"}

        db: Session
        with db_session as db:
            booking = db.query(PeerCounsellorBooking).filter_by(id=int(booking_id)).first()
            if not booking:
                return {"status": "error", "message": "Booking not found"}
            if booking.payment_status == "paid" and booking.meeting_link:
                return {"status": "ok", "message": "Already processed"}

            booking.payment_status = "paid"

            meeting_link = None
            try:
                zoom_info = await create_zoom_meeting(booking.slot_date, booking.user_email, booking.counsellor_email)
                meeting_link = zoom_info["join_url"]
                booking.meeting_link = meeting_link
            except Exception as ze:
                logging.error(f"[Zoom] Failed to create meeting for booking {booking.id}: {ze}")

            db.commit()
            db.refresh(booking)

            slot_time_disp = booking.slot_date.strftime("%A, %d %B %Y at %H:%M UTC")
            student_msg = (
                f"Dear {booking.user_email},\n\n"
                f"Payment confirmed. Your session is booked.\n"
                f"Date & Time: {slot_time_disp}\n"
                f"Meeting Link: {booking.meeting_link or 'Pending'}\n\n"
                f"Please join 5 minutes early.\n\nStudConnect"
            )
            counsellor_msg = (
                f"Dear {booking.counsellor_email},\n\n"
                f"A paid session has been booked.\n"
                f"Student: {booking.user_email}\n"
                f"Date & Time: {slot_time_disp}\n"
                f"Meeting Link: {booking.meeting_link or 'Pending'}\n\n"
                f"Please be ready.\n\nStudConnect"
            )
            try:
                send_email(booking.user_email, "Session Confirmed & Meeting Link", student_msg)
            except Exception as e:
                logging.error(f"[Email] Student send failed: {e}")
            try:
                send_email(booking.counsellor_email, "New Paid Session Booked", counsellor_msg)
            except Exception as e:
                logging.error(f"[Email] Counsellor send failed: {e}")

            return {
                "status": "success",
                "booking_id": booking.id,
                "payment_status": booking.payment_status,
                "meeting_link": booking.meeting_link
            }
    except Exception as e:
        logging.error(f"[Dodo WEBHOOK] Unhandled: {e}", exc_info=True)
        return {"status": "error", "message": str(e)}

@app.get("/peer-counsellors/booking-status", tags=["peer-counsellors"])
def booking_status(booking_id: int = Query(...), db_session=Depends(get_db)):
    db: Session
    with db_session as db:
        b = db.query(PeerCounsellorBooking).filter_by(id=booking_id).first()
        if not b:
            raise HTTPException(status_code=404, detail="Booking not found")
        return {
            "booking_id": b.id,
            "payment_status": b.payment_status,
            "meeting_link": b.meeting_link,
            "slot_date": b.slot_date.isoformat()
        }

@app.get("/peer-counsellors/student-bookings", tags=["peer-counsellors"])
def get_student_bookings(
    user_id: int = Query(None, description="Student user ID"),
    user_email: str = Query(None, description="Student email"),
    db_session=Depends(get_db)
):
    """
    Get all peer counsellor bookings for a student by user_id or user_email.
    At least one of user_id or user_email must be provided.
    """
    if not user_id and not user_email:
        raise HTTPException(status_code=400, detail="user_id or user_email is required")
    db: Session
    with db_session as db:
        query = db.query(PeerCounsellorBooking)
        if user_id:
            query = query.filter(PeerCounsellorBooking.user_id == user_id)
        if user_email:
            query = query.filter(PeerCounsellorBooking.user_email == user_email)
        bookings = query.order_by(PeerCounsellorBooking.slot_date.desc()).all()
        return [
            {
                "id": b.id,
                "user_id": b.user_id,
                "user_email": b.user_email,
                "counsellor_id": b.counsellor_id,
                "counsellor_email": b.counsellor_email,
                "slot_id": b.slot_id,
                "slot_date": b.slot_date.isoformat(),
                "payment_status": b.payment_status,
                "meeting_link": b.meeting_link,
                "created_at": b.created_at.isoformat()
            }
            for b in bookings
        ]

@app.get("/api/university-compare/search", tags=["university-compare"])
def search_universities(
    q: str = Query(..., description="Search query for university name"),
    limit: int = Query(15, ge=1, le=50, description="Maximum number of results"),
    db_session=Depends(get_db)
):
    """
    Search universities by name with case-insensitive partial matching.
    Returns id, name, country, and logo for matching universities.
    """
    try:
        db: Session
        with db_session as db:
            from sqlalchemy import func
            
            # Build query with JSONB text extraction and ILIKE search
            name_field = func.jsonb_extract_path_text(UniversityModel.attributes, 'name')
            query = db.query(UniversityModel).filter(
                name_field.ilike(f"%{q}%")
            ).limit(limit)
            
            universities = query.all()
            
            # Format response
            results = []
            for uni in universities:
                attributes = uni.attributes or {}
                results.append({
                    "id": str(uni.id),
                    "name": attributes.get("name"),
                    "country": attributes.get("country"),
                    "logo": attributes.get("logo")
                })
            
            return results
            
    except Exception as e:
        logging.error(f"University search error: {e}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"error": f"Failed to search universities: {str(e)}"}
        )