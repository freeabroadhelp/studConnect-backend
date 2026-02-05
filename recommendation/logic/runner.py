"""
Engine Runner

Orchestrates the recommendation pipeline:
1. Accepts StudentProfile
2. Fetches programs via adapter
3. Runs recommendation engine
4. Returns ranked recommendations

This is a pure orchestration layer - NO scoring, NO DB queries, NO business logic.
"""

from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session

from .adapter import fetch_and_transform_programs, fetch_single_program
from .contracts import StudentProfile, RecommendationOutput, CandidateProgram
from .engine import RecommendationEngine
from .constants import FitCategory


def _adapter_to_candidate(normalized: Dict[str, Any]) -> CandidateProgram:
    """
    Convert adapter output to CandidateProgram for engine input.
    
    Maps normalized dict fields to CandidateProgram fields.
    """
    # Map conversion signal to academic band
    signal_to_band = {
        "HIGH": "excellent",
        "MEDIUM": "good",
        "LOW": "average",
        "UNKNOWN": "unknown",
    }
    
    # Map seat availability to competition level
    seat_to_competition = {
        "HIGH": "low",       # High availability = low competition
        "MEDIUM": "moderate",
        "LOW": "high",       # Low availability = high competition
        "UNKNOWN": "moderate",
    }
    
    # Extract first intake dates if available
    intakes = normalized.get("intakes", [])
    first_intake = intakes[0] if intakes else {}
    
    # Determine tuition band from fee
    tuition_fee = normalized.get("tuition_fee")
    tuition_band = "unknown"
    if tuition_fee:
        if tuition_fee < 10000:
            tuition_band = "very_low"
        elif tuition_fee < 20000:
            tuition_band = "low"
        elif tuition_fee < 35000:
            tuition_band = "moderate"
        elif tuition_fee < 50000:
            tuition_band = "high"
        else:
            tuition_band = "very_high"
    
    # Determine reputation band from rank
    rank = normalized.get("rank")
    reputation_band = "unknown"
    if rank:
        if rank <= 10:
            reputation_band = "top_10"
        elif rank <= 50:
            reputation_band = "top_50"
        elif rank <= 100:
            reputation_band = "top_100"
        elif rank <= 200:
            reputation_band = "top_200"
        elif rank <= 500:
            reputation_band = "top_500"
        else:
            reputation_band = "unranked"
    
    return CandidateProgram(
        program_id=int(normalized.get("program_id") or 0),
        university_id=int(normalized.get("university_id") or 0),
        intake_id=None,
        
        # University data
        university_name=normalized.get("university_name", ""),
        country=normalized.get("country", ""),
        city=normalized.get("city", ""),
        global_reputation_band=reputation_band,
        institution_type=normalized.get("institution_type", ""),
        logo_thumbnail_url=normalized.get("logo_thumbnail_url"),
        
        # Program data
        program_name=normalized.get("program_name", ""),
        degree_type=normalized.get("degree_level", ""),
        program_domain="",  # Not directly available
        tuition_fee_band=tuition_band,
        program_competitiveness_band=seat_to_competition.get(
            normalized.get("seat_availability", "UNKNOWN"), "moderate"
        ),
        delivery_mode="",
        typical_duration_months=0,
        background_preference_tags=[],
        industry_alignment_tags=[],
        internship_opportunities="",
        
        # Intake data
        intake_term="",
        intake_year=first_intake.get("start_date").year if first_intake.get("start_date") else 0,
        application_open_date=first_intake.get("open_date"),
        application_close_date=first_intake.get("deadline"),
        intake_status="open",
        
        # Eligibility data (from signals)
        academic_score_band=signal_to_band.get(
            normalized.get("conversion_signal", "UNKNOWN"), "unknown"
        ),
        language_score_band="unknown",
        background_match_level="unknown",
        work_experience_preference="neutral",
        gap_year_tolerance_level="moderate",
        historical_acceptance_strictness="moderate",
        competition_level_this_intake=seat_to_competition.get(
            normalized.get("seat_availability", "UNKNOWN"), "moderate"
        ),
    )


