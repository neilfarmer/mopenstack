"""Integration tests for error handling and edge cases."""

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


class TestAuthenticationErrors:
    """Test authentication error handling."""

    def test_invalid_credentials(self, client):
        """Test authentication with invalid credentials."""
        auth_data = {
            "auth": {
                "identity": {
                    "methods": ["password"],
                    "password": {
                        "user": {
                            "name": "admin",
                            "password": "wrong-password",
                            "domain": {"id": "default"},
                        }
                    },
                },
                "scope": {"project": {"name": "admin"}},
            }
        }

        response = client.post("/v3/auth/tokens", json=auth_data)
        assert response.status_code == 401
        assert "Invalid authentication credentials" in response.json()["detail"]

    def test_nonexistent_user(self, client):
        """Test authentication with non-existent user."""
        auth_data = {
            "auth": {
                "identity": {
                    "methods": ["password"],
                    "password": {
                        "user": {
                            "name": "nonexistent",
                            "password": "password",
                            "domain": {"id": "default"},
                        }
                    },
                },
                "scope": {"project": {"name": "admin"}},
            }
        }

        response = client.post("/v3/auth/tokens", json=auth_data)
        assert response.status_code == 401

    def test_nonexistent_project_scope(self, client):
        """Test authentication with non-existent project scope."""
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
                "scope": {"project": {"name": "nonexistent-project"}},
            }
        }

        response = client.post("/v3/auth/tokens", json=auth_data)
        assert response.status_code == 404
        assert "Project not found" in response.json()["detail"]

    def test_malformed_auth_request(self, client):
        """Test malformed authentication request."""
        invalid_requests = [
            {},  # Empty request
            {"auth": {}},  # Empty auth
            {"auth": {"identity": {}}},  # Missing methods
            {"auth": {"identity": {"methods": []}}},  # Empty methods
        ]

        for invalid_data in invalid_requests:
            response = client.post("/v3/auth/tokens", json=invalid_data)
            assert response.status_code in [400, 422]  # Bad request or validation error

    def test_missing_auth_token(self, client):
        """Test accessing protected endpoints without auth token."""
        protected_endpoints = [
            ("/v2.1/flavors", "GET"),
            ("/v2.1/servers", "GET"),
            ("/v2.1/os-keypairs", "GET"),
            ("/v3/projects", "GET"),
            ("/v3/users", "GET"),
        ]

        for endpoint, method in protected_endpoints:
            if method == "GET":
                response = client.get(endpoint)
            else:
                response = getattr(client, method.lower())(endpoint)
            
            # Should fail due to missing authentication
            assert response.status_code in [401, 422], f"Endpoint {endpoint} returned {response.status_code} instead of 401/422"

    def test_invalid_auth_token(self, client):
        """Test accessing endpoints with invalid auth token."""
        headers = {"X-Auth-Token": "invalid-token-123"}
        
        response = client.get("/v2.1/flavors", headers=headers)
        assert response.status_code == 401

    def test_expired_token_handling(self, client):
        """Test handling of expired tokens."""
        # This would require manipulating token expiry time
        # For now, test with malformed JWT token
        headers = {"X-Auth-Token": "malformed.jwt.token"}
        
        response = client.get("/v2.1/flavors", headers=headers)
        assert response.status_code == 401


class TestResourceNotFoundErrors:
    """Test resource not found error handling."""

    def test_flavor_not_found(self, client, auth_token):
        """Test flavor not found errors."""
        headers = {"X-Auth-Token": auth_token}
        
        # Get non-existent flavor by ID
        response = client.get("/v2.1/flavors/nonexistent-id", headers=headers)
        assert response.status_code == 404
        assert "Flavor not found" in response.json()["detail"]

        # Get non-existent flavor by name
        response = client.get("/v2.1/flavors/nonexistent-flavor", headers=headers)
        assert response.status_code == 404

        # Delete non-existent flavor
        response = client.delete("/v2.1/flavors/nonexistent-id", headers=headers)
        assert response.status_code == 404

    def test_server_not_found(self, client, auth_token):
        """Test server not found errors."""
        headers = {"X-Auth-Token": auth_token}
        
        # Get non-existent server by ID
        response = client.get("/v2.1/servers/nonexistent-id", headers=headers)
        assert response.status_code == 404
        assert "Server not found" in response.json()["detail"]

        # Update non-existent server
        update_data = {"server": {"name": "new-name"}}
        response = client.put("/v2.1/servers/nonexistent-id", json=update_data, headers=headers)
        assert response.status_code == 404

        # Delete non-existent server
        response = client.delete("/v2.1/servers/nonexistent-id", headers=headers)
        assert response.status_code == 404

        # Action on non-existent server
        action_data = {"reboot": {"type": "SOFT"}}
        response = client.post("/v2.1/servers/nonexistent-id/action", json=action_data, headers=headers)
        assert response.status_code == 404

    def test_keypair_not_found(self, client, auth_token):
        """Test key pair not found errors."""
        headers = {"X-Auth-Token": auth_token}
        
        # Get non-existent key pair
        response = client.get("/v2.1/os-keypairs/nonexistent-key", headers=headers)
        assert response.status_code == 404
        assert "Key pair not found" in response.json()["detail"]

        # Delete non-existent key pair
        response = client.delete("/v2.1/os-keypairs/nonexistent-key", headers=headers)
        assert response.status_code == 404

    def test_project_not_found(self, client, auth_token):
        """Test project not found errors."""
        headers = {"X-Auth-Token": auth_token}
        
        # Get non-existent project
        response = client.get("/v3/projects/nonexistent-id", headers=headers)
        assert response.status_code == 404
        assert "Project not found" in response.json()["detail"]

        # Update non-existent project
        update_data = {"project": {"name": "new-name"}}
        response = client.patch("/v3/projects/nonexistent-id", json=update_data, headers=headers)
        assert response.status_code == 404

        # Delete non-existent project
        response = client.delete("/v3/projects/nonexistent-id", headers=headers)
        assert response.status_code == 404


