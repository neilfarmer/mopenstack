"""Integration tests for Nova (Compute Service)."""

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
    from mopenstack.models.nova import Flavor, KeyPair, Server

    db = SessionLocal()
    try:
        db.query(Token).delete()
        db.query(Server).delete()
        db.query(KeyPair).delete()
        db.query(Flavor).delete()
        db.commit()
    finally:
        db.close()

    # Ensure we have bootstrap data
    bootstrap_keystone()

    return TestClient(app)


@pytest.fixture(scope="function")
def auth_token(client):
    """Get authentication token for testing."""
    auth_data = {
        "auth": {
            "identity": {
                "methods": ["password"],
                "password": {
                    "user": {
                        "name": "admin",
                        "password": "password",
                        "domain": {"id": "default"},
                    }
                },
            },
            "scope": {"project": {"name": "admin"}},
        }
    }

    response = client.post("/v3/auth/tokens", json=auth_data)
    assert response.status_code == 200
    return response.headers["X-Subject-Token"]


class TestNovaIntegration:
    """Test Nova API endpoints integration."""

    def test_version_endpoint(self, client):
        """Test Nova version endpoint."""
        response = client.get("/v2.1/")
        assert response.status_code == 200

        data = response.json()
        assert "version" in data
        assert data["version"]["id"] == "v2.1"
        assert data["version"]["status"] == "CURRENT"

    def test_flavor_crud_operations(self, client, auth_token):
        """Test complete flavor CRUD operations."""
        headers = {"X-Auth-Token": auth_token}

        # Create flavor
        flavor_data = {
            "flavor": {
                "name": "test-flavor",
                "vcpus": 2,
                "ram": 4096,
                "disk": 20,
                "ephemeral": 0,
                "swap": 0,
                "public": True,
            }
        }

        response = client.post("/v2.1/flavors", json=flavor_data, headers=headers)
        assert response.status_code == 200

        created_flavor = response.json()["flavor"]
        flavor_id = created_flavor["id"]
        assert created_flavor["name"] == "test-flavor"
        assert created_flavor["vcpus"] == 2
        assert created_flavor["ram"] == 4096
        assert created_flavor["disk"] == 20

        # Get flavor by ID
        response = client.get(f"/v2.1/flavors/{flavor_id}", headers=headers)
        assert response.status_code == 200

        flavor = response.json()["flavor"]
        assert flavor["id"] == flavor_id
        assert flavor["name"] == "test-flavor"

        # Get flavor by name
        response = client.get("/v2.1/flavors/test-flavor", headers=headers)
        assert response.status_code == 200

        flavor = response.json()["flavor"]
        assert flavor["id"] == flavor_id
        assert flavor["name"] == "test-flavor"

        # List flavors
        response = client.get("/v2.1/flavors", headers=headers)
        assert response.status_code == 200

        flavors = response.json()["flavors"]
        assert len(flavors) >= 1
        flavor_names = [f["name"] for f in flavors]
        assert "test-flavor" in flavor_names

        # Delete flavor
        response = client.delete(f"/v2.1/flavors/{flavor_id}", headers=headers)
        assert response.status_code == 204

        # Verify deletion
        response = client.get(f"/v2.1/flavors/{flavor_id}", headers=headers)
        assert response.status_code == 404

    def test_server_crud_operations(self, client, auth_token):
        """Test complete server CRUD operations."""
        headers = {"X-Auth-Token": auth_token}

        # First create a flavor for the server
        flavor_data = {
            "flavor": {
                "name": "server-test-flavor",
                "vcpus": 1,
                "ram": 1024,
                "disk": 10,
            }
        }

        response = client.post("/v2.1/flavors", json=flavor_data, headers=headers)
        assert response.status_code == 200
        flavor_id = response.json()["flavor"]["id"]

        # Create server
        server_data = {
            "server": {
                "name": "test-server",
                "image_ref": "test-image-uuid",
                "flavor_ref": flavor_id,
                "metadata": {"test_key": "test_value"},
                "networks": [{"uuid": "test-network-uuid"}],
                "key_name": "test-key",
            }
        }

        response = client.post("/v2.1/servers", json=server_data, headers=headers)
        assert response.status_code == 200

        created_server = response.json()["server"]
        server_id = created_server["id"]
        assert created_server["name"] == "test-server"
        assert (
            created_server["status"] == "ACTIVE"
        )  # Should be active after boot simulation
        assert created_server["image_ref"] == "test-image-uuid"
        assert created_server["flavor_ref"] == flavor_id
        assert created_server["metadata"]["test_key"] == "test_value"

        # Get server by ID
        response = client.get(f"/v2.1/servers/{server_id}", headers=headers)
        assert response.status_code == 200

        server = response.json()["server"]
        assert server["id"] == server_id
        assert server["name"] == "test-server"

        # Get server by name
        response = client.get("/v2.1/servers/test-server", headers=headers)
        assert response.status_code == 200

        server = response.json()["server"]
        assert server["id"] == server_id
        assert server["name"] == "test-server"

        # List servers
        response = client.get("/v2.1/servers", headers=headers)
        assert response.status_code == 200

        servers = response.json()["servers"]
        assert len(servers) >= 1
        server_names = [s["name"] for s in servers]
        assert "test-server" in server_names

        # List servers with detail
        response = client.get("/v2.1/servers/detail", headers=headers)
        assert response.status_code == 200

        servers = response.json()["servers"]
        assert len(servers) >= 1
        test_server = next(s for s in servers if s["name"] == "test-server")
        assert test_server["status"] == "ACTIVE"

        # Update server
        update_data = {"server": {"name": "updated-test-server"}}

        response = client.put(
            f"/v2.1/servers/{server_id}", json=update_data, headers=headers
        )
        assert response.status_code == 200

        updated_server = response.json()["server"]
        assert updated_server["name"] == "updated-test-server"

        # Delete server
        response = client.delete(f"/v2.1/servers/{server_id}", headers=headers)
        assert response.status_code == 204

        # Verify deletion
        response = client.get(f"/v2.1/servers/{server_id}", headers=headers)
        assert response.status_code == 404

        # Clean up flavor
        response = client.delete(f"/v2.1/flavors/{flavor_id}", headers=headers)
        assert response.status_code == 204

    def test_server_actions(self, client, auth_token):
        """Test server action operations (reboot, start, stop)."""
        headers = {"X-Auth-Token": auth_token}

        # Create flavor and server for testing
        flavor_data = {
            "flavor": {"name": "action-test-flavor", "vcpus": 1, "ram": 512, "disk": 5}
        }

        response = client.post("/v2.1/flavors", json=flavor_data, headers=headers)
        flavor_id = response.json()["flavor"]["id"]

        server_data = {
            "server": {
                "name": "action-test-server",
                "image_ref": "test-image-uuid",
                "flavor_ref": flavor_id,
            }
        }

        response = client.post("/v2.1/servers", json=server_data, headers=headers)
        server_id = response.json()["server"]["id"]

        # Test reboot action
        reboot_data = {"reboot": {"type": "SOFT"}}

        response = client.post(
            f"/v2.1/servers/{server_id}/action", json=reboot_data, headers=headers
        )
        assert response.status_code == 202

        # Test stop action
        stop_data = {"os-stop": {}}

        response = client.post(
            f"/v2.1/servers/{server_id}/action", json=stop_data, headers=headers
        )
        assert response.status_code == 202

        # Verify server is stopped
        response = client.get(f"/v2.1/servers/{server_id}", headers=headers)
        server = response.json()["server"]
        assert server["status"] == "SHUTOFF"

        # Test start action
        start_data = {"os-start": {}}

        response = client.post(
            f"/v2.1/servers/{server_id}/action", json=start_data, headers=headers
        )
        assert response.status_code == 202

        # Verify server is active
        response = client.get(f"/v2.1/servers/{server_id}", headers=headers)
        server = response.json()["server"]
        assert server["status"] == "ACTIVE"

        # Clean up
        response = client.delete(f"/v2.1/servers/{server_id}", headers=headers)
        assert response.status_code == 204

        response = client.delete(f"/v2.1/flavors/{flavor_id}", headers=headers)
        assert response.status_code == 204

    def test_keypair_crud_operations(self, client, auth_token):
        """Test complete key pair CRUD operations."""
        headers = {"X-Auth-Token": auth_token}

        # Create key pair
        keypair_data = {
            "keypair": {
                "name": "test-keypair",
                "public_key": "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQ... test@example.com",
                "type": "ssh",
            }
        }

        response = client.post("/v2.1/os-keypairs", json=keypair_data, headers=headers)
        assert response.status_code == 200

        created_keypair = response.json()["keypair"]
        assert created_keypair["name"] == "test-keypair"
        assert created_keypair["type"] == "ssh"
        assert "fingerprint" in created_keypair

        # Get key pair
        response = client.get("/v2.1/os-keypairs/test-keypair", headers=headers)
        assert response.status_code == 200

        keypair = response.json()["keypair"]
        assert keypair["name"] == "test-keypair"

        # List key pairs
        response = client.get("/v2.1/os-keypairs", headers=headers)
        assert response.status_code == 200

        keypairs = response.json()["keypairs"]
        assert len(keypairs) >= 1
        keypair_names = [kp["keypair"]["name"] for kp in keypairs]
        assert "test-keypair" in keypair_names

        # Delete key pair
        response = client.delete("/v2.1/os-keypairs/test-keypair", headers=headers)
        assert response.status_code == 202

        # Verify deletion
        response = client.get("/v2.1/os-keypairs/test-keypair", headers=headers)
        assert response.status_code == 404

    def test_flavor_conflict_handling(self, client, auth_token):
        """Test flavor creation conflict handling."""
        headers = {"X-Auth-Token": auth_token}

        # Create first flavor
        flavor_data = {
            "flavor": {
                "name": "conflict-test-flavor",
                "vcpus": 1,
                "ram": 1024,
                "disk": 10,
            }
        }

        response = client.post("/v2.1/flavors", json=flavor_data, headers=headers)
        assert response.status_code == 200
        flavor_id = response.json()["flavor"]["id"]

        # Try to create another flavor with the same name
        response = client.post("/v2.1/flavors", json=flavor_data, headers=headers)
        assert response.status_code == 409

        # Clean up
        response = client.delete(f"/v2.1/flavors/{flavor_id}", headers=headers)
        assert response.status_code == 204

    def test_flavor_in_use_deletion(self, client, auth_token):
        """Test that flavors in use by servers cannot be deleted."""
        headers = {"X-Auth-Token": auth_token}

        # Create flavor
        flavor_data = {
            "flavor": {"name": "in-use-flavor", "vcpus": 1, "ram": 1024, "disk": 10}
        }

        response = client.post("/v2.1/flavors", json=flavor_data, headers=headers)
        flavor_id = response.json()["flavor"]["id"]

        # Create server using this flavor
        server_data = {
            "server": {
                "name": "flavor-user-server",
                "image_ref": "test-image",
                "flavor_ref": flavor_id,
            }
        }

        response = client.post("/v2.1/servers", json=server_data, headers=headers)
        server_id = response.json()["server"]["id"]

        # Try to delete flavor while in use
        response = client.delete(f"/v2.1/flavors/{flavor_id}", headers=headers)
        assert response.status_code == 409

        # Clean up server first, then flavor
        response = client.delete(f"/v2.1/servers/{server_id}", headers=headers)
        assert response.status_code == 204

        response = client.delete(f"/v2.1/flavors/{flavor_id}", headers=headers)
        assert response.status_code == 204

    def test_authentication_required(self, client):
        """Test that Nova endpoints require authentication."""
        # Try to access endpoints without authentication
        endpoints_to_test = [
            ("/v2.1/flavors", "GET"),
            ("/v2.1/servers", "GET"),
            ("/v2.1/os-keypairs", "GET"),
        ]

        for endpoint, method in endpoints_to_test:
            if method == "GET":
                response = client.get(endpoint)
            assert (
                response.status_code == 422
            )  # FastAPI validation error for missing header
