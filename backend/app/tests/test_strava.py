"""
Strava connect flow and run import. Strava itself is never contacted: its HTTP
calls are replaced by fakes, so these tests are fast, free and deterministic.
"""

from urllib.parse import parse_qs, urlparse

import pytest

from app.api import strava as strava_api
from app.models.ActivityModel import Activity
from app.models.UserModel import User
from app.services import strava as strava_service


class FakeResponse:
    def __init__(self, status_code=200, body=None):
        self.status_code = status_code
        self._body = body

    def json(self):
        return self._body


def state_from_connect_url(client, headers) -> str:
    url = client.get("/strava/connect", headers=headers).json()["url"]
    return parse_qs(urlparse(url).query)["state"][0]


# ----------------------------------------------------------------------
# Connect flow
# ----------------------------------------------------------------------
def test_status_is_false_before_connecting(client, auth):
    response = client.get("/strava/status", headers=auth)
    assert response.status_code == 200
    assert response.json() == {"connected": False}


def test_connect_returns_a_strava_url_as_json(client, auth):
    response = client.get("/strava/connect", headers=auth)
    assert response.status_code == 200

    url = urlparse(response.json()["url"])
    query = parse_qs(url.query)
    assert url.netloc == "www.strava.com"
    assert url.path == "/oauth/authorize"
    assert query["scope"] == ["activity:read_all"]
    assert query["response_type"] == ["code"]
    assert query["state"][0]


def test_connect_requires_login(client):
    assert client.get("/strava/connect").status_code == 401


def test_state_belongs_to_the_user_who_asked(client, auth):
    state = state_from_connect_url(client, auth)
    assert strava_api.read_state_token(state) == 1  # first user in a fresh database


def test_state_token_cannot_be_used_to_log_in(client, auth):
    state = state_from_connect_url(client, auth)
    response = client.get("/plans", headers={"Authorization": f"Bearer {state}"})
    assert response.status_code == 401


def signed_state(**claims) -> str:
    """Builds a state token signed with the real secret, so only the claims differ."""
    from jose import jwt

    from app.core.config import settings

    return jwt.encode(claims, settings.secret_key, algorithm=settings.algorithm)


def test_state_with_the_wrong_purpose_is_rejected():
    # Correctly signed and carrying a user id, but not issued for the Strava flow
    from datetime import datetime, timedelta, timezone

    expires = datetime.now(timezone.utc) + timedelta(minutes=5)
    token = signed_state(uid=1, purpose="something_else", exp=expires)
    assert strava_api.read_state_token(token) is None


def test_expired_state_is_rejected():
    from datetime import datetime, timedelta, timezone

    expired = datetime.now(timezone.utc) - timedelta(minutes=1)
    token = signed_state(uid=1, purpose="strava_oauth", exp=expired)
    assert strava_api.read_state_token(token) is None


def test_state_signed_with_a_different_secret_is_rejected():
    from datetime import datetime, timedelta, timezone

    from jose import jwt

    expires = datetime.now(timezone.utc) + timedelta(minutes=5)
    token = jwt.encode({"uid": 1, "purpose": "strava_oauth", "exp": expires}, "not-the-real-secret", algorithm="HS256")
    assert strava_api.read_state_token(token) is None


def test_forged_state_is_rejected(client):
    response = client.get("/strava/callback?state=forged&code=abc", follow_redirects=False)
    assert response.status_code == 302
    assert response.headers["location"].endswith("/strava/callback?status=invalid_state")


def test_login_token_cannot_be_used_as_state(client, auth):
    login_token = auth["Authorization"].removeprefix("Bearer ")
    response = client.get(f"/strava/callback?state={login_token}&code=abc", follow_redirects=False)
    assert response.headers["location"].endswith("status=invalid_state")


def test_user_denying_access_is_handled(client, auth):
    state = state_from_connect_url(client, auth)
    response = client.get(f"/strava/callback?state={state}&error=access_denied", follow_redirects=False)
    assert response.status_code == 302
    assert response.headers["location"].endswith("status=denied")


def test_successful_callback_stores_tokens_and_redirects_to_the_frontend(client, auth, db, monkeypatch):
    def fake_token_exchange(url, data=None, **kwargs):
        assert url == "https://www.strava.com/oauth/token"
        assert data["code"] == "the-code"
        assert data["grant_type"] == "authorization_code"
        return FakeResponse(
            200,
            {
                "access_token": "access-123",
                "refresh_token": "refresh-123",
                "expires_at": 4102444800,  # year 2100
                "athlete": {"id": 424242},
            },
        )

    monkeypatch.setattr(strava_api.httpx, "post", fake_token_exchange)
    state = state_from_connect_url(client, auth)

    response = client.get(f"/strava/callback?state={state}&code=the-code", follow_redirects=False)

    assert response.status_code == 302
    assert response.headers["location"].endswith("/strava/callback?status=connected")
    user = db.query(User).one()
    assert user.strava_access_token == "access-123"
    assert user.strava_athlete_id == "424242"
    assert client.get("/strava/status", headers=auth).json() == {"connected": True}


def test_strava_rejecting_the_code_is_handled(client, auth, monkeypatch):
    monkeypatch.setattr(strava_api.httpx, "post", lambda *a, **k: FakeResponse(400, {"message": "Bad Request"}))
    state = state_from_connect_url(client, auth)
    response = client.get(f"/strava/callback?state={state}&code=bad", follow_redirects=False)
    assert response.headers["location"].endswith("status=token_exchange_failed")


