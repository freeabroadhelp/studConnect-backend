"""
Candidate Generator

Fetches and filters candidate programs from the database based on student preferences.
Applies initial filtering to reduce the candidate pool before scoring.
"""

from typing import List, Optional
from sqlalchemy.orm import Session

from .contracts import StudentProfile, CandidateProgram
from ..models import RecUniversity, RecProgram, RecIntake, RecEligibilitySnapshot


def generate_candidates(
    db: Session,
    profile: StudentProfile,
    max_candidates: int = 200
) -> List[CandidateProgram]:
    """
    Generate candidate programs based on student profile preferences.
    
    Applies initial filtering:
    - Country preferences (if specified)
    - Program domain preferences (if specified)  
    - Target degree level
    - Target intake timing
    
    Args:
        db: Database session
        profile: Student's profile and preferences
        max_candidates: Maximum number of candidates to return
        
    Returns:
        List of CandidateProgram objects ready for scoring
    """
    candidates: List[CandidateProgram] = []
    
    # Build base query joining all recommendation tables
    query = db.query(
        RecProgram,
        RecUniversity,
        RecIntake,
        RecEligibilitySnapshot
    ).join(
        RecUniversity,
        RecProgram.university_id == RecUniversity.id
    ).outerjoin(
        RecIntake,
        RecIntake.program_id == RecProgram.id
    ).outerjoin(
        RecEligibilitySnapshot,
        RecEligibilitySnapshot.intake_id == RecIntake.id
    )
    
    # Apply filters based on preferences
    
    # Country filter
    if profile.preferred_countries:
        query = query.filter(
            RecUniversity.country.in_(profile.preferred_countries)
        )
    
    # Degree type filter (map target_degree_level to degree types)
    degree_type_map = {
        "masters": ["masters", "mba", "ms", "ma", "msc", "meng"],
        "phd": ["phd", "doctorate", "doctoral"],
        "bachelors": ["bachelors", "bs", "ba", "bsc", "beng"],
        "diploma": ["diploma", "certificate", "postgraduate_diploma"],
    }
    target_degree_types = degree_type_map.get(
        profile.target_degree_level, 
        ["masters"]
    )
    query = query.filter(
        RecProgram.degree_type.in_(target_degree_types)
    )
    
    # Program domain filter
    if profile.preferred_program_domains:
        # Use ILIKE for flexible matching
        domain_filters = []
        for domain in profile.preferred_program_domains:
            domain_filters.append(
                RecProgram.program_domain.ilike(f"%{domain}%")
            )
        if domain_filters:
            from sqlalchemy import or_
            query = query.filter(or_(*domain_filters))
    
    # Intake timing filter
    if profile.target_intake_year:
        query = query.filter(
            RecIntake.intake_year == profile.target_intake_year
        )
    if profile.target_intake_term:
        query = query.filter(
            RecIntake.intake_term.ilike(f"%{profile.target_intake_term}%")
        )
    
    # Active intakes only
    query = query.filter(
        RecIntake.intake_status.in_(["open", "upcoming", "active", None])
    )
    
    # Limit results
    query = query.limit(max_candidates)
    
    # Execute query and build candidates
    results = query.all()
    
    for program, university, intake, eligibility in results:
        candidate = _build_candidate(program, university, intake, eligibility)
        candidates.append(candidate)
    
    return candidates


def _build_candidate(
    program: RecProgram,
    university: RecUniversity,
    intake: Optional[RecIntake],
    eligibility: Optional[RecEligibilitySnapshot]
) -> CandidateProgram:
    """
    Build a CandidateProgram from database models.
    """
    return CandidateProgram(
        # IDs
        program_id=program.id,
        university_id=university.id,
        intake_id=intake.id if intake else None,
        
        # University data
        university_name=university.name or "",
        country=university.country or "",
        city=university.city or "",
        global_reputation_band=university.global_reputation_band or "unknown",
        institution_type=university.institution_type or "",
        
        # Program data
        program_name=program.program_name or "",
        degree_type=program.degree_type or "",
        program_domain=program.program_domain or "",
        tuition_fee_band=program.tuition_fee_band or "unknown",
        program_competitiveness_band=program.program_competitiveness_band or "unknown",
        delivery_mode=program.delivery_mode or "",
        typical_duration_months=program.typical_duration_months or 0,
        background_preference_tags=program.background_preference_tags or [],
        industry_alignment_tags=program.industry_alignment_tags or [],
        internship_opportunities=program.internship_opportunities or "",
        
        # Intake data
        intake_term=intake.intake_term if intake else "",
        intake_year=intake.intake_year if intake else 0,
        application_open_date=intake.application_open_date if intake else None,
        application_close_date=intake.application_close_date if intake else None,
        intake_status=intake.intake_status if intake else "",
        
        # Eligibility snapshot data
        academic_score_band=eligibility.academic_score_band if eligibility else "unknown",
        language_score_band=eligibility.language_score_band if eligibility else "unknown",
        background_match_level=eligibility.background_match_level if eligibility else "unknown",
        work_experience_preference=eligibility.work_experience_preference if eligibility else "neutral",
        gap_year_tolerance_level=eligibility.gap_year_tolerance_level if eligibility else "moderate",
        historical_acceptance_strictness=eligibility.historical_acceptance_strictness if eligibility else "moderate",
        competition_level_this_intake=eligibility.competition_level_this_intake if eligibility else "moderate",
    )


def generate_mock_candidates(
    profile: StudentProfile,
    count: int = 10
) -> List[CandidateProgram]:
    """
    Generate mock candidates for testing without database.
    
    Args:
        profile: Student profile
        count: Number of mock candidates to generate
        
    Returns:
        List of mock CandidateProgram objects
    """
    candidates = []
    
    mock_data = [
        ("MIT", "Computer Science", "USA", "Cambridge", "top_10", "excellent"),
        ("Stanford", "Data Science", "USA", "Stanford", "top_10", "excellent"),
        ("UC Berkeley", "Software Engineering", "USA", "Berkeley", "top_50", "good"),
        ("Georgia Tech", "Machine Learning", "USA", "Atlanta", "top_50", "good"),
        ("University of Toronto", "AI", "Canada", "Toronto", "top_50", "good"),
        ("University of British Columbia", "CS", "Canada", "Vancouver", "top_100", "average"),
        ("TU Munich", "Informatics", "Germany", "Munich", "top_100", "good"),
        ("ETH Zurich", "Computer Science", "Switzerland", "Zurich", "top_10", "excellent"),
        ("Imperial College", "Computing", "UK", "London", "top_10", "excellent"),
        ("University of Melbourne", "IT", "Australia", "Melbourne", "top_100", "average"),
    ]
    
    for i, (uni, prog, country, city, rep, academic) in enumerate(mock_data[:count]):
        candidate = CandidateProgram(
            program_id=i + 1,
            university_id=i + 1,
            intake_id=i + 1,
            university_name=uni,
            program_name=prog,
            country=country,
            city=city,
            global_reputation_band=rep,
            degree_type="masters",
            program_domain="Computer Science",
            tuition_fee_band="high" if "USA" in country else "moderate",
            academic_score_band=academic,
            language_score_band="good",
            background_match_level="good_match",
            work_experience_preference="preferred",
            gap_year_tolerance_level="moderate",
            competition_level_this_intake="high" if rep == "top_10" else "moderate",
            intake_term="Fall",
            intake_year=2026,
        )
        candidates.append(candidate)
    
    return candidates
