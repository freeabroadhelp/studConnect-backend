"""
Test Script for Recommendation Engine Fixes

Tests:
1. Degree level enforcement (Masters → only Masters programs)
2. Large candidate pool (ensures realistic recommendation count)

Run from backend directory:
    python -m recommendation.tests.test_degree_filter
"""

import sys
sys.path.insert(0, ".")

from db import SessionLocal
from recommendation.logic.contracts import StudentProfile
from recommendation.logic.runner import run_recommendations
import logging

# Configure logging to see debug output
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s - %(message)s'
)

def test_masters_ireland():
    """
    Test Case 1: Degree Level Enforcement
    
    Input: Masters degree, Ireland
    Expected:
    - NO bachelor programs
    - NO diploma programs
    - ONLY masters programs
    - Multiple results (5-20)
    """
    print("\n" + "=" * 80)
    print("TEST CASE 1: MASTERS IN IRELAND")
    print("=" * 80)
    
    profile = StudentProfile(
        student_id="test_masters_ireland",
        target_degree_level="masters",
        preferred_countries=["Ireland"],
        academic_score_band="good",
        language_score_band="good",
    )
    
    db = SessionLocal()
    try:
        output = run_recommendations(db, profile, limit=100)
        
        print(f"\n📊 RESULTS:")
        print(f"  Total Evaluated: {output.total_candidates_evaluated}")
        print(f"  Total Eligible: {output.total_eligible}")
        print(f"  Total Recommended: {output.total_recommended}")
        print(f"  Processing Time: {output.processing_time_ms:.2f}ms")
        
        # Verify degree level enforcement
        print(f"\n🎓 DEGREE LEVEL VERIFICATION:")
        degree_counts = {}
        for rec in output.all_recommendations:
            degree = rec.degree_type.lower()
            degree_counts[degree] = degree_counts.get(degree, 0) + 1
        
        for degree, count in degree_counts.items():
            print(f"  {degree}: {count} programs")
        
        # Check for violations
        violations = []
        for rec in output.all_recommendations:
            degree_lower = rec.degree_type.lower()
            if not any(pattern in degree_lower for pattern in ["master", "msc", "ma", "mba", "meng", "ms"]):
                violations.append((rec.program_name, rec.degree_type))
        
        if violations:
            print(f"\n❌ DEGREE VIOLATIONS FOUND: {len(violations)}")
            for prog, deg in violations[:5]:  # Show first 5
                print(f"  - {prog} ({deg})")
        else:
            print(f"\n✅ NO DEGREE VIOLATIONS - All programs are Masters level")
        
        # Check recommendation count
        if output.total_recommended < 5:
            print(f"\n⚠️ WARNING: Only {output.total_recommended} recommendations (expected >= 5)")
        else:
            print(f"\n✅ REALISTIC COUNT: {output.total_recommended} recommendations")
        
        # Show top 5 recommendations
        print(f"\n🏆 TOP 5 RECOMMENDATIONS:")
        for rec in output.all_recommendations[:5]:
            print(f"  {rec.rank}. {rec.university_name}")
            print(f"     Program: {rec.program_name} ({rec.degree_type})")
            print(f"     Score: {rec.overall_score:.3f}")
        
        # Show warnings
        if output.warnings:
            print(f"\n⚠️ WARNINGS:")
            for warning in output.warnings:
                print(f"  - {warning}")
        
        return output
        
    finally:
        db.close()


