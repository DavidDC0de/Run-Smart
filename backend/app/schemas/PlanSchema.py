from datetime import date, timedelta, datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

# The phase split in determine_phases() needs at least 6 weeks to make sense.
# The upper limit stops someone requesting a plan that takes ages to save.
# Change these two numbers if you want different limits.
MIN_WEEKS_TO_RACE = 6
MAX_WEEKS_TO_RACE = 52


# ------------------------------------------------------------------
# Requests
# ------------------------------------------------------------------
class PlanRequestBase(BaseModel):
    goal_race_km: Literal[5, 10, 21, 42]
    race_date: date
    training_days_per_week: int = Field(ge=3, le=5)
    available_days: list[str]
    goal_time_min: float = Field(gt=0)  # goal finish time in minutes

    @field_validator("available_days")
    @classmethod
    def clean_days(cls, v: list[str]) -> list[str]:
        cleaned = {d.strip().capitalize() for d in v}
        invalid = cleaned - set(DAYS)
        if invalid:
            raise ValueError(f"Invalid day(s): {sorted(invalid)}. Use full English day names.")
        # Sort Monday -> Sunday so the long run lands on the latest chosen day
        return sorted(cleaned, key=DAYS.index)

    @field_validator("race_date")
    @classmethod
    def race_date_in_range(cls, v: date) -> date:
        today = date.today()
        if v < today + timedelta(weeks=MIN_WEEKS_TO_RACE):
            raise ValueError(f"Race must be at least {MIN_WEEKS_TO_RACE} weeks away.")
        if v > today + timedelta(weeks=MAX_WEEKS_TO_RACE):
            raise ValueError(f"Race must be no more than {MAX_WEEKS_TO_RACE} weeks away.")
        return v

    @model_validator(mode="after")
    def enough_available_days(self):
        if len(self.available_days) < self.training_days_per_week:
            raise ValueError("Select at least as many available days as training days per week.")
        return self


class GeneratePlan(PlanRequestBase):
    # Pace in SECONDS per km (400 = 6:40 /km). Range is 2:30 to 12:00 /km.
    current_5k_pace: float = Field(ge=150, le=720)


class GenerateManualPlan(PlanRequestBase):
    average_weekly_km: float = Field(ge=0, le=300)
    longest_run_km: float = Field(ge=0, le=100)
    weeks_trained_last_8: int = Field(ge=0, le=8)
    longest_run_pace: float = Field(ge=150, le=720)  # seconds per km


# ------------------------------------------------------------------
# Responses (wired into the endpoints in the next step)
# ------------------------------------------------------------------
class SessionOut(BaseModel):
    day: str
    type: Literal["easy", "interval", "tempo", "long_run"]
    distance_km: float
    pace_sec_per_km: int


class WeekOut(BaseModel):
    week_number: int
    phase: Literal["base", "build", "race_specific", "taper"]
    total_km: float
    sessions: list[SessionOut]

class PlanSummaryOut(BaseModel):
    id: int
    goal_race_km: int
    goal_time_min: float | None
    race_date: date
    weeks_until_race: int
    training_days_per_week: int
    status: str
    created_at: datetime


class PlanDetailOut(PlanSummaryOut):
    weeks: list[WeekOut]


class ExplanationOut(BaseModel):
    plan_id: int
    week_number: int
    explanation: str