"""
Score Aggregator

Combines individual dimension scores into an overall score.
Applies weighting and normalization.
"""

from typing import List, Dict
from .contracts import (
    StudentProfile, 
    CandidateProgram, 
    DimensionScore, 
    ScoredCandidate,
    RiskFactor
)
from .dimension_scorers import (
    score_academic_fit,
    score_eligibility,
    score_program_fit,
    score_affordability,
    score_career_alignment,
    score_location_preference,
)
from .constants import DIMENSION_WEIGHTS, ELIGIBILITY_THRESHOLD


def aggregate_scores(
    profile: StudentProfile,
    candidate: CandidateProgram
) -> ScoredCandidate:
    """
    Compute all dimension scores and aggregate into overall score.
    
    Args:
        profile: Student's profile
        candidate: Program candidate to score
        
    Returns:
        ScoredCandidate with all scores and eligibility status
    """
    dimension_scores: Dict[str, DimensionScore] = {}
    all_risks: List[RiskFactor] = []
    
    # Score each dimension
    scorers = [
        score_academic_fit,
        score_eligibility,
        score_program_fit,
        score_affordability,
        score_career_alignment,
        score_location_preference,
    ]
    
    for scorer in scorers:
        score, risks = scorer(profile, candidate)
        dimension_scores[score.dimension] = score
        all_risks.extend(risks)
    
    # Calculate overall score (weighted sum)
    overall_score = sum(
        score.weighted_score 
        for score in dimension_scores.values()
    )
    
    # Normalize to ensure 0-1 range
    overall_score = max(0.0, min(1.0, overall_score))
    
    # Determine eligibility based on thresholds
    is_eligible = True
    
    # Check academic fit threshold
    academic_score = dimension_scores.get("academic_fit")
    if academic_score and academic_score.score < ELIGIBILITY_THRESHOLD:
        is_eligible = False
    
    # Check eligibility dimension threshold
    eligibility_score = dimension_scores.get("eligibility")
    if eligibility_score and eligibility_score.score < ELIGIBILITY_THRESHOLD:
        is_eligible = False
    
    # Check for high-severity risks
    high_risks = [r for r in all_risks if r.severity == "high"]
    if len(high_risks) >= 2:
        is_eligible = False
    
    return ScoredCandidate(
        candidate=candidate,
        dimension_scores=dimension_scores,
        overall_score=overall_score,
        is_eligible=is_eligible,
        risk_factors=all_risks
    )


def batch_aggregate(
    profile: StudentProfile,
    candidates: List[CandidateProgram]
) -> List[ScoredCandidate]:
    """
    Score multiple candidates in batch.
    
    Args:
        profile: Student's profile
        candidates: List of program candidates
        
    Returns:
        List of ScoredCandidate objects
    """
    return [aggregate_scores(profile, c) for c in candidates]
