"""
Ranker

Ranks candidates within and across categories.
Applies diversity rules to ensure varied recommendations.
"""

from typing import List, Tuple, Dict
from .contracts import ScoredCandidate
from .constants import (
    FitCategory,
    MAX_RECOMMENDATIONS_PER_CATEGORY,
    MAX_TOTAL_RECOMMENDATIONS,
    SAME_UNIVERSITY_PENALTY,
)


def rank_candidates(
    scored_candidates: List[ScoredCandidate]
) -> List[ScoredCandidate]:
    """
    Rank candidates by overall score (descending).
    
    Args:
        scored_candidates: List of scored candidates
        
    Returns:
        Sorted list by score
    """
    return sorted(
        scored_candidates,
        key=lambda x: x.overall_score,
        reverse=True
    )


def apply_diversity_penalty(
    ranked: List[ScoredCandidate]
) -> List[ScoredCandidate]:
    """
    Apply penalty to reduce score for multiple programs from same university.
    This encourages diversity in recommendations.
    
    Args:
        ranked: Ranked list of candidates
        
    Returns:
        Adjusted and re-ranked list
    """
    seen_universities: Dict[int, int] = {}  # university_id -> count
    adjusted = []
    
    for scored in ranked:
        uni_id = scored.candidate.university_id
        count = seen_universities.get(uni_id, 0)
        
        # Apply progressive penalty for repeat universities
        penalty = count * SAME_UNIVERSITY_PENALTY
        adjusted_score = max(0.1, scored.overall_score - penalty)
        
        # Create new scored candidate with adjusted score
        adjusted_scored = ScoredCandidate(
            candidate=scored.candidate,
            dimension_scores=scored.dimension_scores,
            overall_score=adjusted_score,
            is_eligible=scored.is_eligible,
            risk_factors=scored.risk_factors
        )
        adjusted.append(adjusted_scored)
        
        seen_universities[uni_id] = count + 1
    
    # Re-sort after adjustment
    return sorted(adjusted, key=lambda x: x.overall_score, reverse=True)


def select_top_per_category(
    classified: List[Tuple[ScoredCandidate, FitCategory]],
    max_per_category: int = MAX_RECOMMENDATIONS_PER_CATEGORY
) -> Dict[FitCategory, List[ScoredCandidate]]:
    """
    Select top N candidates per category.
    
    Args:
        classified: Classified candidates
        max_per_category: Maximum per category
        
    Returns:
        Dict mapping category to list of top candidates
    """
    by_category: Dict[FitCategory, List[ScoredCandidate]] = {
        FitCategory.AMBITIOUS: [],
        FitCategory.TARGET: [],
        FitCategory.SAFE: [],
    }
    
    for scored, category in classified:
        if category == FitCategory.NOT_RECOMMENDED:
            continue
        if len(by_category[category]) < max_per_category:
            by_category[category].append(scored)
    
    # Sort each category by score
    for category in by_category:
        by_category[category] = sorted(
            by_category[category],
            key=lambda x: x.overall_score,
            reverse=True
        )
    
    return by_category


def get_final_ranked_list(
    by_category: Dict[FitCategory, List[ScoredCandidate]],
    max_total: int = MAX_TOTAL_RECOMMENDATIONS
) -> List[ScoredCandidate]:
    """
    Create final ranked list from all categories.
    Interleaves categories to ensure diversity.
    
    Args:
        by_category: Candidates grouped by category
        max_total: Maximum total recommendations
        
    Returns:
        Final ranked list
    """
    final_list: List[ScoredCandidate] = []
    
    # Collect all with original scores
    all_candidates = []
    for category in [FitCategory.AMBITIOUS, FitCategory.TARGET, FitCategory.SAFE]:
        all_candidates.extend(by_category.get(category, []))
    
    # Sort by score and take top N
    all_candidates.sort(key=lambda x: x.overall_score, reverse=True)
    
    return all_candidates[:max_total]
