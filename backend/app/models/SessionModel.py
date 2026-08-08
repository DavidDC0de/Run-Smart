
from app.core.database import Base
from sqlalchemy import TIMESTAMP, Column, ForeignKey, Integer, String, Boolean, text, BigInteger, Float

class Session(Base):
    __tablename__ = "TrainingSession"

    id = Column(Integer, primary_key=True, nullable=False)
    plan_id = Column(Integer, ForeignKey("TrainingPlan.id"), nullable=False)
    week_number = Column(Integer, nullable=False)
    day_of_week = Column(String, nullable=False)
    session_type = Column(String, nullable=False)
    target_distance = Column(Float, nullable=False)
    target_pace = Column(Float, nullable=False)
    target_heart_rate_zone = Column(Integer, nullable=False)
    description = Column(String, nullable=False)
    completed = Column(Boolean, nullable=False, server_default = text("false"))
    completed_at = Column(TIMESTAMP(timezone=True))

