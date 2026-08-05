from app.core.database import Base
from sqlalchemy import TIMESTAMP, Column, ForeignKey, Integer, String, Boolean, text, BigInteger, Float

class Activity(Base):
    __tablename__ = "activity"

    activity_id = Column(BigInteger, primary_key=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    date = Column(TIMESTAMP(timezone=True), nullable=False)

    distance_meters = Column(Float, nullable=False)
    duration_minutes = Column(Float, nullable=False)
    total_elevation_gain = Column(Float)

    average_pace_seconds = Column(Float, nullable=False)

    max_heart_rate = Column(Float, nullable=True)
    heart_rate_zone_1_minutes = Column(Float, nullable=True)
    heart_rate_zone_2_minutes = Column(Float, nullable=True)
    heart_rate_zone_3_minutes = Column(Float, nullable=True)
    heart_rate_zone_4_minutes = Column(Float, nullable=True)
    heart_rate_zone_5_minutes = Column(Float, nullable=True)

    activity_type = Column(String, nullable=True)
    perceived_effort = Column(Integer, nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), server_default=text('now()'))