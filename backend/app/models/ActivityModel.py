from app.core.database import Base
from sqlalchemy import TIMESTAMP, Column, ForeignKey, Integer, String, Boolean, text

class Activity(Base):
    __tablename__ = "activity"

    activity_id = Column(Integer, primary_key=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    date = Column(TIMESTAMP(timezone=True), nullable=False)

    distance_meters = Column(Integer, nullable=False)
    duration_minutes = Column(Integer, nullable=False)
    total_elevation_gain = Column(Integer)

    average_pace_seconds = Column(Integer, nullable=False)

    max_heart_rate = Column(Integer, nullable=False)
    heart_rate_zone_1_minutes = Column(Integer, nullable=False)
    heart_rate_zone_2_minutes = Column(Integer, nullable=False)
    heart_rate_zone_3_minutes = Column(Integer, nullable=False)
    heart_rate_zone_4_minutes = Column(Integer, nullable=False)
    heart_rate_zone_5_minutes = Column(Integer, nullable=False)

    activity_type = Column(String, nullable=True)
    perceived_effort = Column(Integer)
    created_at = Column(TIMESTAMP(timezone=True), server_default=text('now()'))