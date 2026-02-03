"""
Recommendation Logic Module

Provides the deterministic scoring engine for university/program recommendations.
"""

from .contracts import (
    StudentProfile,
    RecommendationOutput,
    ProgramRecommendation,
    DimensionScore,
    RiskFactor,
    ImprovementSuggestion,
    CandidateProgram,
    ScoredCandidate,
    DegreeLevel,
)
from .engine import RecommendationEngine, get_recommendations
from .constants import FitCategory

__all__ = [
    # Main engine
    "RecommendationEngine",
    "get_recommendations",
    
    # Contracts
    "StudentProfile",
    "RecommendationOutput",
    "ProgramRecommendation",
    "DimensionScore",
    "RiskFactor",
    "ImprovementSuggestion",
    "CandidateProgram",
    "ScoredCandidate",
    "DegreeLevel",
    
    # Enums
    "FitCategory",
]
