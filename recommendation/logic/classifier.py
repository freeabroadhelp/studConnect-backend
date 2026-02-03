"""
Classifier

Classifies scored candidates into fit categories:
- Ambitious (reach schools)
- Target (realistic match)
- Safe (high confidence)
- Not Recommended (poor fit)
"""

from typing import List, Tuple
from .contracts import ScoredCandidate
from .constants import FitCategory, CLASSIFICATION_THRESHOLDS


def classify_candidate(scored: ScoredCandidate) -> FitCategory:
    """
    Classify a single scored candidate into a fit category.
    
    Args:
        scored: Candidate with computed scores
        
    Returns:
        FitCategory enum value
    """
    # Not eligible candidates are not recommended
    if not scored.is_eligible:
        return FitCategory.NOT_RECOMMENDED
    
    score = scored.overall_score
    
    # Check thresholds from highest to lowest
    for category in [FitCategory.AMBITIOUS, FitCategory.TARGET, FitCategory.SAFE]:
        low, high = CLASSIFICATION_THRESHOLDS[category]
        if low <= score < high or (category == FitCategory.AMBITIOUS and score >= high):
            return category
    
    return FitCategory.NOT_RECOMMENDED


def classify_all(
    scored_candidates: List[ScoredCandidate]
) -> List[Tuple[ScoredCandidate, FitCategory]]:
    """
    Classify all scored candidates.
    
    Args:
        scored_candidates: List of scored candidates
        
    Returns:
        List of tuples (ScoredCandidate, FitCategory)
    """
    return [(scored, classify_candidate(scored)) for scored in scored_candidates]


def filter_by_category(
    classified: List[Tuple[ScoredCandidate, FitCategory]],
    category: FitCategory
) -> List[ScoredCandidate]:
    """
    Filter candidates by a specific category.
    
    Args:
        classified: List of classified candidates
        category: Target category
        
    Returns:
        List of ScoredCandidate in the specified category
    """
    return [scored for scored, cat in classified if cat == category]


def get_category_counts(
    classified: List[Tuple[ScoredCandidate, FitCategory]]
) -> dict:
    """
    Count candidates in each category.
    """
    counts = {cat: 0 for cat in FitCategory}
    for _, category in classified:
        counts[category] += 1
    return counts
