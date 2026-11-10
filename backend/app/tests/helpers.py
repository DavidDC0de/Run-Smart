"""Plain helper functions shared by the API tests (fixtures live in conftest.py)."""

from datetime import date, timedelta

PASSWORD = "correct-horse-battery"


def register(client, email="runner@example.com", password=PASSWORD) -> dict:
    """Creates a user, logs in the way the real frontend does (a form), and
    returns the Authorization headers."""
    response = client.post("/user/signup", json={"email": email, "password": password})
    assert response.status_code == 201, response.text
    login = client.post("/user/login", data={"username": email, "password": password})
    assert login.status_code == 200, login.text
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def manual_plan_body(**overrides) -> dict:
    """A valid request body for POST /plans/generate_manual."""
    body = {
        "goal_race_km": 10,
        "race_date": (date.today() + timedelta(weeks=20, days=3)).isoformat(),
        "goal_time_min": 55,
        "training_days_per_week": 4,
        "available_days": ["Monday", "Wednesday", "Friday", "Sunday"],
        "average_weekly_km": 25,
        "longest_run_km": 10,
        "weeks_trained_last_8": 6,
        "longest_run_pace": 400,
    }
    body.update(overrides)
    return body
