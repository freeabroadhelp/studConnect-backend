"""
Test the scoring engine with mock data.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from recommendation.logic import (
    RecommendationEngine,
    StudentProfile,
    DegreeLevel,
)


def test_scoring_engine():
    """Test the scoring engine with a sample profile."""
    
    # Create a sample student profile
    profile = StudentProfile(
        student_id="test_student_001",
        current_degree_level=DegreeLevel.BACHELORS,
        target_degree_level=DegreeLevel.MASTERS,
        academic_score_band="good",  # 3.3-3.69 GPA
        language_score_band="good",  # IELTS 7.0-7.5
        background_field="Computer Science",
        work_experience_years=2.0,
        has_research_experience=False,
        gap_years=0,
        preferred_countries=["USA", "Canada"],
        preferred_program_domains=["Computer Science", "Data Science", "AI"],
        career_goals=["Software Engineering", "Machine Learning"],
        tuition_preference_band="moderate",
        target_intake_year=2026,
        target_intake_term="fall",
        internship_importance="high",
    )
    
    print("=" * 60)
    print("SCORING ENGINE TEST")
    print("=" * 60)
    print(f"\nStudent Profile:")
    print(f"  Academic: {profile.academic_score_band}")
    print(f"  Language: {profile.language_score_band}")
    print(f"  Background: {profile.background_field}")
    print(f"  Work Experience: {profile.work_experience_years} years")
    print(f"  Target: {profile.target_degree_level.value}")
    print(f"  Preferred Countries: {profile.preferred_countries}")
    
    # Create engine and get recommendations (using mock data)
    engine = RecommendationEngine()
    output = engine.recommend(profile, use_mock=True)
    
    print(f"\n" + "=" * 60)
    print("RESULTS")
    print("=" * 60)
    print(f"\nTotal Candidates Evaluated: {output.total_candidates_evaluated}")
    print(f"Total Eligible: {output.total_eligible}")
    print(f"Total Recommended: {output.total_recommended}")
    print(f"Processing Time: {output.processing_time_ms:.2f}ms")
    
    print(f"\n--- AMBITIOUS (Reach Schools) ---")
    for rec in output.ambitious:
        print(f"  #{rec.category_rank}: {rec.university_name} - {rec.program_name}")
        print(f"      Score: {rec.overall_score:.3f} | {rec.country}")
    
    print(f"\n--- TARGET (Good Match) ---")
    for rec in output.target:
        print(f"  #{rec.category_rank}: {rec.university_name} - {rec.program_name}")
        print(f"      Score: {rec.overall_score:.3f} | {rec.country}")
    
    print(f"\n--- SAFE (High Confidence) ---")
    for rec in output.safe:
        print(f"  #{rec.category_rank}: {rec.university_name} - {rec.program_name}")
        print(f"      Score: {rec.overall_score:.3f} | {rec.country}")
    
    if output.warnings:
        print(f"\n--- WARNINGS ---")
        for warning in output.warnings:
            print(f"  ⚠️  {warning}")
    
    # Test single program scoring
    print(f"\n" + "=" * 60)
    print("SINGLE PROGRAM SCORING TEST")
    print("=" * 60)
    
    if output.all_recommendations:
        first_rec = output.all_recommendations[0]
        print(f"\nDetailed scoring for: {first_rec.university_name}")
        print(f"Overall Score: {first_rec.overall_score:.3f}")
        print(f"Category: {first_rec.fit_category}")
        print(f"Confidence: {first_rec.confidence_level:.2f}")
        
        print("\nDimension Scores:")
        for dim in first_rec.dimension_scores:
            print(f"  {dim.dimension}: {dim.score:.3f} (weight: {dim.weight}, weighted: {dim.weighted_score:.3f})")
        
        if first_rec.risk_factors:
            print("\nRisk Factors:")
            for risk in first_rec.risk_factors:
                print(f"  [{risk.severity.upper()}] {risk.factor}: {risk.description}")
        
        if first_rec.improvement_suggestions:
            print("\nImprovement Suggestions:")
            for sug in first_rec.improvement_suggestions:
                print(f"  [{sug.impact.upper()}] {sug.area}: {sug.suggestion}")
    
    print("\n" + "=" * 60)
    print("TEST COMPLETE ✓")
    print("=" * 60)


if __name__ == "__main__":
    test_scoring_engine()
