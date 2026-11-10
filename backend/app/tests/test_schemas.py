"""Request validation rules, tested directly on the schemas (no database, no HTTP)."""

from datetime import date, timedelta

import pytest
from pydantic import ValidationError

from app.schemas.PlanSchema import GenerateManualPlan, GeneratePlan
from app.tests.helpers import manual_plan_body


def strava_plan_body(**overrides) -> dict:
    body = {
        "goal_race_km": 21,
        "race_date": (date.today() + timedelta(weeks=16)).isoformat(),
        "goal_time_min": 110,
        "training_days_per_week": 3,
        "available_days": ["Tuesday", "Thursday", "Saturday"],
        "current_5k_pace": 330,
    }
    body.update(overrides)
    return body


def test_valid_manual_request_is_accepted():
    plan = GenerateManualPlan(**manual_plan_body())
    assert plan.goal_race_km == 10


def test_valid_strava_request_is_accepted():
    plan = GeneratePlan(**strava_plan_body())
    assert plan.current_5k_pace == 330


def test_days_are_cleaned_sorted_and_deduplicated():
    plan = GenerateManualPlan(**manual_plan_body(available_days=["sunday", " Friday", "monday", "Monday", "wednesday"]))
    assert plan.available_days == ["Monday", "Wednesday", "Friday", "Sunday"]


def test_duplicate_days_do_not_count_towards_the_minimum():
    with pytest.raises(ValidationError):
        GenerateManualPlan(**manual_plan_body(available_days=["Monday", "Monday", "Monday", "Friday"]))


@pytest.mark.parametrize("weeks", [5, 53])
def test_race_must_be_between_6_and_52_weeks_away(weeks):
    with pytest.raises(ValidationError):
        GenerateManualPlan(**manual_plan_body(race_date=(date.today() + timedelta(weeks=weeks, days=1)).isoformat()))


@pytest.mark.parametrize("weeks", [6, 52])
def test_race_range_boundaries_are_accepted(weeks):
    GenerateManualPlan(**manual_plan_body(race_date=(date.today() + timedelta(weeks=weeks)).isoformat()))


@pytest.mark.parametrize("distance", [5, 10, 21, 42])
def test_supported_race_distances(distance):
    GenerateManualPlan(**manual_plan_body(goal_race_km=distance))


@pytest.mark.parametrize("distance", [0, 3, 15, 100])
def test_unsupported_race_distances_are_rejected(distance):
    with pytest.raises(ValidationError):
        GenerateManualPlan(**manual_plan_body(goal_race_km=distance))


@pytest.mark.parametrize("pace", [149, 721, 0, -1])
def test_paces_outside_a_human_range_are_rejected(pace):
    with pytest.raises(ValidationError):
        GeneratePlan(**strava_plan_body(current_5k_pace=pace))


def test_pace_is_not_optional_for_strava_plans():
    body = strava_plan_body()
    del body["current_5k_pace"]
    with pytest.raises(ValidationError):
        GeneratePlan(**body)
