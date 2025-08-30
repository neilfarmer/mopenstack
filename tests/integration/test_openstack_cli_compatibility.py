"""Integration tests for OpenStack CLI compatibility."""

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


class TestOpenStackCLIFlow:
    """Test complete OpenStack CLI workflow compatibility."""

    def test_complete_server_lifecycle(self, client, auth_token):
        """Test complete server lifecycle as used by OpenStack CLI."""
        headers = {"X-Auth-Token": auth_token}

        # 1. Create a flavor (like 'openstack flavor create')
        flavor_data = {
            "flavor": {
                "name": "m1.small",
                "vcpus": 1,
                "ram": 2048,
                "disk": 20,
                "ephemeral": 0,
                "swap": 0,
                "public": True,
            }
        }
        response = client.post("/v2.1/flavors", json=flavor_data, headers=headers)
        assert response.status_code == 200
        flavor = response.json()["flavor"]
        flavor_id = flavor["id"]

        # 2. List flavors with detail (like 'openstack flavor list')
        response = client.get("/v2.1/flavors/detail", headers=headers)
        assert response.status_code == 200
        flavors = response.json()["flavors"]
        flavor_names = [f["name"] for f in flavors]
        assert "m1.small" in flavor_names

        # 3. Create server using actual OpenStack CLI format
        server_data = {
            "server": {
                "name": "test-instance",
                "imageRef": "3394d42a-9583-4c79-9a1b-7bb94ae7dc04",  # Ubuntu image UUID
                "flavorRef": flavor_id,
                "min_count": 1,
                "max_count": 1,
            }
        }
        response = client.post("/v2.1/servers", json=server_data, headers=headers)
        assert response.status_code == 200
        server = response.json()["server"]
        server_id = server["id"]

        # Verify server has expected OpenStack CLI fields
        assert "OS-EXT-STS:power_state" in server or "power_state" in server
        assert "OS-EXT-STS:vm_state" in server or "vm_state" in server
        assert "flavor" in server  # Should be object with id
        assert "image" in server   # Should be object with id
        assert server["tenant_id"] == server["project_id"]  # CLI compatibility

        # 4. List servers (like 'openstack server list')
        response = client.get("/v2.1/servers", headers=headers)
        assert response.status_code == 200
        servers = response.json()["servers"]
        server_names = [s["name"] for s in servers]
        assert "test-instance" in server_names

        # 5. List servers with detail (like 'openstack server list --long')
        response = client.get("/v2.1/servers/detail", headers=headers)
        assert response.status_code == 200
        detailed_servers = response.json()["servers"]
        test_server = next(s for s in detailed_servers if s["name"] == "test-instance")
        
        # Verify all required fields are present for CLI display
        required_fields = [
            "id", "name", "status", "created", "updated",
            "flavor", "image", "user_id", "project_id"
        ]
        for field in required_fields:
            assert field in test_server, f"Missing required field: {field}"

        # 6. Get server details (like 'openstack server show')
        response = client.get(f"/v2.1/servers/{server_id}", headers=headers)
        assert response.status_code == 200
        server_detail = response.json()["server"]
        
        # Verify extensive server details for CLI compatibility
        assert server_detail["name"] == "test-instance"
        assert server_detail["status"] == "ACTIVE"
        assert isinstance(server_detail["flavor"], dict)
        assert isinstance(server_detail["image"], dict)

        # 7. Perform server actions (like 'openstack server reboot')
        reboot_data = {"reboot": {"type": "SOFT"}}
        response = client.post(f"/v2.1/servers/{server_id}/action", json=reboot_data, headers=headers)
        assert response.status_code == 202

        # 8. Stop server (like 'openstack server stop')
        stop_data = {"os-stop": {}}
        response = client.post(f"/v2.1/servers/{server_id}/action", json=stop_data, headers=headers)
        assert response.status_code == 202

        # 9. Start server (like 'openstack server start')
        start_data = {"os-start": {}}
        response = client.post(f"/v2.1/servers/{server_id}/action", json=start_data, headers=headers)
        assert response.status_code == 202

        # 10. Delete server (like 'openstack server delete')
        response = client.delete(f"/v2.1/servers/{server_id}", headers=headers)
        assert response.status_code == 204

        # 11. Delete flavor (like 'openstack flavor delete')
        response = client.delete(f"/v2.1/flavors/{flavor_id}", headers=headers)
        assert response.status_code == 204

    def test_keypair_cli_workflow(self, client, auth_token):
        """Test key pair workflow as used by OpenStack CLI."""
        headers = {"X-Auth-Token": auth_token}

        # 1. Create key pair (like 'openstack keypair create')
        keypair_data = {
            "keypair": {
                "name": "test-key",
                "public_key": "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQC... test@example.com",
                "type": "ssh",
            }
        }
        response = client.post("/v2.1/os-keypairs", json=keypair_data, headers=headers)
        assert response.status_code == 200
        keypair = response.json()["keypair"]
        assert keypair["name"] == "test-key"
        assert "fingerprint" in keypair

        # 2. List key pairs (like 'openstack keypair list')
        response = client.get("/v2.1/os-keypairs", headers=headers)
        assert response.status_code == 200
        keypairs = response.json()["keypairs"]
        keypair_names = [kp["keypair"]["name"] for kp in keypairs]
        assert "test-key" in keypair_names

        # 3. Show key pair (like 'openstack keypair show')
        response = client.get("/v2.1/os-keypairs/test-key", headers=headers)
        assert response.status_code == 200
        keypair_detail = response.json()["keypair"]
        assert keypair_detail["name"] == "test-key"
        assert keypair_detail["type"] == "ssh"

        # 4. Delete key pair (like 'openstack keypair delete')
        response = client.delete("/v2.1/os-keypairs/test-key", headers=headers)
        assert response.status_code == 202

    def test_project_cli_workflow(self, client, auth_token):
        """Test project workflow as used by OpenStack CLI."""
        headers = {"X-Auth-Token": auth_token}

        # 1. Create project (like 'openstack project create')
        project_data = {
            "project": {
                "name": "test-project",
                "description": "Test project for CLI compatibility",
                "enabled": True,
            }
        }
        response = client.post("/v3/projects", json=project_data, headers=headers)
        assert response.status_code == 200
        project = response.json()["project"]
        project_id = project["id"]
        assert project["name"] == "test-project"
        assert "links" in project  # CLI expects links

        # 2. List projects (like 'openstack project list')
        response = client.get("/v3/projects", headers=headers)
        assert response.status_code == 200
        projects = response.json()["projects"]
        project_names = [p["name"] for p in projects]
        assert "test-project" in project_names

        # 3. Show project (like 'openstack project show')
        response = client.get(f"/v3/projects/{project_id}", headers=headers)
        assert response.status_code == 200
        project_detail = response.json()["project"]
        assert project_detail["name"] == "test-project"
        assert project_detail["description"] == "Test project for CLI compatibility"

        # 4. Update project (like 'openstack project set')
        update_data = {
            "project": {
                "name": "updated-test-project",
                "description": "Updated description",
            }
        }
        response = client.patch(f"/v3/projects/{project_id}", json=update_data, headers=headers)
        assert response.status_code == 200
        updated_project = response.json()["project"]
        assert updated_project["name"] == "updated-test-project"
        assert "links" in updated_project  # CLI expects links

        # 5. Delete project (like 'openstack project delete')
        response = client.delete(f"/v3/projects/{project_id}", headers=headers)
        assert response.status_code == 204


