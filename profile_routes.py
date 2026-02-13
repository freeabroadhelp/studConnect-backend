"""
Profile API Routes

Endpoints to save/update and fetch user profiles from MongoDB.
Collection: profiles (in yournextuniversity database)
"""

from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Body
from fastapi.responses import JSONResponse
from typing import Dict, Any

from db_mongo import profiles_collection

router = APIRouter(prefix="/api/profile", tags=["profile"])


# ─────────────────────────────────────────────
# GET /api/profile/{user_id}
# ─────────────────────────────────────────────
@router.get("/{user_id}", summary="Fetch user profile")
async def get_profile(user_id: str):
    """
    Return profile for the given user_id.
    Returns empty object with status 200 if not found.
    """
    try:
        profile = await profiles_collection.find_one(
            {"user_id": user_id},
            {"_id": 0}  # exclude Mongo ObjectId
        )
        return profile if profile else {}

    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": f"Database error: {str(e)}"},
        )


# ─────────────────────────────────────────────
# POST /api/profile
# ─────────────────────────────────────────────
@router.post("", summary="Create or update user profile")
async def save_profile(payload: Dict[str, Any] = Body(...)):
    """
    Create or update a profile document.
    Uses user_id as the unique key with upsert.
    """
    user_id = payload.get("user_id")
    if not user_id:
        raise HTTPException(status_code=400, detail="user_id is required")

    try:
        # Build the document from allowed fields
        profile_data = {
            "user_id": user_id,
            "first_name": payload.get("first_name"),
            "last_name": payload.get("last_name"),
            "email": payload.get("email"),
            "phone": payload.get("phone"),
            "date_of_birth": payload.get("date_of_birth"),
            "gender": payload.get("gender"),
            "address": payload.get("address"),
            "city": payload.get("city"),
            "postal_code": payload.get("postal_code"),
            "country": payload.get("country"),
            "updated_at": datetime.now(timezone.utc),
        }

        # Remove None values so partial updates don't overwrite with null
        profile_data = {k: v for k, v in profile_data.items() if v is not None}

        await profiles_collection.update_one(
            {"user_id": user_id},
            {"$set": profile_data},
            upsert=True,
        )

        return {"status": "ok", "message": "Profile saved"}

    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": f"Database error: {str(e)}"},
        )
