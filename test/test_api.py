import pytest
from trading_engine.api import TradingEngineAPI
from trading_engine.engine import TradingEngine


@pytest.fixture(scope="module")
def test_engine():
    return TradingEngine()


@pytest.fixture(scope="module")
def test_app(test_engine):
    jwt_secret_key = "test_secret_key"
    allowed_users_passwords = [("user1", "pass1"), ("user2", "pass2")]
    api = TradingEngineAPI(
        test_engine,
        jwt_secret_key,
        allowed_users_passwords,
        debug=True,
    )
    return api.app


def test_login(test_app):
    client = test_app.test_client()
    response = client.post("/login", json={"username": "user1", "password": "pass1"})
    assert response.status_code == 200
    assert "access_token" in response.json


def test_login_invalid_credentials(test_app):
    client = test_app.test_client()
    response = client.post(
        "/login", json={"username": "invalid_user", "password": "invalid_pass"}
    )
    assert response.status_code == 401
    assert "access_token" not in response.json


def test_start_engine(test_app):
    client = test_app.test_client()
    with client:
        access_token = client.post(
            "/login", json={"username": "user1", "password": "pass1"}
        ).json["access_token"]
        headers = {"Authorization": f"Bearer {access_token}"}
        response = client.post("/start", headers=headers)
        assert response.status_code == 200
        assert response.json["status"] == "success"
        assert response.json["message"] == "Started TradingEngine"


def test_stop_engine(test_app):
    client = test_app.test_client()
    with client:
        access_token = client.post(
            "/login", json={"username": "user1", "password": "pass1"}
        ).json["access_token"]
        headers = {"Authorization": f"Bearer {access_token}"}
        response = client.post("/stop", headers=headers)
        assert response.status_code == 200
        assert response.json["status"] == "success"
        assert response.json["message"] == "Stopped TradingEngine"


def test_engine_stats_not_running(test_app):
    client = test_app.test_client()
    with client:
        access_token = client.post(
            "/login", json={"username": "user1", "password": "pass1"}
        ).json["access_token"]
        headers = {"Authorization": f"Bearer {access_token}"}
        response = client.get("/stats", headers=headers)
        assert response.status_code == 404
        assert response.json["status"] == "error"
        assert response.json["message"] == "Engine is not running"


def test_update_engine(test_app):
    client = test_app.test_client()
    with client:
        access_token = client.post(
            "/login", json={"username": "user1", "password": "pass1"}
        ).json["access_token"]
        headers = {"Authorization": f"Bearer {access_token}"}
        response = client.post("/update", headers=headers)
        assert response.status_code == 200
        assert response.json["status"] == "success"
        assert response.json["message"] == "Updated TradingEngine"
