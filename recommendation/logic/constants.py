"""
Scoring Engine Constants

Defines all band mappings, weights, thresholds, and enums used by the scoring engine.
All values are deterministic with no AI/ML components.
"""

from enum import Enum
from typing import Dict

# =============================================================================
# BAND SCORE MAPPINGS
# =============================================================================

# Academic score bands (e.g., GPA normalized)
ACADEMIC_SCORE_BAND_MAP: Dict[str, float] = {
    "excellent": 1.0,      # 3.7+ GPA / 85%+
    "good": 0.8,           # 3.3-3.69 GPA / 75-84%
    "average": 0.6,        # 3.0-3.29 GPA / 65-74%
    "below_average": 0.4,  # 2.5-2.99 GPA / 55-64%
    "poor": 0.2,           # Below 2.5 GPA / Below 55%
    "unknown": 0.5,        # Default when not provided
}

# Language proficiency bands (IELTS/TOEFL normalized)
LANGUAGE_SCORE_BAND_MAP: Dict[str, float] = {
    "native": 1.0,         # Native speaker
    "excellent": 0.95,     # IELTS 8.0+ / TOEFL 110+
    "good": 0.8,           # IELTS 7.0-7.5 / TOEFL 95-109
    "adequate": 0.65,      # IELTS 6.0-6.5 / TOEFL 80-94
    "minimum": 0.5,        # IELTS 5.5 / TOEFL 70-79
    "below_minimum": 0.3,  # Below minimum requirements
    "unknown": 0.5,
}

# Background match levels
BACKGROUND_MATCH_LEVEL_MAP: Dict[str, float] = {
    "strong_match": 1.0,      # Highly relevant background
    "good_match": 0.8,        # Generally relevant
    "partial_match": 0.6,     # Some overlap
    "weak_match": 0.4,        # Limited relevance
    "no_match": 0.2,          # Unrelated background
    "unknown": 0.5,
}

# Work experience preference alignment
WORK_EXPERIENCE_PREFERENCE_MAP: Dict[str, float] = {
    "required": 1.0,       # Program explicitly requires work exp
    "preferred": 0.7,      # Preferred but not required
    "neutral": 0.5,        # No preference
    "not_required": 0.3,   # Fresh grads preferred
}

# Work experience years bands
WORK_EXPERIENCE_YEARS_MAP: Dict[str, float] = {
    "extensive": 1.0,      # 5+ years
    "significant": 0.8,    # 3-5 years
    "moderate": 0.6,       # 1-3 years
    "minimal": 0.4,        # <1 year
    "none": 0.2,           # No experience
    "unknown": 0.5,
}

# Gap year tolerance
GAP_YEAR_TOLERANCE_MAP: Dict[str, float] = {
    "flexible": 1.0,       # No penalty for gaps
    "moderate": 0.7,       # Small penalty
    "strict": 0.4,         # Significant penalty
    "very_strict": 0.2,    # Major red flag for gaps
}

# Competition level
COMPETITION_LEVEL_MAP: Dict[str, float] = {
    "low": 1.0,            # Less competitive = higher chance
    "moderate": 0.7,
    "high": 0.5,
    "very_high": 0.3,
    "extremely_high": 0.15,
}

# Acceptance strictness (inverted - stricter = lower score)
ACCEPTANCE_STRICTNESS_MAP: Dict[str, float] = {
    "lenient": 1.0,
    "moderate": 0.7,
    "strict": 0.5,
    "very_strict": 0.3,
}

# Global reputation bands
REPUTATION_BAND_MAP: Dict[str, float] = {
    "top_10": 1.0,
    "top_50": 0.85,
    "top_100": 0.7,
    "top_200": 0.55,
    "top_500": 0.4,
    "unranked": 0.25,
    "unknown": 0.5,
}

# Tuition fee bands (for affordability scoring)
TUITION_FEE_BAND_MAP: Dict[str, float] = {
    "very_low": 1.0,       # < $10k/year
    "low": 0.8,            # $10k-$20k/year
    "moderate": 0.6,       # $20k-$35k/year
    "high": 0.4,           # $35k-$50k/year
    "very_high": 0.2,      # > $50k/year
    "unknown": 0.5,
}

# Program competitiveness
PROGRAM_COMPETITIVENESS_MAP: Dict[str, float] = {
    "low": 1.0,
    "moderate": 0.75,
    "high": 0.5,
    "very_high": 0.3,
}

# =============================================================================
# DIMENSION WEIGHTS
# =============================================================================

# Weights for each scoring dimension (must sum to 1.0)
DIMENSION_WEIGHTS: Dict[str, float] = {
    "academic_fit": 0.25,      # GPA, test scores alignment
    "eligibility": 0.25,       # Meets requirements
    "program_fit": 0.20,       # Background, interests alignment
    "affordability": 0.15,     # Budget match
    "career_alignment": 0.10,  # Career goals match
    "location_preference": 0.05,  # Country/city preference
}

# =============================================================================
# CLASSIFICATION THRESHOLDS
# =============================================================================

class FitCategory(str, Enum):
    """Classification categories for program fit."""
    AMBITIOUS = "ambitious"      # Reach school - stretch goal
    TARGET = "target"            # Good match - realistic target
    SAFE = "safe"                # Safety school - high confidence
    NOT_RECOMMENDED = "not_recommended"  # Poor fit


# Score thresholds for classification
CLASSIFICATION_THRESHOLDS: Dict[str, tuple] = {
    FitCategory.AMBITIOUS: (0.75, 1.0),      # Top 25%
    FitCategory.TARGET: (0.50, 0.75),        # Middle range
    FitCategory.SAFE: (0.30, 0.50),          # Lower competitive
    FitCategory.NOT_RECOMMENDED: (0.0, 0.30),  # Poor fit
}

# Eligibility score thresholds
ELIGIBILITY_THRESHOLD = 0.4  # Minimum score to be considered eligible

# =============================================================================
# RANKING CONFIGURATION
# =============================================================================

# Maximum number of recommendations per category
MAX_RECOMMENDATIONS_PER_CATEGORY = 5
MAX_TOTAL_RECOMMENDATIONS = 15

# Diversity penalty - reduce score for programs from same university
SAME_UNIVERSITY_PENALTY = 0.1

# =============================================================================
# RISK FACTORS
# =============================================================================

HIGH_RISK_FACTORS = [
    "gpa_below_minimum",
    "language_below_requirement",
    "missing_prerequisites",
    "excessive_gap_years",
    "no_work_experience_required",
]

MODERATE_RISK_FACTORS = [
    "borderline_gpa",
    "borderline_language",
    "limited_work_experience",
    "different_background",
]

# =============================================================================
# DEFAULT VALUES
# =============================================================================

DEFAULT_BAND = "unknown"
DEFAULT_SCORE = 0.5
MIN_CONFIDENCE_THRESHOLD = 0.3