class TestAPIResponseFormat:
    """Test API response formats match OpenStack expectations."""

    def test_server_response_format(self, client, auth_token):
        """Test server responses match expected OpenStack format."""
        headers = {"X-Auth-Token": auth_token}

        # Create minimal flavor for testing
        flavor_data = {"flavor": {"name": "format-test", "vcpus": 1, "ram": 512, "disk": 5}}
        flavor_response = client.post("/v2.1/flavors", json=flavor_data, headers=headers)
        flavor_id = flavor_response.json()["flavor"]["id"]

        # Create server with OpenStack CLI format
        server_data = {
            "server": {
                "name": "format-test-server",
                "imageRef": "3394d42a-9583-4c79-9a1b-7bb94ae7dc04",
                "flavorRef": flavor_id,
            }
        }
        response = client.post("/v2.1/servers", json=server_data, headers=headers)
        assert response.status_code == 200

        server = response.json()["server"]
        server_id = server["id"]

        # Test server creation response format
        expected_creation_fields = [
            "id", "name", "status", "created", "updated",
            "image_ref", "flavor_ref", "user_id", "project_id",
            "tenant_id",  # Alias for project_id
            "flavor", "image",  # Objects with id field
        ]
        for field in expected_creation_fields:
            assert field in server, f"Missing field in server creation response: {field}"

        # Test server list response format
        response = client.get("/v2.1/servers", headers=headers)
        servers = response.json()["servers"]
        list_server = next(s for s in servers if s["id"] == server_id)
        
        # List response should have same fields
        for field in expected_creation_fields:
            assert field in list_server, f"Missing field in server list response: {field}"

        # Test server detail response format
        response = client.get(f"/v2.1/servers/{server_id}", headers=headers)
        detail_server = response.json()["server"]
        
        # Detail response should have additional fields
        additional_detail_fields = [
            "vm_state", "power_state", "task_state",
            "launched_at", "terminated_at", "config_drive"
        ]
        for field in additional_detail_fields:
            assert field in detail_server, f"Missing field in server detail response: {field}"

        # Clean up
        client.delete(f"/v2.1/servers/{server_id}", headers=headers)
        client.delete(f"/v2.1/flavors/{flavor_id}", headers=headers)

    def test_flavor_response_format(self, client, auth_token):
        """Test flavor responses match expected OpenStack format."""
        headers = {"X-Auth-Token": auth_token}

        # Create flavor
        flavor_data = {
            "flavor": {
                "name": "format-test-flavor",
                "vcpus": 2,
                "ram": 4096,
                "disk": 20,
                "ephemeral": 10,
                "swap": 1024,
                "public": True,
            }
        }
        response = client.post("/v2.1/flavors", json=flavor_data, headers=headers)
        assert response.status_code == 200

        flavor = response.json()["flavor"]
        flavor_id = flavor["id"]

        # Test flavor creation response format
        expected_fields = [
            "id", "name", "vcpus", "ram", "disk",
            "ephemeral", "swap", "public", "disabled",
            "created_at", "updated_at"
        ]
        for field in expected_fields:
            assert field in flavor, f"Missing field in flavor creation response: {field}"

        # Test flavor list response format
        response = client.get("/v2.1/flavors", headers=headers)
        flavors = response.json()["flavors"]
        list_flavor = next(f for f in flavors if f["id"] == flavor_id)
        
        for field in expected_fields:
            assert field in list_flavor, f"Missing field in flavor list response: {field}"

        # Test flavor detail list response format
        response = client.get("/v2.1/flavors/detail", headers=headers)
        detailed_flavors = response.json()["flavors"]
        detail_flavor = next(f for f in detailed_flavors if f["id"] == flavor_id)
        
        for field in expected_fields:
            assert field in detail_flavor, f"Missing field in flavor detail response: {field}"

        # Clean up
        client.delete(f"/v2.1/flavors/{flavor_id}", headers=headers)

    def test_authentication_response_format(self, client):
        """Test authentication response matches OpenStack format."""
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

        # Check response headers
        assert "X-Subject-Token" in response.headers
        token = response.headers["X-Subject-Token"]
        assert len(token) > 0

        # Check response body format
        data = response.json()
        assert "token" in data
        token_data = data["token"]

        expected_token_fields = [
            "expires_at", "issued_at", "methods", "user", "project", "catalog"
        ]
        for field in expected_token_fields:
            assert field in token_data, f"Missing field in token response: {field}"

        # Check user format
        user = token_data["user"]
        expected_user_fields = ["id", "name", "domain"]
        for field in expected_user_fields:
            assert field in user, f"Missing field in token user: {field}"

        # Check project format
        project = token_data["project"]
        expected_project_fields = ["id", "name", "domain"]
        for field in expected_project_fields:
            assert field in project, f"Missing field in token project: {field}"

        # Check catalog format
        catalog = token_data["catalog"]
        assert isinstance(catalog, list)
        assert len(catalog) >= 3  # Should have identity, compute, network services

        for service in catalog:
            expected_service_fields = ["type", "name", "endpoints"]
            for field in expected_service_fields:
                assert field in service, f"Missing field in catalog service: {field}"

            # Check endpoints format
            endpoints = service["endpoints"]
            assert isinstance(endpoints, list)
            assert len(endpoints) >= 1

            for endpoint in endpoints:
                expected_endpoint_fields = ["id", "interface", "url"]
                for field in expected_endpoint_fields:
                    assert field in endpoint, f"Missing field in service endpoint: {field}"


