from sqlalchemy import Column, Integer, String, Text, DateTime, JSON

from .base import Base


class RecEligibilitySnapshot(Base):
    __tablename__ = "rec_eligibility_snapshots"

    id = Column(Integer, primary_key=True)
    intake_id = Column(Integer)

    # Core Eligibility Signals
    academic_score_band = Column(String)
    language_score_band = Column(String)
    background_match_level = Column(String)
    minimum_degree_requirement = Column(String)

    # Profile-Sensitive Signals
    work_experience_preference = Column(String)
    work_experience_years_band = Column(String)
    gap_year_tolerance_level = Column(String)
    academic_consistency_preference = Column(String)
    research_experience_preference = Column(String)

    # Intake Behavior Signals
    historical_acceptance_strictness = Column(String)
    borderline_profile_acceptance = Column(String)
    competition_level_this_intake = Column(String)

    # Risk & Explainability
    eligibility_risk_level = Column(String)
    key_risk_factors = Column(JSON)
    improvement_suggestions = Column(JSON)

    # Meta & Governance
    eligibility_confidence_level = Column(String)
    last_verified_at = Column(DateTime)
    data_source = Column(String)
    eligibility_notes = Column(Text)