def run_recommendations(
    db: Session,
    profile: StudentProfile,
    limit: int = 100
) -> RecommendationOutput:
    """
    Main entry point: run full recommendation pipeline.
    
    Args:
        db: Database session
        profile: Student profile with preferences
        limit: Max programs to evaluate
    
    Returns:
        RecommendationOutput with ranked recommendations
    """
    import logging
    logger = logging.getLogger(__name__)
    
    logger.info(f"🚀 Starting recommendation pipeline for student: {profile.student_id or 'anonymous'}")
    logger.info(f"🎯 Target degree level: {profile.target_degree_level}")
    logger.info(f"🌍 Preferred countries: {profile.preferred_countries}")
    
    # Step 1: Fetch programs via adapter with HARD FILTERS
    # Use optimized fetch limit - adapter now does SQL-level filtering
    fetch_limit = min(100, limit)  # Reduced since adapter filters at SQL level now
    
    normalized_programs = fetch_and_transform_programs(
        db=db,
        limit=fetch_limit,
        country_filter=profile.preferred_countries[0] if profile.preferred_countries else None,
        target_degree_level=profile.target_degree_level  # HARD FILTER: Degree level
    )
    
    if not normalized_programs:
        logger.warning(f"⚠️ No programs found matching criteria")
        return RecommendationOutput(
            student_id=profile.student_id,
            total_candidates_evaluated=0,
            total_eligible=0,
            total_recommended=0,
            warnings=["No programs found matching criteria."],
        )
    
    # Step 2: Convert to CandidateProgram format
    candidates = []
    for normalized in normalized_programs:
        try:
            candidate = _adapter_to_candidate(normalized)
            candidates.append(candidate)
        except Exception as e:
            # Skip programs that fail conversion
            logger.debug(f"Failed to convert program {normalized.get('program_id')}: {e}")
            continue
    
    if not candidates:
        logger.warning(f"⚠️ Failed to process any programs")
        return RecommendationOutput(
            student_id=profile.student_id,
            total_candidates_evaluated=len(normalized_programs),
            total_eligible=0,
            total_recommended=0,
            warnings=["Failed to process any programs."],
        )
    
    logger.info(f"📦 Candidates converted for scoring: {len(candidates)}")
    
    # Step 3: Run engine with candidates
    engine = RecommendationEngine(db=None)  # Engine doesn't need DB - we provide candidates
    
    # Use engine's internal pipeline with our candidates
    from .aggregator import batch_aggregate
    from .ranker import rank_candidates, apply_diversity_penalty, get_final_ranked_list
    from .output_assembler import assemble_output
    import time
    
    start_time = time.perf_counter()
    
    # Score all candidates
    logger.info(f"🎲 Scoring candidates...")
    scored_candidates = batch_aggregate(profile, candidates)
    logger.info(f"📊 Candidates scored: {len(scored_candidates)}")
    
    # Filter eligible
    eligible = [s for s in scored_candidates if s.is_eligible]
    logger.info(f"✅ Eligible candidates: {len(eligible)}")
    
    if len(eligible) < 5:
        logger.warning(f"⚠️ Low eligible count: {len(eligible)} (expected > 5)")
    
    # Rank
    logger.info(f"📈 Ranking candidates...")
    ranked = rank_candidates(eligible)
    ranked = apply_diversity_penalty(ranked)
    logger.info(f"🏆 Candidates ranked: {len(ranked)}")
    
    # Final ranked list (take top N based on original limit)
    # DO NOT apply limit here - let output assembler decide
    all_ranked = ranked[:min(limit, len(ranked))]
    logger.info(f"🎁 Final recommendations to return: {len(all_ranked)}")
    
    processing_time = (time.perf_counter() - start_time) * 1000
    
    # Assemble output
    output = assemble_output(
        profile=profile,
        all_ranked=all_ranked,
        total_evaluated=len(candidates),
        total_eligible=len(eligible),
        processing_time_ms=round(processing_time, 2)
    )
    
    logger.info(f"✨ Recommendation pipeline complete ({processing_time:.2f}ms)")
    
    return output


def run_recommendations_from_dict(
    db: Session,
    profile_data: Dict[str, Any],
    limit: int = 100
) -> RecommendationOutput:
    """
    Convenience wrapper accepting dict instead of StudentProfile.
    
    Args:
        db: Database session
        profile_data: Dict matching StudentProfile fields
        limit: Max programs to evaluate
    
    Returns:
        RecommendationOutput
    """
    profile = StudentProfile(**profile_data)
    return run_recommendations(db, profile, limit)


def get_recommendations_simple(
    db: Session,
    profile: StudentProfile,
    limit: int = 100
) -> List[Dict[str, Any]]:
    """
    Simplified output format for easier consumption.
    
    Returns list of dicts instead of full RecommendationOutput.
    """
    output = run_recommendations(db, profile, limit)
    
    results = []
    for rec in output.all_recommendations:
        results.append({
            "program_id": rec.program_id,
            "university_id": rec.university_id,
            "university_name": rec.university_name,
            "program_name": rec.program_name,
            "country": rec.country,
            "classification": "recommended", # Fixed value
            "total_score": rec.overall_score,
            "rank": rec.rank,
            "dimension_scores": {
                d.dimension: d.score for d in rec.dimension_scores
            },
            "confidence_level": rec.confidence_level,
            "risk_factors": [r.factor for r in rec.risk_factors],
        })
    
    return results


# =============================================================================
# VALIDATION
# =============================================================================

def validate_runner():
    """
    Developer sanity check - runs full pipeline with real DB data.
    """
    import sys
    sys.path.insert(0, ".")
    from db import SessionLocal
    
    # Create test profile
    profile = StudentProfile(
        student_id="test_runner_001",
        academic_score_band="good",
        language_score_band="good",
        background_field="Computer Science",
        work_experience_years=1.5,
        preferred_countries=[],  # No filter - get all
        preferred_program_domains=["Computer Science", "Engineering"],
        tuition_preference_band="moderate",
    )
    
    db = SessionLocal()
    try:
        print("=" * 60)
        print("RUNNER VALIDATION")
        print("=" * 60)
        
        output = run_recommendations(db, profile, limit=50)
        
        print(f"\nTotal Evaluated: {output.total_candidates_evaluated}")
        print(f"Total Eligible: {output.total_eligible}")
        print(f"Total Recommended: {output.total_recommended}")
        print(f"Processing Time: {output.processing_time_ms:.2f}ms")
        
        print(f"\n--- TOP 3 RECOMMENDATIONS ---")
        for rec in output.all_recommendations[:3]:
            print(f"\n{rec.rank}. {rec.university_name}")
            print(f"   Program: {rec.program_name}")
            print(f"   Category: {rec.fit_category}")
            print(f"   Score: {rec.overall_score:.3f}")
            print(f"   Country: {rec.country}")
        
        if output.warnings:
            print(f"\n--- WARNINGS ---")
            for w in output.warnings:
                print(f"  ⚠️  {w}")
        
        print("\n" + "=" * 60)
        print("VALIDATION COMPLETE ✓")
        print("=" * 60)
        
        return output
        
    finally:
        db.close()


if __name__ == "__main__":
    validate_runner()