def test_masters_broad():
    """
    Test Case 2: Large Candidate Pool
    
    Input: Masters degree, no country filter
    Expected:
    - Logs show hundreds of programs fetched
    - 10-20 ranked programs returned
    """
    print("\n" + "=" * 80)
    print("TEST CASE 2: MASTERS BROAD SEARCH")
    print("=" * 80)
    
    profile = StudentProfile(
        student_id="test_masters_broad",
        target_degree_level="masters",
        academic_score_band="good",
        language_score_band="good",
    )
    
    db = SessionLocal()
    try:
        output = run_recommendations(db, profile, limit=100)
        
        print(f"\n📊 RESULTS:")
        print(f"  Total Evaluated: {output.total_candidates_evaluated}")
        print(f"  Total Eligible: {output.total_eligible}")
        print(f"  Total Recommended: {output.total_recommended}")
        print(f"  Processing Time: {output.processing_time_ms:.2f}ms")
        
        # Verify large pool was evaluated
        if output.total_candidates_evaluated < 50:
            print(f"\n⚠️ WARNING: Only {output.total_candidates_evaluated} candidates evaluated (expected >= 100)")
        else:
            print(f"\n✅ LARGE POOL: {output.total_candidates_evaluated} candidates evaluated")
        
        # Verify realistic output count
        if output.total_recommended < 10:
            print(f"\n⚠️ WARNING: Only {output.total_recommended} recommendations (expected >= 10)")
        else:
            print(f"\n✅ REALISTIC OUTPUT: {output.total_recommended} recommendations")
        
        # Show country distribution
        print(f"\n🌍 COUNTRY DISTRIBUTION:")
        country_counts = {}
        for rec in output.all_recommendations:
            country = rec.country or "Unknown"
            country_counts[country] = country_counts.get(country, 0) + 1
        
        for country, count in sorted(country_counts.items(), key=lambda x: x[1], reverse=True)[:10]:
            print(f"  {country}: {count} programs")
        
        return output
        
    finally:
        db.close()


def test_bachelors_filter():
    """
    Test Case 3: Bachelors Degree Filter
    
    Input: Bachelors degree
    Expected:
    - ONLY bachelors programs
    - NO masters/diploma/phd programs
    """
    print("\n" + "=" * 80)
    print("TEST CASE 3: BACHELORS FILTER")
    print("=" * 80)
    
    profile = StudentProfile(
        student_id="test_bachelors",
        target_degree_level="bachelors",
        academic_score_band="good",
        language_score_band="good",
    )
    
    db = SessionLocal()
    try:
        output = run_recommendations(db, profile, limit=100)
        
        print(f"\n📊 RESULTS:")
        print(f"  Total Evaluated: {output.total_candidates_evaluated}")
        print(f"  Total Eligible: {output.total_eligible}")
        print(f"  Total Recommended: {output.total_recommended}")
        
        # Verify degree level enforcement
        print(f"\n🎓 DEGREE LEVEL VERIFICATION:")
        violations = []
        for rec in output.all_recommendations:
            degree_lower = rec.degree_type.lower()
            if not any(pattern in degree_lower for pattern in ["bachelor", "bsc", "ba", "beng", "bs"]):
                violations.append((rec.program_name, rec.degree_type))
        
        if violations:
            print(f"\n❌ DEGREE VIOLATIONS FOUND: {len(violations)}")
            for prog, deg in violations[:5]:
                print(f"  - {prog} ({deg})")
        else:
            print(f"\n✅ NO DEGREE VIOLATIONS - All programs are Bachelors level")
        
        return output
        
    finally:
        db.close()


if __name__ == "__main__":
    print("\n🧪 RECOMMENDATION ENGINE TEST SUITE")
    print("Testing degree level filtering and candidate pool fixes")
    
    try:
        # Test 1: Masters in Ireland
        test_masters_ireland()
        
        # Test 2: Masters broad search
        test_masters_broad()
        
        # Test 3: Bachelors filter
        test_bachelors_filter()
        
        print("\n" + "=" * 80)
        print("✅ TEST SUITE COMPLETE")
        print("=" * 80)
        print("\nPlease review the logs above to verify:")
        print("  1. Degree level is strictly enforced (no violations)")
        print("  2. Large candidate pools are being evaluated")
        print("  3. Realistic recommendation counts (5-20)")
        print("  4. Debug logs show counts at each pipeline stage")
        
    except Exception as e:
        print(f"\n❌ TEST SUITE FAILED")
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
