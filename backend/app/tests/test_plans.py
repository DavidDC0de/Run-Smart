"""Plan creation, retrieval, ownership, validation and the AI explanations."""

from datetime import datetime, timedelta, timezone

import pytest

from app.models.ActivityModel import Activity
from app.models.ExplanationModel import WeekExplanation
from app.models.SessionModel import Session as TrainingSession
from app.models.UserModel import User
from app.tests.helpers import manual_plan_body

DAY_ORDER = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


def create_plan(client, headers, **overrides) -> dict:
    response = client.post("/plans/generate_manual", json=manual_plan_body(**overrides), headers=headers)
    assert response.status_code == 201, response.text
    return response.json()


# ----------------------------------------------------------------------
# Creating plans
# ----------------------------------------------------------------------
def test_manual_plan_is_created_and_returned_with_an_id(client, auth):
    plan = create_plan(client, auth)

    assert plan["id"] >= 1
    assert plan["goal_race_km"] == 10
    assert plan["training_days_per_week"] == 4
    assert plan["weeks_until_race"] == 20
    assert len(plan["weeks"]) == plan["weeks_until_race"]
    assert [w["week_number"] for w in plan["weeks"]] == list(range(1, 21))


def test_every_week_has_the_requested_number_of_sessions(client, auth):
    plan = create_plan(client, auth)
    for week in plan["weeks"]:
        assert len(week["sessions"]) == 4
        assert week["phase"] in {"base", "build", "race_specific", "taper"}


def test_week_total_is_the_sum_of_its_sessions(client, auth):
    plan = create_plan(client, auth)
    for week in plan["weeks"]:
        assert week["total_km"] == pytest.approx(sum(s["distance_km"] for s in week["sessions"]), abs=0.15)


def test_long_run_lands_on_the_last_chosen_day_whatever_order_days_arrive_in(client, auth):
    plan = create_plan(client, auth, available_days=["Sunday", "Monday", "Friday", "Wednesday"])

    for week in plan["weeks"]:
        days = [s["day"] for s in week["sessions"]]
        assert days == sorted(days, key=DAY_ORDER.index)  # Monday to Sunday
        long_runs = [s for s in week["sessions"] if s["type"] == "long_run"]
        assert len(long_runs) == 1
        assert long_runs[0]["day"] == "Sunday"


def test_lowercase_day_names_are_accepted(client, auth):
    plan = create_plan(client, auth, available_days=["monday", "wednesday", "friday", "sunday"])
    assert plan["weeks"][0]["sessions"][0]["day"] == "Monday"


def test_paces_are_in_seconds_per_km_and_realistic(client, auth):
    plan = create_plan(client, auth)
    for week in plan["weeks"]:
        for session in week["sessions"]:
            assert 150 <= session["pace_sec_per_km"] <= 720


def test_plan_is_saved_atomically_with_all_its_sessions(client, auth, db):
    plan = create_plan(client, auth)
    saved = db.query(TrainingSession).filter(TrainingSession.plan_id == plan["id"]).count()
    assert saved == sum(len(w["sessions"]) for w in plan["weeks"])


# ----------------------------------------------------------------------
# Validation: bad input must give a clean 422, never a 500
# ----------------------------------------------------------------------
@pytest.mark.parametrize(
    "override",
    [
        pytest.param({"race_date": "2020-01-01"}, id="race-in-the-past"),
        pytest.param({"race_date": (datetime.now() + timedelta(weeks=3)).date().isoformat()}, id="race-too-soon"),
        pytest.param({"race_date": (datetime.now() + timedelta(weeks=80)).date().isoformat()}, id="race-too-far"),
        pytest.param({"training_days_per_week": 6}, id="too-many-training-days"),
        pytest.param({"training_days_per_week": 2}, id="too-few-training-days"),
        pytest.param({"available_days": ["Monday", "Funday", "Friday", "Sunday"]}, id="invalid-day-name"),
        pytest.param({"available_days": ["Monday", "Friday"]}, id="fewer-days-than-training-days"),
        pytest.param({"goal_race_km": 7}, id="unsupported-distance"),
        pytest.param({"longest_run_pace": 30}, id="impossible-pace"),
        pytest.param({"average_weekly_km": -5}, id="negative-distance"),
    ],
)
def test_invalid_plan_requests_return_422(client, auth, override):
    response = client.post("/plans/generate_manual", json=manual_plan_body(**override), headers=auth)
    assert response.status_code == 422


def test_goal_time_is_required(client, auth):
    body = manual_plan_body()
    del body["goal_time_min"]
    response = client.post("/plans/generate_manual", json=body, headers=auth)
    assert response.status_code == 422


def test_creating_a_plan_requires_login(client):
    response = client.post("/plans/generate_manual", json=manual_plan_body())
    assert response.status_code == 401


# ----------------------------------------------------------------------
# Reading, listing, deleting
# ----------------------------------------------------------------------
def test_saved_plan_can_be_fetched_and_matches_what_was_created(client, auth):
    created = create_plan(client, auth)
    fetched = client.get(f"/plans/{created['id']}", headers=auth)
    assert fetched.status_code == 200
    assert fetched.json() == created


def test_listing_plans_returns_summaries_newest_first(client, auth):
    first = create_plan(client, auth)
    second = create_plan(client, auth, goal_race_km=21)

    response = client.get("/plans", headers=auth)
    assert response.status_code == 200
    plans = response.json()
    assert [p["id"] for p in plans] == [second["id"], first["id"]]
    assert "weeks" not in plans[0]