class TestValidationErrors:
    """Test request validation errors."""

    def test_invalid_flavor_creation(self, client, auth_token):
        """Test flavor creation with invalid data."""
        headers = {"X-Auth-Token": auth_token}
        
        invalid_requests = [
            # Missing required fields
            {"flavor": {"name": "test"}},  # Missing vcpus, ram, disk
            {"flavor": {"vcpus": 1, "ram": 1024}},  # Missing name, disk
            # Invalid data types
            {"flavor": {"name": "test", "vcpus": "invalid", "ram": 1024, "disk": 10}},
            {"flavor": {"name": "test", "vcpus": 1, "ram": "invalid", "disk": 10}},
            # Negative values
            {"flavor": {"name": "test", "vcpus": -1, "ram": 1024, "disk": 10}},
        ]

        for invalid_data in invalid_requests:
            response = client.post("/v2.1/flavors", json=invalid_data, headers=headers)
            assert response.status_code == 422  # Validation error

    def test_invalid_server_creation(self, client, auth_token):
        """Test server creation with invalid data."""
        headers = {"X-Auth-Token": auth_token}
        
        invalid_requests = [
            # Missing required fields
            {"server": {"name": "test"}},  # Missing image_ref, flavor_ref
            {"server": {"name": "test", "imageRef": "image-123"}},  # Missing flavor_ref
            # Empty required fields
            {"server": {"name": "", "imageRef": "image-123", "flavorRef": "flavor-456"}},
            # Invalid data types
            {"server": {"name": 123, "imageRef": "image-123", "flavorRef": "flavor-456"}},
        ]

        for invalid_data in invalid_requests:
            response = client.post("/v2.1/servers", json=invalid_data, headers=headers)
            assert response.status_code == 422  # Validation error

    def test_invalid_keypair_creation(self, client, auth_token):
        """Test key pair creation with invalid data."""
        headers = {"X-Auth-Token": auth_token}
        
        invalid_requests = [
            # Missing required name
            {"keypair": {"type": "ssh"}},
            # Empty name
            {"keypair": {"name": "", "type": "ssh"}},
            # Invalid type
            {"keypair": {"name": "test", "type": "invalid"}},
        ]

        for invalid_data in invalid_requests:
            response = client.post("/v2.1/os-keypairs", json=invalid_data, headers=headers)
            assert response.status_code == 422  # Validation error

    def test_invalid_project_creation(self, client, auth_token):
        """Test project creation with invalid data."""
        headers = {"X-Auth-Token": auth_token}
        
        invalid_requests = [
            # Missing required name
            {"project": {"description": "test"}},
            # Empty name
            {"project": {"name": "", "description": "test"}},
            # Invalid enabled field
            {"project": {"name": "test", "enabled": "invalid"}},
        ]

        for invalid_data in invalid_requests:
            response = client.post("/v3/projects", json=invalid_data, headers=headers)
            assert response.status_code == 422  # Validation error


