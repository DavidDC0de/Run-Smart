from app.core.database import Base
from sqlalchemy import TIMESTAMP, Column, ForeignKey, Integer, String, Boolean, text

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, nullable=False)
    email = Column(String, unique=True, nullable=False)
    password = Column(String, nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=text('now()'))

    strava_access_token = Column(String, nullable=True)
    strava_refresh_token = Column(String, nullable=True)
    strava_token_expires_at = Column(TIMESTAMP(timezone=True), nullable=True)
    strava_athlete_id = Column(String, nullable=True)