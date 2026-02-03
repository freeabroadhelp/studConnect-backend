"""
Dimension Scorers

Individual scoring functions for each evaluation dimension.
Each scorer produces a normalized score between 0.0 and 1.0.
All logic is deterministic - no AI/ML components.
"""

from typing import List, Tuple
from .contracts import StudentProfile, CandidateProgram, DimensionScore, RiskFactor
from .constants import (
    ACADEMIC_SCORE_BAND_MAP,
    LANGUAGE_SCORE_BAND_MAP,
    BACKGROUND_MATCH_LEVEL_MAP,
    WORK_EXPERIENCE_PREFERENCE_MAP,
    WORK_EXPERIENCE_YEARS_MAP,
    GAP_YEAR_TOLERANCE_MAP,
    COMPETITION_LEVEL_MAP,
    ACCEPTANCE_STRICTNESS_MAP,
    REPUTATION_BAND_MAP,
    TUITION_FEE_BAND_MAP,
    PROGRAM_COMPETITIVENESS_MAP,
    DIMENSION_WEIGHTS,
    DEFAULT_SCORE,
)


def score_academic_fit(
    profile: StudentProfile,
    candidate: CandidateProgram
) -> Tuple[DimensionScore, List[RiskFactor]]:
    """
    Score academic alignment between student and program requirements.
    
    Compares:
    - Student's academic score band vs program requirements
    - Language proficiency alignment
    """
    risks: List[RiskFactor] = []
    
    # Get student's band scores
    student_academic = ACADEMIC_SCORE_BAND_MAP.get(
        profile.academic_score_band.lower(), DEFAULT_SCORE
    )
    student_language = LANGUAGE_SCORE_BAND_MAP.get(
        profile.language_score_band.lower(), DEFAULT_SCORE
    )
    
    # Get program requirement bands
    program_academic_req = ACADEMIC_SCORE_BAND_MAP.get(
        candidate.academic_score_band.lower(), DEFAULT_SCORE
    )
    program_language_req = LANGUAGE_SCORE_BAND_MAP.get(
        candidate.language_score_band.lower(), DEFAULT_SCORE
    )
    
    # Calculate match scores (how well student meets requirements)
    # If student exceeds requirements, cap at 1.0
    academic_match = min(1.0, student_academic / max(program_academic_req, 0.1))
    language_match = min(1.0, student_language / max(program_language_req, 0.1))
    
    # Weighted combination (academic 60%, language 40%)
    raw_score = (academic_match * 0.6) + (language_match * 0.4)
    
    # Apply degree match confidence penalty (3-state degree handling)
    degree_penalty = 1.0
    if hasattr(candidate, 'degree_match_status'):
        if candidate.degree_match_status == "unknown":
            degree_penalty = 0.7  # Penalize unknown degree data
            risks.append(RiskFactor(
                factor="uncertain_degree_match",
                severity="low",
                description="Program degree information is unclear - included with penalty"
            ))
        # "match" and "mismatch" remain at 1.0 (mismatch already filtered in adapter)
    
    # Apply penalty
    raw_score = raw_score * degree_penalty
    
    # Identify risks
    if student_academic < program_academic_req - 0.2:
        risks.append(RiskFactor(
            factor="gpa_below_minimum",
            severity="high",
            description=f"Academic score ({profile.academic_score_band}) below program requirement ({candidate.academic_score_band})"
        ))
    elif student_academic < program_academic_req:
        risks.append(RiskFactor(
            factor="borderline_gpa",
            severity="moderate",
            description="Academic score is borderline for this program"
        ))
    
    if student_language < program_language_req - 0.2:
        risks.append(RiskFactor(
            factor="language_below_requirement",
            severity="high",
            description=f"Language score ({profile.language_score_band}) below requirement ({candidate.language_score_band})"
        ))
    elif student_language < program_language_req:
        risks.append(RiskFactor(
            factor="borderline_language",
            severity="moderate",
            description="Language score is borderline for this program"
        ))
    
    weight = DIMENSION_WEIGHTS["academic_fit"]
    
    return DimensionScore(
        dimension="academic_fit",
        score=raw_score,
        weight=weight,
        weighted_score=raw_score * weight,
        explanation=f"Academic match: {academic_match:.2f}, Language match: {language_match:.2f}"
    ), risks


