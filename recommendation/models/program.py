from sqlalchemy import Column, Integer, String, Text, JSON

from .base import Base


class RecProgram(Base):
    __tablename__ = "rec_programs"

    id = Column(Integer, primary_key=True)
    university_id = Column(Integer)
    degree_type = Column(String)
    program_domain = Column(String)
    program_name = Column(String)
    language_of_instruction = Column(String)
    typical_duration_months = Column(Integer)
    tuition_fee_band = Column(String)
    program_orientation = Column(String)
    delivery_mode = Column(String)
    program_competitiveness_band = Column(String)
    background_preference_tags = Column(JSON)
    industry_alignment_tags = Column(JSON)
    typical_class_size_band = Column(String)
    internship_opportunities = Column(String)
    career_outcomes_focus = Column(Text)
