"""
Recommendation Engine

Main orchestrator that combines all scoring components into a single pipeline.
This is the primary entry point for generating recommendations.
"""

import time
from typing import List, Optional
from sqlalchemy.orm import Session

from .contracts import StudentProfile, RecommendationOutput, CandidateProgram
from .candidate_generator import generate_candidates, generate_mock_candidates
from .aggregator import batch_aggregate
from .classifier import classify_all
from .ranker import rank_candidates, apply_diversity_penalty, select_top_per_category, get_final_ranked_list
from .output_assembler import assemble_output
from .constants import FitCategory


class RecommendationEngine:
    """
    Main recommendation engine that orchestrates the scoring pipeline.
    
    Pipeline flow:
    1. Candidate Generation - Fetch/filter programs from DB
    2. Dimension Scoring - Score each dimension independently
    3. Aggregation - Combine dimension scores into overall score
    4. Classification - Categorize into Ambitious/Target/Safe
    5. Ranking - Rank within and across categories
    6. Output Assembly - Build final RecommendationOutput
    """
    
    def __init__(self, db: Optional[Session] = None):
        """
        Initialize the recommendation engine.
        
        Args:
            db: Optional database session. If None, uses mock data.
        """
        self.db = db
        self.version = "1.0.0"
    
    def recommend(
        self,
        profile: StudentProfile,
        max_candidates: int = 200,
        use_mock: bool = False
    ) -> RecommendationOutput:
        """
        Generate recommendations for a student profile.
        
        Args:
            profile: Student's profile and preferences
            max_candidates: Maximum candidates to evaluate
            use_mock: If True, use mock data instead of DB
            
        Returns:
            RecommendationOutput with categorized recommendations
        """
        start_time = time.perf_counter()
        
        # Step 1: Generate candidates
        if use_mock or self.db is None:
            candidates = generate_mock_candidates(profile, count=max_candidates)
        else:
            candidates = generate_candidates(self.db, profile, max_candidates)
        
        if not candidates:
            # Return empty result
            return RecommendationOutput(
                student_id=profile.student_id,
                total_candidates_evaluated=0,
                total_eligible=0,
                total_recommended=0,
                warnings=["No programs found matching your criteria."],
            )
        
        # Step 2 & 3: Score and aggregate
        scored_candidates = batch_aggregate(profile, candidates)
        
        # Filter eligible only for further processing
        eligible = [s for s in scored_candidates if s.is_eligible]
        
        # Step 4: Classify
        classified = classify_all(eligible)
        
        # Step 5: Rank
        # First rank all eligible by score
        ranked = rank_candidates(eligible)
        
        # Apply diversity penalty
        ranked = apply_diversity_penalty(ranked)
        
        # Re-classify after diversity adjustment
        classified = classify_all(ranked)
        
        # Select top per category
        by_category = select_top_per_category(classified)
        
        # Get final ranked list
        all_ranked = get_final_ranked_list(by_category)
        
        # Step 6: Assemble output
        processing_time = (time.perf_counter() - start_time) * 1000
        
        output = assemble_output(
            profile=profile,
            by_category=by_category,
            all_ranked=all_ranked,
            total_evaluated=len(candidates),
            total_eligible=len(eligible),
            processing_time_ms=round(processing_time, 2)
        )
        
        return output
    
    def recommend_from_dict(
        self,
        profile_data: dict,
        **kwargs
    ) -> RecommendationOutput:
        """
        Generate recommendations from a dictionary profile.
        
        Convenience method for API integration.
        
        Args:
            profile_data: Dictionary matching StudentProfile fields
            **kwargs: Additional arguments passed to recommend()
            
        Returns:
            RecommendationOutput
        """
        profile = StudentProfile(**profile_data)
        return self.recommend(profile, **kwargs)
    
    def score_single_program(
        self,
        profile: StudentProfile,
        candidate: CandidateProgram
    ) -> dict:
        """
        Score a single program for a student.
        
        Useful for getting detailed scoring on a specific program
        the student is interested in.
        
        Args:
            profile: Student profile
            candidate: Program to score
            
        Returns:
            Dict with scoring details
        """
        from .aggregator import aggregate_scores
        from .classifier import classify_candidate
        
        scored = aggregate_scores(profile, candidate)
        category = classify_candidate(scored)
        
        return {
            "overall_score": scored.overall_score,
            "is_eligible": scored.is_eligible,
            "category": category.value,
            "dimension_scores": {
                dim: {
                    "score": score.score,
                    "weight": score.weight,
                    "weighted_score": score.weighted_score,
                    "explanation": score.explanation
                }
                for dim, score in scored.dimension_scores.items()
            },
            "risk_factors": [
                {"factor": r.factor, "severity": r.severity, "description": r.description}
                for r in scored.risk_factors
            ]
        }


# Convenience function for simple usage
def get_recommendations(
    profile: StudentProfile,
    db: Optional[Session] = None,
    use_mock: bool = False
) -> RecommendationOutput:
    """
    Convenience function to get recommendations.
    
    Args:
        profile: Student profile
        db: Optional database session
        use_mock: Use mock data
        
    Returns:
        RecommendationOutput
    """
    engine = RecommendationEngine(db)
    return engine.recommend(profile, use_mock=use_mock)
