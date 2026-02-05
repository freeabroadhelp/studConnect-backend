"""
Data Contracts for the Recommendation Scoring Engine

Defines Pydantic models for StudentProfile (input) and RecommendationOutput (output).
These contracts are the API boundary for the scoring engine.
"""

from datetime import date
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum

from .constants import FitCategory


# =============================================================================
# INPUT CONTRACTS
# =============================================================================

class DegreeLevel(str, Enum):
    """Student's current or target degree level."""
    BACHELORS = "bachelors"
    MASTERS = "masters"
    PHD = "phd"
    DIPLOMA = "diploma"


class StudentProfile(BaseModel):
    """
    Input contract for the scoring engine.
    Represents a student's academic profile and preferences.
    """
    # Identity (optional, for tracking)
    student_id: Optional[str] = None
    
    # Academic Background
    current_degree_level: DegreeLevel = DegreeLevel.BACHELORS
    target_degree_level: DegreeLevel = DegreeLevel.MASTERS
    academic_score_band: str = "unknown"  # excellent/good/average/below_average/poor
    language_score_band: str = "unknown"  # native/excellent/good/adequate/minimum
    background_field: Optional[str] = None  # e.g., "Computer Science", "Business"
    
    # Work Experience
    work_experience_years: float = 0.0
    has_research_experience: bool = False
    
    # Gap Years
    gap_years: int = 0
    graduation_year: Optional[int] = None
    
    # Preferences
    preferred_countries: List[str] = Field(default_factory=list)
    preferred_program_domains: List[str] = Field(default_factory=list)
    career_goals: List[str] = Field(default_factory=list)
    
    # Budget
    max_tuition_budget_usd: Optional[float] = None
    tuition_preference_band: str = "unknown"  # very_low/low/moderate/high/very_high
    
    # Intake Timing
    target_intake_year: Optional[int] = None
    target_intake_term: Optional[str] = None  # fall/spring/winter/summer
    
    # Additional Preferences
    preferred_class_size: Optional[str] = None  # small/medium/large
    internship_importance: str = "neutral"  # high/neutral/low
    
    class Config:
        use_enum_values = True


# =============================================================================
# OUTPUT CONTRACTS
# =============================================================================

class DimensionScore(BaseModel):
    """Individual dimension score with explanation."""
    dimension: str
    score: float = Field(ge=0.0, le=1.0)
    weight: float = Field(ge=0.0, le=1.0)
    weighted_score: float = Field(ge=0.0, le=1.0)
    explanation: str = ""


class RiskFactor(BaseModel):
    """Risk factor identified for a recommendation."""
    factor: str
    severity: str  # high/moderate/low
    description: str


class ImprovementSuggestion(BaseModel):
    """Actionable suggestion to improve match."""
    area: str
    suggestion: str
    impact: str  # high/moderate/low


class ProgramRecommendation(BaseModel):
    """
    Single program recommendation with full scoring details.
    """
    # Identifiers
    program_id: int
    intake_id: Optional[int] = None
    university_id: int
    
    # Basic Info
    university_name: str
    program_name: str
    degree_type: str
    country: str
    city: Optional[str] = None
    logo_thumbnail_url: Optional[str] = None
    
    # Scoring
    overall_score: float = Field(ge=0.0, le=1.0)
    dimension_scores: List[DimensionScore] = Field(default_factory=list)
    
    # Classification
    fit_category: str  # ambitious/target/safe/not_recommended
    confidence_level: float = Field(ge=0.0, le=1.0)
    
    # Risk & Explainability
    risk_factors: List[RiskFactor] = Field(default_factory=list)
    improvement_suggestions: List[ImprovementSuggestion] = Field(default_factory=list)
    
    # Additional Context
    tuition_fee_band: Optional[str] = None
    intake_term: Optional[str] = None
    intake_year: Optional[int] = None
    application_deadline: Optional[date] = None
    
    # Ranking metadata
    rank: int = 0
    category_rank: int = 0


class RecommendationOutput(BaseModel):
    """
    Output contract for the scoring engine.
    Contains ranked recommendations with summary statistics.
    """
    # Request tracking
    request_id: Optional[str] = None
    student_id: Optional[str] = None
    
    # All recommendations (ranked)
    all_recommendations: List[ProgramRecommendation] = Field(default_factory=list)
    
    # Summary Statistics
    total_candidates_evaluated: int = 0
    total_eligible: int = 0
    total_recommended: int = 0
    
    # Processing metadata
    processing_time_ms: Optional[float] = None
    engine_version: str = "1.0.0"
    
    # Warnings/Notes
    warnings: List[str] = Field(default_factory=list)


# =============================================================================
# INTERMEDIATE DATA STRUCTURES
# =============================================================================

class CandidateProgram(BaseModel):
    """
    Intermediate representation of a program candidate during scoring.
    Used internally by the scoring engine pipeline.
    """
    # IDs
    program_id: int
    university_id: int
    intake_id: Optional[int] = None
    
    # University data
    university_name: str = ""
    country: str = ""
    city: str = ""
    global_reputation_band: str = "unknown"
    institution_type: str = ""
    logo_thumbnail_url: Optional[str] = None
    
    # Program data
    program_name: str = ""
    degree_type: str = ""
    program_domain: str = ""
    tuition_fee_band: str = "unknown"
    program_competitiveness_band: str = "unknown"
    delivery_mode: str = ""
    typical_duration_months: int = 0
    background_preference_tags: List[str] = Field(default_factory=list)
    industry_alignment_tags: List[str] = Field(default_factory=list)
    internship_opportunities: str = ""
    
    # Intake data
    intake_term: str = ""
    intake_year: int = 0
    application_open_date: Optional[date] = None
    application_close_date: Optional[date] = None
    intake_status: str = ""
    
    # Eligibility snapshot data
    academic_score_band: str = "unknown"
    language_score_band: str = "unknown"
    background_match_level: str = "unknown"
    work_experience_preference: str = "neutral"
    gap_year_tolerance_level: str = "moderate"
    historical_acceptance_strictness: str = "moderate"
    competition_level_this_intake: str = "moderate"
    
    # Degree match metadata (for 3-state degree handling)
    degree_match_status: str = "unknown"  # "match" | "unknown" | "mismatch"
    
    class Config:
        use_enum_values = True


class ScoredCandidate(BaseModel):
    """
    A candidate with computed scores.
    Used between scoring and classification stages.
    """
    candidate: CandidateProgram
    dimension_scores: Dict[str, DimensionScore] = Field(default_factory=dict)
    overall_score: float = 0.0
    is_eligible: bool = True
    risk_factors: List[RiskFactor] = Field(default_factory=list)
