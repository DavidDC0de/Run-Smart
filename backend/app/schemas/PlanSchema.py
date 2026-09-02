from pydantic import BaseModel
from datetime import date
from typing import Optional

class GeneratePlan(BaseModel):
    goal_race_km: int          # 5, 10, 21, 42
    race_date: date            # when is the race
    training_days_per_week: int  # how many days can they train
    available_days: list[str]  # e.g. ["Monday", "Wednesday", "Saturday"]
    goal_time_min: Optional[float] = None  # optional goal finish time in minutes
    current_5k_pace: Optional[float]  #currnet pace for a 5k run


class GenerateManualPlan(BaseModel):
    average_weekly_km: int
    longest_run_km: float #current longest run
    weeks_trained_last_8: int #consistancy over last 8 weeks
    goal_race_km: int          # 5, 10, 21, 42
    race_date: date            # when is the race
    training_days_per_week: int  # how many days can they train
    available_days: list[str]  # e.g. ["Monday", "Wednesday", "Saturday"]
    goal_time_min: Optional[float] = None  # optional goal finish time in minutes 
    longest_run_pace: float