# ----------------------------------------------------------------------
# Sync and disconnect
# ----------------------------------------------------------------------
def connect_user(db):
    user = db.query(User).one()
    user.strava_access_token = "access-123"
    user.strava_refresh_token = "refresh-123"
    db.commit()


def test_sync_requires_a_connected_account(client, auth):
    response = client.get("/strava/sync", headers=auth)
    assert response.status_code == 400
    assert response.json()["detail"] == "Strava is not connected"


def test_sync_reports_what_it_found_and_saved(client, auth, db, monkeypatch):
    connect_user(db)

    def fake_get_activities(user, session):
        # three activities from Strava, as the importer would have stored them
        session.add(
            Activity(
                activity_id=1,
                user_id=user.id,
                date="2026-10-01T08:00:00Z",
                distance_meters=5000.0,
                duration_minutes=25.0,
                average_pace_seconds=300.0,
                activity_type="Run",
            )
        )
        session.commit()
        return [{"id": 1}, {"id": 2}, {"id": 3}]

    monkeypatch.setattr(strava_api, "get_strava_activities", fake_get_activities)

    response = client.get("/strava/sync", headers=auth)
    assert response.status_code == 200
    assert response.json() == {"activities_found": 3, "runs_saved": 1}


def test_sync_failure_is_a_502(client, auth, db, monkeypatch):
    connect_user(db)

    def failing(user, session):
        raise strava_api.StravaError("Strava returned 500")

    monkeypatch.setattr(strava_api, "get_strava_activities", failing)
    assert client.get("/strava/sync", headers=auth).status_code == 502


def test_disconnect_clears_tokens_and_imported_runs(client, auth, db):
    connect_user(db)
    db.add(
        Activity(
            activity_id=7,
            user_id=db.query(User).one().id,
            date="2026-10-01T08:00:00Z",
            distance_meters=5000.0,
            duration_minutes=25.0,
            average_pace_seconds=300.0,
        )
    )
    db.commit()

    assert client.delete("/strava/disconnect", headers=auth).status_code == 204

    db.expire_all()
    assert client.get("/strava/status", headers=auth).json() == {"connected": False}
    assert db.query(Activity).count() == 0


# ----------------------------------------------------------------------
# The importer itself (services/strava.py)
# ----------------------------------------------------------------------
def raw_activity(activity_id, sport="Run", distance=5000.0):
    return {
        "id": activity_id,
        "type": sport,
        "sport_type": sport,
        "start_date": "2026-10-01T08:00:00Z",
        "distance": distance,
        "moving_time": 1500,
        "total_elevation_gain": 12.0,
        "max_heartrate": 170,
    }


HEART_RATE_ZONES = [
    {
        "type": "heartrate",
        "distribution_buckets": [{"time": 60}, {"time": 120}, {"time": 180}, {"time": 60}, {"time": 0}],
    }
]


@pytest.fixture
def user_in_db(client, auth, db):
    connect_user(db)
    return db.query(User).one()


def test_importer_saves_runs_and_skips_other_sports(user_in_db, db, monkeypatch):
    monkeypatch.setattr(strava_service.httpx, "get", lambda *a, **k: FakeResponse(200, HEART_RATE_ZONES))
    activities = [raw_activity(1), raw_activity(2, sport="Ride"), raw_activity(3, sport="TrailRun")]

    strava_service.process_activity(activities, user_in_db, db)

    saved = {a.activity_id: a for a in db.query(Activity).all()}
    assert set(saved) == {1, 3}  # the ride was skipped
    assert saved[1].activity_type == "Run"
    assert saved[1].heart_rate_zone_2_minutes == pytest.approx(2.0)
    assert saved[1].average_pace_seconds == pytest.approx(300.0)  # 1500 s over 5 km


def test_importer_does_not_create_duplicates(user_in_db, db, monkeypatch):
    monkeypatch.setattr(strava_service.httpx, "get", lambda *a, **k: FakeResponse(200, HEART_RATE_ZONES))
    strava_service.process_activity([raw_activity(1)], user_in_db, db)
    strava_service.process_activity([raw_activity(1)], user_in_db, db)
    assert db.query(Activity).count() == 1


@pytest.mark.parametrize(
    "zones_reply",
    [
        pytest.param(FakeResponse(402, {"message": "Payment Required"}), id="non-premium-account"),
        pytest.param(FakeResponse(429, {"message": "Rate Limit Exceeded"}), id="rate-limited"),
    ],
)
def test_importer_survives_strava_refusing_heart_rate_zones(user_in_db, db, monkeypatch, zones_reply):
    monkeypatch.setattr(strava_service.httpx, "get", lambda *a, **k: zones_reply)

    strava_service.process_activity([raw_activity(1)], user_in_db, db)

    saved = db.query(Activity).one()
    assert saved.heart_rate_zone_2_minutes == 0  # run still saved, just without zones


def test_importer_handles_a_zero_distance_run(user_in_db, db, monkeypatch):
    monkeypatch.setattr(strava_service.httpx, "get", lambda *a, **k: FakeResponse(200, []))
    strava_service.process_activity([raw_activity(1, distance=0.0)], user_in_db, db)
    assert db.query(Activity).one().average_pace_seconds == 0
