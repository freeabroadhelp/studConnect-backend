"""
Recommendation API Routes

Exposes the recommendation engine via REST API.
Single endpoint: POST /recommendations
"""

from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Body
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from db import get_db
from .logic.contracts import StudentProfile, RecommendationOutput
from .logic.runner import run_recommendations, get_recommendations_simple


router = APIRouter(prefix="/recommendations", tags=["recommendations"])


# =============================================================================
# REQUEST/RESPONSE SCHEMAS
# =============================================================================

class RecommendationRequest(BaseModel):
    """Request body for recommendations endpoint."""
    student_profile: Dict[str, Any] = Field(
        ...,
        description="Student profile with preferences",
        example={
            "academic_score_band": "good",
            "language_score_band": "good",
            "background_field": "Computer Science",
            "work_experience_years": 2.0,
            "preferred_countries": ["Germany", "Canada"],
            "preferred_program_domains": ["Computer Science", "Data Science"],
            "tuition_preference_band": "moderate"
        }
    )
    limit: int = Field(
        default=50,
        ge=1,
        le=200,
        description="Max programs to evaluate"
    )
    format: str = Field(
        default="full",
        description="Response format: 'full' (complete output) or 'simple' (list only)"
    )
    explain: bool = Field(
        default=False,
        description="Include AI-generated explanation"
    )

# ... (imports)
from .ai.explainer import explainer

# =============================================================================
# ENDPOINTS
# =============================================================================

@router.post("", summary="Get program recommendations")
@router.post("/", summary="Get program recommendations", include_in_schema=False)
def get_recommendations(
    request: RecommendationRequest,
    db_session=Depends(get_db)
):
    """
    Generate personalized program recommendations based on student profile.
    
    **Request Body:**
    - `student_profile`: Student's academic profile and preferences
    - `limit`: Maximum number of programs to evaluate (default: 50)
    - `format`: Response format - 'full' or 'simple'
    - `explain`: Include AI-generated explanation (default: False)
    
    **Response:**
    - Ranked recommendations categorized as Ambitious/Target/Safe
    - Dimension scores and risk factors for each recommendation
    - AI explanation (if requested)
    """
    try:
        db: Session = db_session
        
        # Parse student profile
        try:
            profile = StudentProfile(**request.student_profile)
        except Exception as e:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid student profile: {str(e)}"
            )
        
        # Run recommendation pipeline
        if request.format == "simple":
            results = get_recommendations_simple(db, profile, request.limit)
            return {
                "recommendations": results,
                "count": len(results)
            }
        else:
            output = run_recommendations(db, profile, request.limit)
            
            # Convert to JSON-serializable dict
            response_data = {
                "request_id": output.request_id,
                "student_id": output.student_id,
                "summary": {
                    "total_evaluated": output.total_candidates_evaluated,
                    "total_eligible": output.total_eligible,
                    "total_recommended": output.total_recommended,
                    "processing_time_ms": output.processing_time_ms,
                },
                "recommendations": [_serialize_recommendation(r) for r in output.all_recommendations],
                "warnings": output.warnings,
                "engine_version": output.engine_version,
            }

            # AI Explanation Layer
            if request.explain:
                explanation = explainer.get_explanation(
                    request_id=output.request_id,
                    student_profile=request.student_profile,
                    engine_output=response_data
                )
                if explanation:
                    response_data["ai_explanation"] = explanation
            
            return response_data
            
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        return JSONResponse(
            status_code=500,
            content={"error": str(e), "trace": traceback.format_exc()}
        )


def _serialize_recommendation(rec) -> Dict[str, Any]:
    """Convert ProgramRecommendation to JSON-serializable dict."""
    return {
        "rank": rec.rank,
        "program_id": rec.program_id,
        "university_id": rec.university_id,
        "university_name": rec.university_name,
        "program_name": rec.program_name,
        "degree_type": rec.degree_type,
        "country": rec.country,
        "city": rec.city,
        "classification": rec.fit_category,
        "total_score": round(rec.overall_score, 3),
        "confidence_level": round(rec.confidence_level, 2),
        "dimension_scores": {
            d.dimension: {
                "score": round(d.score, 3),
                "weight": d.weight,
                "weighted_score": round(d.weighted_score, 3),
            }
            for d in rec.dimension_scores
        },
        "risk_factors": [
            {"factor": r.factor, "severity": r.severity, "description": r.description}
            for r in rec.risk_factors
        ],
        "improvement_suggestions": [
            {"area": s.area, "suggestion": s.suggestion, "impact": s.impact}
            for s in rec.improvement_suggestions
        ],
        "tuition_fee_band": rec.tuition_fee_band,
        "intake_term": rec.intake_term,
        "intake_year": rec.intake_year,
        "application_deadline": rec.application_deadline.isoformat() if rec.application_deadline else None,
    }


# =============================================================================
# HEALTH CHECK
# =============================================================================

@router.get("/health", summary="Recommendation engine health check")
def health_check():
    """Check if recommendation engine is operational."""
    return {"status": "ok", "engine": "recommendation", "version": "1.0.0"}
