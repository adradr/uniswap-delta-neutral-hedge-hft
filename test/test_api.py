from unittest.mock import MagicMock

import pytest
from trading_engine.api import TradingEngineAPI
from trading_engine.engine import TradingEngine


@pytest.fixture(scope="module")
def test_engine():
    trading_engine = TradingEngine(
        poolAddress="0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640",
        poolFee=500,
        walletAddress="0x1234567890123456789012345678901234567890",
        walletPrivateKey="0x1234567890123456789012345678901234567890123456789012345678901234",
        range_percentage=0,
        capital_percentage=0,
        provider="http://cloudflare-eth.com",
    )

    trading_engine.start = MagicMock()
    trading_engine.stop = MagicMock()
    trading_engine.update = MagicMock()
    trading_engine.get_stats = MagicMock()
    trading_engine.running = False
    trading_engine.web3_manager.position_history = [{"test": "test"}]

    return trading_engine


@pytest.fixture(scope="module")
def test_app(test_engine):
    jwt_secret_key = "test_secret_key"
    jwt_access_token_expires = 300
    allowed_users_passwords = [("user1", "pass1"), ("user2", "pass2")]
    return TradingEngineAPI(
        test_engine,
        allowed_users_passwords,
        jwt_secret_key,
        jwt_access_token_expires,
        debug=True,
    )


def test_login(test_app):
    client = test_app.app.test_client()
    response = client.post("/login", json={"username": "user1", "password": "pass1"})
    assert response.status_code == 200
    assert "access_token" in response.json


def test_login_invalid_credentials(test_app):
    client = test_app.app.test_client()
    response = client.post(
        "/login", json={"username": "invalid_user", "password": "invalid_pass"}
    )
    assert response.status_code == 401
    assert "access_token" not in response.json


def test_start_engine(test_app):
    client = test_app.app.test_client()
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
    client = test_app.app.test_client()
    with client:
        access_token = client.post(
            "/login", json={"username": "user1", "password": "pass1"}
        ).json["access_token"]
        headers = {"Authorization": f"Bearer {access_token}"}
        response = client.post("/stop", headers=headers)
        assert response.status_code == 200
        assert response.json["status"] == "success"
        assert response.json["message"] == "Stopped TradingEngine"


def test_update_engine(test_app):
    client = test_app.app.test_client()
    with client:
        access_token = client.post(
            "/login", json={"username": "user1", "password": "pass1"}
        ).json["access_token"]
        headers = {"Authorization": f"Bearer {access_token}"}
        response = client.post("/update", headers=headers)
        assert response.status_code == 404
        assert response.json["status"] == "error"
        assert response.json["message"] == "Engine is not running"


def test_engine_stats_not_running(test_app):
    client = test_app.app.test_client()
    with client:
        access_token = client.post(
            "/login", json={"username": "user1", "password": "pass1"}
        ).json["access_token"]
        headers = {"Authorization": f"Bearer {access_token}"}
        response = client.get("/stats", headers=headers)
        assert response.status_code == 404
        assert response.json["status"] == "error"
        assert response.json["message"] == "Engine is not running"


def test_engine_stats_running(test_app):
    client = test_app.app.test_client()
    test_app.engine.running = True
    with client:
        access_token = client.post(
            "/login", json={"username": "user1", "password": "pass1"}
        ).json["access_token"]
        headers = {"Authorization": f"Bearer {access_token}"}
        response = client.get("/stats", headers=headers)
        assert response.status_code == 200
        assert response.json["status"] == "success"
        assert response.json["message"] == "Stats for TradingEngine"
        assert response.json["stats"] == {"test": "test"}
