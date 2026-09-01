from app.core.database import Base
from sqlalchemy import TIMESTAMP, Column, ForeignKey, Integer, String, Boolean, text, BigInteger, Float

class TrainingPlan(Base):
    __tablename__ = "TrainingPlan"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    goal_race_km = Column(Integer, nullable=False)
    goal_time_min = Column(Float, nullable=True)
    race_date = Column(TIMESTAMP(timezone=True), nullable=False)
    weeks_until_race = Column(Integer, nullable=False)
    training_days_per_week = Column(Integer, nullable=False)
    status = Column(String, nullable=False, server_default='active')
    created_at = Column(TIMESTAMP(timezone=True), server_default=text("now()"))

