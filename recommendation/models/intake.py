from sqlalchemy import Column, Integer, String, Date, DateTime, Text

from .base import Base


class RecIntake(Base):
    __tablename__ = "rec_intakes"

    id = Column(Integer, primary_key=True)
    program_id = Column(Integer)
    intake_term = Column(String)
    intake_year = Column(Integer)
    application_open_date = Column(Date)
    application_close_date = Column(Date)
    intake_status = Column(String)
    seats_estimate_band = Column(String)
    data_confidence_level = Column(String)
    last_verified_at = Column(DateTime)
    data_source = Column(String)
    notes = Column(Text)