def score_eligibility(
    profile: StudentProfile,
    candidate: CandidateProgram
) -> Tuple[DimensionScore, List[RiskFactor]]:
    """
    Score overall eligibility considering all requirements.
    
    Considers:
    - Background match
    - Work experience alignment
    - Gap year tolerance
    - Competition level
    """
    risks: List[RiskFactor] = []
    
    # Background match
    background_score = BACKGROUND_MATCH_LEVEL_MAP.get(
        candidate.background_match_level.lower(), DEFAULT_SCORE
    )
    
    # Work experience
    work_exp_pref = WORK_EXPERIENCE_PREFERENCE_MAP.get(
        candidate.work_experience_preference.lower(), DEFAULT_SCORE
    )
    
    # Convert years to band
    years = profile.work_experience_years
    if years >= 5:
        years_band = "extensive"
    elif years >= 3:
        years_band = "significant"
    elif years >= 1:
        years_band = "moderate"
    elif years > 0:
        years_band = "minimal"
    else:
        years_band = "none"
    
    student_work_exp = WORK_EXPERIENCE_YEARS_MAP.get(years_band, DEFAULT_SCORE)
    
    # Work experience alignment score
    if candidate.work_experience_preference.lower() == "required":
        work_exp_match = student_work_exp
        if student_work_exp < 0.4:
            risks.append(RiskFactor(
                factor="no_work_experience_required",
                severity="high",
                description="Program requires work experience but student has minimal/none"
            ))
    elif candidate.work_experience_preference.lower() == "preferred":
        work_exp_match = 0.5 + (student_work_exp * 0.5)  # Boost but not required
        if student_work_exp < 0.4:
            risks.append(RiskFactor(
                factor="limited_work_experience",
                severity="moderate",
                description="Program prefers work experience"
            ))
    else:
        work_exp_match = 0.8  # Not a factor
    
    # Gap year tolerance
    gap_tolerance = GAP_YEAR_TOLERANCE_MAP.get(
        candidate.gap_year_tolerance_level.lower(), 0.7
    )
    gap_penalty = 0.0
    if profile.gap_years > 0:
        gap_penalty = profile.gap_years * (1.0 - gap_tolerance) * 0.1
        gap_penalty = min(gap_penalty, 0.3)  # Cap penalty
        
        if profile.gap_years >= 3 and gap_tolerance < 0.5:
            risks.append(RiskFactor(
                factor="excessive_gap_years",
                severity="high",
                description=f"{profile.gap_years} gap years with strict tolerance"
            ))
    
    gap_score = max(0.2, 1.0 - gap_penalty)
    
    # Competition level (higher competition = lower score)
    competition_score = COMPETITION_LEVEL_MAP.get(
        candidate.competition_level_this_intake.lower(), 0.5
    )
    
    # Weighted combination
    raw_score = (
        background_score * 0.35 +
        work_exp_match * 0.25 +
        gap_score * 0.15 +
        competition_score * 0.25
    )
    
    weight = DIMENSION_WEIGHTS["eligibility"]
    
    return DimensionScore(
        dimension="eligibility",
        score=raw_score,
        weight=weight,
        weighted_score=raw_score * weight,
        explanation=f"Background: {background_score:.2f}, Work exp: {work_exp_match:.2f}, Gap: {gap_score:.2f}, Competition: {competition_score:.2f}"
    ), risks


def score_program_fit(
    profile: StudentProfile,
    candidate: CandidateProgram
) -> Tuple[DimensionScore, List[RiskFactor]]:
    """
    Score how well the program matches student's goals and interests.
    
    Considers:
    - Background alignment
    - Career goals match with industry tags
    - Program domain preference match
    """
    risks: List[RiskFactor] = []
    
    # Domain match
    domain_match = 0.5  # Default
    if profile.preferred_program_domains:
        for domain in profile.preferred_program_domains:
            if domain.lower() in candidate.program_domain.lower():
                domain_match = 1.0
                break
            elif _fuzzy_match(domain, candidate.program_domain):
                domain_match = max(domain_match, 0.7)
    
    # Career alignment
    career_match = 0.5
    if profile.career_goals and candidate.industry_alignment_tags:
        matches = 0
        for goal in profile.career_goals:
            for tag in candidate.industry_alignment_tags:
                if _fuzzy_match(goal, tag):
                    matches += 1
                    break
        if matches > 0:
            career_match = min(1.0, 0.5 + (matches * 0.25))
    
    # Background preference alignment
    background_fit = 0.5
    if profile.background_field and candidate.background_preference_tags:
        for tag in candidate.background_preference_tags:
            if _fuzzy_match(profile.background_field, tag):
                background_fit = 1.0
                break
            elif _partial_match(profile.background_field, tag):
                background_fit = max(background_fit, 0.7)
    
    if background_fit < 0.5:
        risks.append(RiskFactor(
            factor="different_background",
            severity="moderate",
            description=f"Student background ({profile.background_field}) may not align with program preferences"
        ))
    
    # Internship preference
    internship_match = 0.7  # Default neutral
    if profile.internship_importance == "high":
        if "strong" in candidate.internship_opportunities.lower():
            internship_match = 1.0
        elif "available" in candidate.internship_opportunities.lower():
            internship_match = 0.8
        else:
            internship_match = 0.5
    
    # Weighted combination
    raw_score = (
        domain_match * 0.35 +
        career_match * 0.25 +
        background_fit * 0.25 +
        internship_match * 0.15
    )
    
    weight = DIMENSION_WEIGHTS["program_fit"]
    
    return DimensionScore(
        dimension="program_fit",
        score=raw_score,
        weight=weight,
        weighted_score=raw_score * weight,
        explanation=f"Domain: {domain_match:.2f}, Career: {career_match:.2f}, Background: {background_fit:.2f}"
    ), risks


