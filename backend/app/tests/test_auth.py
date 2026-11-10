"""Signup, login and token handling, tested through the real HTTP API."""

from app.models.UserModel import User

from app.tests.helpers import PASSWORD, manual_plan_body, register


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_signup_returns_user_without_password(client):
    response = client.post("/user/signup", json={"email": "a@example.com", "password": PASSWORD})
    assert response.status_code == 201
    body = response.json()
    assert body["email"] == "a@example.com"
    assert "id" in body
    assert "password" not in body


def test_password_is_stored_hashed(client, db):
    client.post("/user/signup", json={"email": "a@example.com", "password": PASSWORD})
    stored = db.query(User).filter(User.email == "a@example.com").one()
    assert stored.password != PASSWORD
    assert stored.password.startswith("$2")  # bcrypt hash


def test_signup_duplicate_email_is_409(client):
    client.post("/user/signup", json={"email": "a@example.com", "password": PASSWORD})
    response = client.post("/user/signup", json={"email": "a@example.com", "password": PASSWORD})
    assert response.status_code == 409
    assert response.json()["detail"] == "Email already registered"


def test_signup_rejects_short_password(client):
    response = client.post("/user/signup", json={"email": "a@example.com", "password": "short"})
    assert response.status_code == 422


def test_signup_rejects_invalid_email(client):
    response = client.post("/user/signup", json={"email": "not-an-email", "password": PASSWORD})
    assert response.status_code == 422


def test_login_returns_bearer_token(client):
    client.post("/user/signup", json={"email": "a@example.com", "password": PASSWORD})
    response = client.post("/user/login", data={"username": "a@example.com", "password": PASSWORD})
    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]


def test_login_wrong_password_is_403(client):
    client.post("/user/signup", json={"email": "a@example.com", "password": PASSWORD})
    response = client.post("/user/login", data={"username": "a@example.com", "password": "wrong-password"})
    assert response.status_code == 403
    assert isinstance(response.json()["detail"], str)  # plain-string error shape


def test_login_unknown_email_is_403(client):
    response = client.post("/user/login", data={"username": "nobody@example.com", "password": PASSWORD})
    assert response.status_code == 403


def test_login_expects_a_form_not_json(client):
    # Documents a trap for frontends: login is form-encoded, with the email in "username"
    client.post("/user/signup", json={"email": "a@example.com", "password": PASSWORD})
    response = client.post("/user/login", json={"username": "a@example.com", "password": PASSWORD})
    assert response.status_code == 422


def test_protected_route_requires_token(client):
    response = client.get("/plans")
    assert response.status_code == 401


def test_garbage_token_is_rejected(client):
    response = client.get("/plans", headers={"Authorization": "Bearer abc123"})
    assert response.status_code == 401


def test_token_for_deleted_user_is_rejected(client, db):
    headers = register(client)
    assert client.get("/plans", headers=headers).status_code == 200

    db.query(User).delete()
    db.commit()

    assert client.get("/plans", headers=headers).status_code == 401


def test_validation_errors_use_the_list_shape(client, auth):
    # 422s carry `detail` as a LIST of problems, unlike the string errors above.
    # The frontend's errorMessage() depends on this.
    response = client.post("/plans/generate_manual", json=manual_plan_body(training_days_per_week=9), headers=auth)
    assert response.status_code == 422
    detail = response.json()["detail"]
    assert isinstance(detail, list)
    assert {"loc", "msg"} <= set(detail[0])