class TestConflictErrors:
    """Test resource conflict errors."""

    def test_duplicate_flavor_name(self, client, auth_token):
        """Test creating flavors with duplicate names."""
        headers = {"X-Auth-Token": auth_token}
        
        # Create first flavor
        flavor_data = {
            "flavor": {
                "name": "duplicate-test",
                "vcpus": 1,
                "ram": 1024,
                "disk": 10,
            }
        }
        
        response = client.post("/v2.1/flavors", json=flavor_data, headers=headers)
        assert response.status_code == 200
        flavor_id = response.json()["flavor"]["id"]
        
        # Try to create another with same name
        response = client.post("/v2.1/flavors", json=flavor_data, headers=headers)
        assert response.status_code == 409
        assert "already exists" in response.json()["detail"].lower()
        
        # Clean up
        client.delete(f"/v2.1/flavors/{flavor_id}", headers=headers)

    def test_duplicate_keypair_name(self, client, auth_token):
        """Test creating key pairs with duplicate names."""
        headers = {"X-Auth-Token": auth_token}
        
        # Create first key pair
        kp_data = {
            "keypair": {
                "name": "duplicate-key",
                "type": "ssh",
                "public_key": "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQ..."
            }
        }
        
        response = client.post("/v2.1/os-keypairs", json=kp_data, headers=headers)
        assert response.status_code == 200
        
        # Try to create another with same name
        response = client.post("/v2.1/os-keypairs", json=kp_data, headers=headers)
        assert response.status_code == 409
        
        # Clean up
        client.delete("/v2.1/os-keypairs/duplicate-key", headers=headers)


class TestBusinessLogicErrors:
    """Test business logic error handling."""

    def test_server_creation_nonexistent_flavor(self, client, auth_token):
        """Test server creation with non-existent flavor."""
        headers = {"X-Auth-Token": auth_token}
        
        server_data = {
            "server": {
                "name": "test-server",
                "imageRef": "image-123",
                "flavorRef": "nonexistent-flavor-id",
            }
        }
        
        response = client.post("/v2.1/servers", json=server_data, headers=headers)
        assert response.status_code == 400
        assert "not found" in response.json()["detail"].lower()

    def test_server_actions_invalid_action(self, client, auth_token):
        """Test server actions with invalid action types."""
        headers = {"X-Auth-Token": auth_token}
        
        # First create a server
        flavor_data = {"flavor": {"name": "action-test", "vcpus": 1, "ram": 512, "disk": 5}}
        flavor_response = client.post("/v2.1/flavors", json=flavor_data, headers=headers)
        flavor_id = flavor_response.json()["flavor"]["id"]
        
        server_data = {
            "server": {
                "name": "action-test-server",
                "imageRef": "image-123",
                "flavorRef": flavor_id,
            }
        }
        server_response = client.post("/v2.1/servers", json=server_data, headers=headers)
        server_id = server_response.json()["server"]["id"]
        
        # Try invalid action
        invalid_action = {"invalid-action": {}}
        response = client.post(f"/v2.1/servers/{server_id}/action", json=invalid_action, headers=headers)
        assert response.status_code == 400
        assert "Unsupported server action" in response.json()["detail"]
        
        # Clean up
        client.delete(f"/v2.1/servers/{server_id}", headers=headers)
        client.delete(f"/v2.1/flavors/{flavor_id}", headers=headers)


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_extremely_long_names(self, client, auth_token):
        """Test handling of extremely long resource names."""
        headers = {"X-Auth-Token": auth_token}
        
        # Very long flavor name (over typical DB limits)
        long_name = "x" * 1000
        flavor_data = {
            "flavor": {
                "name": long_name,
                "vcpus": 1,
                "ram": 1024,
                "disk": 10,
            }
        }
        
        response = client.post("/v2.1/flavors", json=flavor_data, headers=headers)
        # Should handle gracefully (either accept with truncation or reject)
        assert response.status_code in [200, 422, 400]

    def test_special_characters_in_names(self, client, auth_token):
        """Test handling of special characters in resource names."""
        headers = {"X-Auth-Token": auth_token}
        
        special_names = [
            "test-with-unicode-ñáéí",
            "test with spaces",
            "test@with#special$chars",
            "test.with.dots",
            "test_with_underscores",
        ]
        
        for name in special_names:
            flavor_data = {
                "flavor": {
                    "name": name,
                    "vcpus": 1,
                    "ram": 1024,
                    "disk": 10,
                }
            }
            
            response = client.post("/v2.1/flavors", json=flavor_data, headers=headers)
            # Should handle gracefully
            if response.status_code == 200:
                # Clean up if created
                flavor_id = response.json()["flavor"]["id"]
                client.delete(f"/v2.1/flavors/{flavor_id}", headers=headers)

    def test_zero_and_negative_resource_values(self, client, auth_token):
        """Test handling of zero and negative values in resources."""
        headers = {"X-Auth-Token": auth_token}
        
        edge_case_flavors = [
            # Zero values
            {"name": "zero-vcpu", "vcpus": 0, "ram": 1024, "disk": 10},
            {"name": "zero-ram", "vcpus": 1, "ram": 0, "disk": 10},
            {"name": "zero-disk", "vcpus": 1, "ram": 1024, "disk": 0},
            # Very large values
            {"name": "huge-ram", "vcpus": 1, "ram": 999999999, "disk": 10},
        ]
        
        for flavor_spec in edge_case_flavors:
            flavor_data = {"flavor": flavor_spec}
            response = client.post("/v2.1/flavors", json=flavor_data, headers=headers)
            # Should handle validation appropriately
            assert response.status_code in [200, 400, 422]