def test_users_only_see_their_own_plans(client, auth, other_auth):
    mine = create_plan(client, auth)
    assert client.get("/plans", headers=other_auth).json() == []

    assert client.get(f"/plans/{mine['id']}", headers=other_auth).status_code == 404
    assert client.delete(f"/plans/{mine['id']}", headers=other_auth).status_code == 404
    assert client.get(f"/plans/{mine['id']}/weeks/1/explanation", headers=other_auth).status_code == 404

    # ...and the plan is untouched
    assert client.get(f"/plans/{mine['id']}", headers=auth).status_code == 200


def test_missing_plan_is_404(client, auth):
    assert client.get("/plans/99999", headers=auth).status_code == 404


def test_deleting_a_plan_removes_it_and_its_sessions(client, auth, db):
    plan = create_plan(client, auth)

    response = client.delete(f"/plans/{plan['id']}", headers=auth)
    assert response.status_code == 204

    assert client.get(f"/plans/{plan['id']}", headers=auth).status_code == 404
    assert db.query(TrainingSession).filter(TrainingSession.plan_id == plan["id"]).count() == 0


# ----------------------------------------------------------------------
# Plans built from Strava runs
# ----------------------------------------------------------------------
STRAVA_PLAN_BODY = {
    "goal_race_km": 10,
    "race_date": manual_plan_body()["race_date"],
    "goal_time_min": 55,
    "training_days_per_week": 4,
    "available_days": ["Monday", "Wednesday", "Friday", "Sunday"],
    "current_5k_pace": 330,
}


def test_strava_plan_without_synced_runs_is_a_clear_400(client, auth):
    response = client.post("/plans/generate", json=STRAVA_PLAN_BODY, headers=auth)
    assert response.status_code == 400
    assert "No Strava runs" in response.json()["detail"]


def test_strava_plan_is_built_from_synced_runs(client, auth, db):
    user_id = db.query(User).one().id
    now = datetime.now(timezone.utc)
    for i in range(12):
        db.add(
            Activity(
                activity_id=1000 + i,
                user_id=user_id,
                date=now - timedelta(days=7 * (i + 1)),
                distance_meters=8000.0,
                duration_minutes=48.0,
                average_pace_seconds=360.0,
                total_elevation_gain=20.0,
                activity_type="Run",
            )
        )
    db.commit()

    response = client.post("/plans/generate", json=STRAVA_PLAN_BODY, headers=auth)
    assert response.status_code == 201, response.text
    plan = response.json()
    assert len(plan["weeks"]) == plan["weeks_until_race"]


# ----------------------------------------------------------------------
# AI explanations (OpenAI is replaced by a fake: no network, no cost)
# ----------------------------------------------------------------------
@pytest.fixture
def fake_ai(monkeypatch):
    calls = []

    def fake_explain(week, runner_context=""):
        calls.append(week["week_number"])
        return f"Explanation for week {week['week_number']}"

    monkeypatch.setattr("app.api.plans.explaining_programme_ai", fake_explain)
    return calls


def test_explanation_is_generated_once_then_served_from_the_database(client, auth, fake_ai, db):
    plan = create_plan(client, auth)
    url = f"/plans/{plan['id']}/weeks/3/explanation"

    first = client.get(url, headers=auth)
    second = client.get(url, headers=auth)

    assert first.status_code == second.status_code == 200
    assert first.json() == second.json()
    assert first.json()["explanation"] == "Explanation for week 3"
    assert fake_ai == [3]  # OpenAI was called exactly once
    assert db.query(WeekExplanation).count() == 1


def test_each_week_gets_its_own_explanation(client, auth, fake_ai):
    plan = create_plan(client, auth)
    one = client.get(f"/plans/{plan['id']}/weeks/1/explanation", headers=auth).json()
    two = client.get(f"/plans/{plan['id']}/weeks/2/explanation", headers=auth).json()
    assert one["explanation"] != two["explanation"]
    assert fake_ai == [1, 2]


def test_explanation_for_a_week_outside_the_plan_is_404_and_costs_nothing(client, auth, fake_ai):
    plan = create_plan(client, auth)
    response = client.get(f"/plans/{plan['id']}/weeks/999/explanation", headers=auth)
    assert response.status_code == 404
    assert fake_ai == []


def test_openai_failure_gives_a_502_and_saves_nothing(client, auth, monkeypatch, db):
    plan = create_plan(client, auth)

    def broken(*args, **kwargs):
        raise RuntimeError("OpenAI is down")

    monkeypatch.setattr("app.api.plans.explaining_programme_ai", broken)
    response = client.get(f"/plans/{plan['id']}/weeks/1/explanation", headers=auth)

    assert response.status_code == 502
    assert db.query(WeekExplanation).count() == 0


def test_deleting_a_plan_also_deletes_its_explanations(client, auth, fake_ai, db):
    plan = create_plan(client, auth)
    client.get(f"/plans/{plan['id']}/weeks/1/explanation", headers=auth)
    assert db.query(WeekExplanation).count() == 1

    assert client.delete(f"/plans/{plan['id']}", headers=auth).status_code == 204
    assert db.query(WeekExplanation).count() == 0