class TestServiceDiscovery:
    """Test service discovery through service catalog."""

    def test_service_catalog_completeness(self, client):
        """Test service catalog contains all expected services."""
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

        catalog = response.json()["token"]["catalog"]
        service_types = [service["type"] for service in catalog]

        # Essential services that OpenStack CLI expects
        expected_services = ["identity", "compute", "network", "image"]
        for service_type in expected_services:
            assert service_type in service_types, f"Missing service: {service_type}"

        # Verify service names match OpenStack conventions
        service_names = {service["type"]: service["name"] for service in catalog}
        expected_names = {
            "identity": "keystone",
            "compute": "nova", 
            "network": "neutron",
            "image": "glance",
        }
        
        for service_type, expected_name in expected_names.items():
            if service_type in service_names:
                assert service_names[service_type] == expected_name

    def test_endpoint_urls_correct(self, client):
        """Test service catalog endpoints have correct URLs."""
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
        catalog = response.json()["token"]["catalog"]

        # Verify endpoint URLs are accessible
        for service in catalog:
            for endpoint in service["endpoints"]:
                url = endpoint["url"]
                assert url.startswith("http://"), f"Invalid endpoint URL: {url}"
                
                # URLs should match expected patterns
                if service["type"] == "identity":
                    assert "/v3" in url
                elif service["type"] == "compute":
                    assert "/v2.1" in url
                elif service["type"] == "network":
                    assert "/v2.0" in url
                elif service["type"] == "image":
                    assert "/v2" in url