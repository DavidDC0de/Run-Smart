from sqlalchemy import TIMESTAMP, Column, ForeignKey, Integer, Text, UniqueConstraint, text
from app.core.database import Base


class WeekExplanation(Base):
    __tablename__ = "WeekExplanation"

    id = Column(Integer, primary_key=True, autoincrement=True)
    plan_id = Column(Integer, ForeignKey("TrainingPlan.id"), nullable=False)
    week_number = Column(Integer, nullable=False)
    explanation = Column(Text, nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), server_default=text("now()"))

    __table_args__ = (
        UniqueConstraint("plan_id", "week_number", name="uq_week_explanation_plan_week"),
    )