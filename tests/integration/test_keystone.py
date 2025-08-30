"""Integration tests for Keystone authentication."""

import pytest
from fastapi.testclient import TestClient

from mopenstack.bootstrap import bootstrap_keystone
from mopenstack.main import app


@pytest.fixture(scope="function")
def client():
    """Test client fixture."""
    # Clean up any existing tokens from previous tests
    from mopenstack.common.database import SessionLocal
    from mopenstack.models.keystone import Token

    db = SessionLocal()
    try:
        db.query(Token).delete()
        db.commit()
    finally:
        db.close()

    # Ensure we have bootstrap data
    bootstrap_keystone()

    return TestClient(app)


def test_version_endpoint(client):
    """Test Keystone version endpoint."""
    response = client.get("/v3/")
    assert response.status_code == 200
    data = response.json()
    assert "version" in data
    assert data["version"]["status"] == "stable"


def test_authentication_flow(client):
    """Test complete authentication flow."""
    # Test authentication with admin credentials
    auth_data = {
        "auth": {
            "identity": {
                "password": {
                    "user": {
                        "name": "admin",
                        "password": "password",
                        "domain": {"id": "default"},
                    }
                }
            },
            "scope": {"project": {"name": "admin"}},
        }
    }

    response = client.post("/v3/auth/tokens", json=auth_data)
    assert response.status_code == 200

    data = response.json()
    assert "token" in data
    assert "expires_at" in data["token"]
    assert data["token"]["user"]["name"] == "admin"
    assert data["token"]["project"]["name"] == "admin"

    # Extract the token for further tests
    token = response.headers.get("x-subject-token")
    assert token is not None


def test_token_validation(client):
    """Test token validation."""
    # First authenticate to get a token
    auth_data = {
        "auth": {
            "identity": {
                "password": {
                    "user": {
                        "name": "admin",
                        "password": "password",
                        "domain": {"id": "default"},
                    }
                }
            },
            "scope": {"project": {"name": "admin"}},
        }
    }

    auth_response = client.post("/v3/auth/tokens", json=auth_data)
    assert auth_response.status_code == 200
    token = auth_response.headers.get("x-subject-token")
    assert token is not None

    # Validate the token
    response = client.get(
        "/v3/auth/tokens", headers={"X-Auth-Token": token, "X-Subject-Token": token}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["token"]["user"]["name"] == "admin"


def test_health_check(client):
    """Test health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_service_catalog(client):
    """Test service catalog in auth response."""
    auth_data = {
        "auth": {
            "identity": {
                "password": {
                    "user": {
                        "name": "admin",
                        "password": "password",
                        "domain": {"id": "default"},
                    }
                }
            },
            "scope": {"project": {"name": "admin"}},
        }
    }

    response = client.post("/v3/auth/tokens", json=auth_data)
    assert response.status_code == 200

    data = response.json()
    assert "catalog" in data["token"]
    catalog = data["token"]["catalog"]
    assert len(catalog) >= 3  # At least identity, compute, network

    # Verify service types exist
    service_types = [service["type"] for service in catalog]
    assert "identity" in service_types
    assert "compute" in service_types
    assert "network" in service_types
