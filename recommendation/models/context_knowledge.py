from sqlalchemy import Column, Integer, String, Text, DateTime, JSON, Float

from .base import Base


class RecContextKnowledge(Base):
    __tablename__ = "rec_context_knowledge"

    # Identifiers
    id = Column(Integer, primary_key=True)
    program_id = Column(Integer)
    intake_id = Column(Integer)

    # Academic & Program Context
    program_overview = Column(Text)
    curriculum_highlights = Column(Text)
    research_strengths = Column(Text)
    faculty_quality_notes = Column(Text)

    # Career & Outcomes
    career_outcomes_summary = Column(Text)
    industry_connections = Column(Text)
    internship_support_notes = Column(Text)
    alumni_presence_notes = Column(Text)

    # Student Life & Location
    campus_life_overview = Column(Text)
    city_lifestyle_notes = Column(Text)
    cost_of_living_context = Column(Text)
    part_time_work_context = Column(Text)

    # Risk & Reality Checks
    common_challenges = Column(Text)
    who_should_avoid_this_program = Column(Text)
    known_application_pitfalls = Column(Text)

    # LLM Optimization
    context_tags = Column(JSON)
    tone_hint = Column(String)
    confidence_score = Column(Float)

    # Meta
    data_source = Column(String)
    last_updated_at = Column(DateTime)
    context_notes = Column(Text)
