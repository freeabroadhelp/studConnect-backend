from sqlalchemy import Column, Integer, String, Text, DateTime

from .base import Base


class RecUniversity(Base):
    __tablename__ = "rec_universities"

    id = Column(Integer, primary_key=True)
    name = Column(String)
    country = Column(String)
    city = Column(String)
    institution_type = Column(String)
    global_reputation_band = Column(String)
    primary_language = Column(String)
    university_category = Column(String)
    campus_type = Column(String)
    country_region = Column(String)
    data_source = Column(String)
    confidence_level = Column(String)
    last_reviewed_at = Column(DateTime)
    notes = Column(Text)
