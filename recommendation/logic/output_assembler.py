"""
Output Assembler

Transforms internal scoring data into the final RecommendationOutput contract.
Generates improvement suggestions based on risk factors.
"""

from typing import List, Dict, Optional
import uuid
from datetime import date

from .contracts import (
    StudentProfile,
    ScoredCandidate,
    DimensionScore,
    RiskFactor,
    ImprovementSuggestion,
    ProgramRecommendation,
    RecommendationOutput,
)
from .constants import FitCategory


def assemble_recommendation(
    scored: ScoredCandidate,
    global_rank: int
) -> ProgramRecommendation:
    """
    Convert a ScoredCandidate into a ProgramRecommendation.
    
    Args:
        scored: The scored candidate
        global_rank: Overall ranking position
        
    Returns:
        ProgramRecommendation object
    """
    candidate = scored.candidate
    
    # Convert dimension scores dict to list
    dimension_scores_list = list(scored.dimension_scores.values())
    
    # Generate improvement suggestions from risk factors
    suggestions = _generate_suggestions(scored.risk_factors)
    
    # Calculate confidence level
    confidence = _calculate_confidence(scored)
    
    return ProgramRecommendation(
        # Identifiers
        program_id=candidate.program_id,
        intake_id=candidate.intake_id,
        university_id=candidate.university_id,
        
        # Basic Info
        university_name=candidate.university_name,
        program_name=candidate.program_name,
        degree_type=candidate.degree_type,
        country=candidate.country,
        city=candidate.city,
        
        # Scoring
        overall_score=round(scored.overall_score, 3),
        dimension_scores=dimension_scores_list,
        
        # Classification (REMOVED)
        fit_category="recommended", 
        confidence_level=confidence,
        
        # Risk & Explainability
        risk_factors=scored.risk_factors,
        improvement_suggestions=suggestions,
        
        # Additional Context
        tuition_fee_band=candidate.tuition_fee_band,
        intake_term=candidate.intake_term,
        intake_year=candidate.intake_year if candidate.intake_year else None,
        application_deadline=candidate.application_close_date,
        
        # Ranking
        rank=global_rank,
        category_rank=0, # Deprecated
    )


def assemble_output(
    profile: StudentProfile,
    all_ranked: List[ScoredCandidate],
    total_evaluated: int,
    total_eligible: int,
    processing_time_ms: Optional[float] = None
) -> RecommendationOutput:
    """
    Assemble the final RecommendationOutput.
    
    Args:
        profile: Original student profile
        all_ranked: All ranked candidates
        total_evaluated: Total candidates evaluated
        total_eligible: Total eligible candidates
        processing_time_ms: Processing time in milliseconds
        
    Returns:
        Complete RecommendationOutput
    """
    import logging
    logger = logging.getLogger(__name__)
    
    # Build all recommendations list
    all_recommendations = _build_all_list(all_ranked)
    
    # Generate warnings
    warnings = _generate_warnings(profile, total_evaluated)
    
    # SAFETY GUARD: Warn if recommendation count is unrealistically low
    if len(all_recommendations) < 5:
        warning_msg = f"Low recommendation count: {len(all_recommendations)} programs returned. Consider broadening search criteria."
        logger.warning(f"⚠️ {warning_msg}")
        warnings.append(warning_msg)
    
    return RecommendationOutput(
        request_id=str(uuid.uuid4()),
        student_id=profile.student_id,
        
        all_recommendations=all_recommendations,
        
        total_candidates_evaluated=total_evaluated,
        total_eligible=total_eligible,
        total_recommended=len(all_recommendations),
        
        processing_time_ms=processing_time_ms,
        engine_version="1.0.0",
        
        warnings=warnings,
    )


def _build_all_list(
    all_ranked: List[ScoredCandidate]
) -> List[ProgramRecommendation]:
    """Build complete ranked list of all recommendations."""
    recommendations = []
    
    for global_rank, scored in enumerate(all_ranked, 1):
        rec = assemble_recommendation(scored, global_rank)
        recommendations.append(rec)
    
    return recommendations


def _generate_suggestions(
    risk_factors: List[RiskFactor]
) -> List[ImprovementSuggestion]:
    """Generate improvement suggestions based on risk factors."""
    suggestions = []
    
    suggestion_map = {
        "gpa_below_minimum": ImprovementSuggestion(
            area="Academic Performance",
            suggestion="Consider additional coursework or certifications to strengthen academic profile",
            impact="high"
        ),
        "language_below_requirement": ImprovementSuggestion(
            area="Language Proficiency",
            suggestion="Retake language test (IELTS/TOEFL) to achieve required score",
            impact="high"
        ),
        "borderline_gpa": ImprovementSuggestion(
            area="Academic Performance",
            suggestion="Highlight strong performance in relevant coursework; consider GRE to supplement",
            impact="moderate"
        ),
        "borderline_language": ImprovementSuggestion(
            area="Language Proficiency",
            suggestion="Practice speaking and writing; consider Duolingo as backup option",
            impact="moderate"
        ),
        "limited_work_experience": ImprovementSuggestion(
            area="Work Experience",
            suggestion="Gain relevant internship or project experience before applying",
            impact="moderate"
        ),
        "no_work_experience_required": ImprovementSuggestion(
            area="Work Experience",
            suggestion="Consider programs that don't require work experience, or defer application",
            impact="high"
        ),
        "different_background": ImprovementSuggestion(
            area="Background Alignment",
            suggestion="Take prerequisite courses or MOOCs in the target field",
            impact="moderate"
        ),
        "excessive_gap_years": ImprovementSuggestion(
            area="Gap Years",
            suggestion="Prepare strong explanation; highlight productive activities during gap",
            impact="moderate"
        ),
    }
    
    for risk in risk_factors:
        if risk.factor in suggestion_map:
            suggestions.append(suggestion_map[risk.factor])
    
    return suggestions


def _calculate_confidence(scored: ScoredCandidate) -> float:
    """Calculate confidence level for this recommendation."""
    base_confidence = 0.7
    
    # Adjust based on data completeness
    unknown_count = sum(
        1 for score in scored.dimension_scores.values()
        if "unknown" in score.explanation.lower()
    )
    data_penalty = unknown_count * 0.1
    
    # Adjust based on risk factors
    high_risks = sum(1 for r in scored.risk_factors if r.severity == "high")
    risk_penalty = high_risks * 0.15
    
    confidence = base_confidence - data_penalty - risk_penalty
    return max(0.3, min(1.0, confidence))


def _generate_warnings(
    profile: StudentProfile,
    total_evaluated: int
) -> List[str]:
    """Generate any warnings for the output."""
    warnings = []
    
    if total_evaluated == 0:
        warnings.append("No candidates found matching your criteria. Consider broadening preferences.")
    
    if profile.academic_score_band == "unknown":
        warnings.append("Academic score not provided. Scores may be less accurate.")
    
    if profile.language_score_band == "unknown":
        warnings.append("Language score not provided. Please add for better recommendations.")
    
    return warnings