def score_affordability(
    profile: StudentProfile,
    candidate: CandidateProgram
) -> Tuple[DimensionScore, List[RiskFactor]]:
    """
    Score program affordability based on tuition and budget.
    """
    risks: List[RiskFactor] = []
    
    program_tuition = TUITION_FEE_BAND_MAP.get(
        candidate.tuition_fee_band.lower(), DEFAULT_SCORE
    )
    
    # If student specified budget preference
    if profile.tuition_preference_band and profile.tuition_preference_band != "unknown":
        student_budget = TUITION_FEE_BAND_MAP.get(
            profile.tuition_preference_band.lower(), DEFAULT_SCORE
        )
        # Score based on whether program is within budget
        # Higher program_tuition score = cheaper = better match
        if program_tuition >= student_budget:
            raw_score = 1.0  # Within or below budget
        else:
            # Calculate penalty for exceeding budget
            raw_score = max(0.2, program_tuition / student_budget)
    else:
        # No budget preference - neutral score
        raw_score = 0.7
    
    weight = DIMENSION_WEIGHTS["affordability"]
    
    return DimensionScore(
        dimension="affordability",
        score=raw_score,
        weight=weight,
        weighted_score=raw_score * weight,
        explanation=f"Program tuition: {candidate.tuition_fee_band}, Budget fit: {raw_score:.2f}"
    ), risks


def score_career_alignment(
    profile: StudentProfile,
    candidate: CandidateProgram
) -> Tuple[DimensionScore, List[RiskFactor]]:
    """
    Score career outcomes alignment.
    """
    risks: List[RiskFactor] = []
    
    # University reputation contributes to career outcomes
    reputation_score = REPUTATION_BAND_MAP.get(
        candidate.global_reputation_band.lower(), DEFAULT_SCORE
    )
    
    # Industry alignment from program fit (reuse logic)
    industry_match = 0.5
    if profile.career_goals and candidate.industry_alignment_tags:
        matches = sum(
            1 for goal in profile.career_goals
            for tag in candidate.industry_alignment_tags
            if _fuzzy_match(goal, tag)
        )
        industry_match = min(1.0, 0.5 + (matches * 0.2))
    
    # Combined score
    raw_score = (reputation_score * 0.4) + (industry_match * 0.6)
    
    weight = DIMENSION_WEIGHTS["career_alignment"]
    
    return DimensionScore(
        dimension="career_alignment",
        score=raw_score,
        weight=weight,
        weighted_score=raw_score * weight,
        explanation=f"Reputation: {reputation_score:.2f}, Industry match: {industry_match:.2f}"
    ), risks


def score_location_preference(
    profile: StudentProfile,
    candidate: CandidateProgram
) -> Tuple[DimensionScore, List[RiskFactor]]:
    """
    Score location preference alignment.
    """
    risks: List[RiskFactor] = []
    
    if not profile.preferred_countries:
        raw_score = 0.7  # No preference = neutral
    elif candidate.country in profile.preferred_countries:
        raw_score = 1.0  # Exact match
    else:
        # Check region match (e.g., USA and Canada both North America)
        raw_score = 0.4  # Not in preferred list
    
    weight = DIMENSION_WEIGHTS["location_preference"]
    
    return DimensionScore(
        dimension="location_preference",
        score=raw_score,
        weight=weight,
        weighted_score=raw_score * weight,
        explanation=f"Country: {candidate.country}, Match: {raw_score:.2f}"
    ), risks


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def _fuzzy_match(term1: str, term2: str) -> bool:
    """Simple fuzzy matching - checks if terms overlap significantly."""
    t1 = term1.lower().strip()
    t2 = term2.lower().strip()
    return t1 in t2 or t2 in t1


def _partial_match(term1: str, term2: str) -> bool:
    """Check for partial word overlap."""
    words1 = set(term1.lower().split())
    words2 = set(term2.lower().split())
    return bool(words1 & words2)
