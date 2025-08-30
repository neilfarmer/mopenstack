"""Integration tests for Glance mock service."""

import pytest
from fastapi.testclient import TestClient

from mopenstack.main import app


@pytest.fixture(scope="function") 
def client():
    """Test client fixture."""
    return TestClient(app)


class TestGlanceMockService:
    """Test Glance image service mock endpoints."""

    def test_list_images(self, client):
        """Test listing all images."""
        response = client.get("/v2/images")
        assert response.status_code == 200
        
        data = response.json()
        assert "images" in data
        images = data["images"]
        assert len(images) >= 3  # We have 3 mock images
        
        # Check that all images have required fields
        for image in images:
            assert "id" in image
            assert "name" in image
            assert "status" in image
            assert image["status"] == "active"
            assert "visibility" in image
            assert image["visibility"] == "public"

    def test_list_images_with_name_filter(self, client):
        """Test listing images with name filter."""
        response = client.get("/v2/images?name=Ubuntu 22.04 LTS")
        assert response.status_code == 200
        
        data = response.json()
        images = data["images"]
        assert len(images) >= 1
        
        # Should contain the Ubuntu image
        ubuntu_found = any(img["name"] == "Ubuntu 22.04 LTS" for img in images)
        assert ubuntu_found

    def test_get_image_by_uuid(self, client):
        """Test getting image by UUID."""
        ubuntu_uuid = "3394d42a-9583-4c79-9a1b-7bb94ae7dc04"
        response = client.get(f"/v2/images/{ubuntu_uuid}")
        assert response.status_code == 200
        
        image = response.json()
        assert image["id"] == ubuntu_uuid
        assert image["name"] == "Ubuntu 22.04 LTS"
        assert image["status"] == "active"
        assert image["container_format"] == "bare"
        assert image["disk_format"] == "qcow2"

    def test_get_image_by_name_alias(self, client):
        """Test getting image by name alias."""
        response = client.get("/v2/images/ubuntu-22.04")
        assert response.status_code == 200
        
        image = response.json()
        assert image["id"] == "3394d42a-9583-4c79-9a1b-7bb94ae7dc04"
        assert image["name"] == "Ubuntu 22.04 LTS"

    def test_get_nonexistent_image(self, client):
        """Test getting non-existent image returns 404."""
        response = client.get("/v2/images/nonexistent-image")
        assert response.status_code == 404
        
        error = response.json()
        assert "not found" in error["detail"].lower()

    def test_all_mock_images_accessible(self, client):
        """Test that all mock images are accessible."""
        expected_images = [
            {
                "id": "3394d42a-9583-4c79-9a1b-7bb94ae7dc04",
                "name": "Ubuntu 22.04 LTS"
            },
            {
                "id": "c8b1e50a-3c91-4d2e-a5f6-8f7b2a9c1d3e", 
                "name": "CentOS 8 Stream"
            },
            {
                "id": "f2e4d6c8-1a3b-4c5d-9e7f-2b8d4c6e8f0a",
                "name": "Debian 12 Bookworm"
            }
        ]
        
        for expected in expected_images:
            response = client.get(f"/v2/images/{expected['id']}")
            assert response.status_code == 200
            image = response.json()
            assert image["id"] == expected["id"]
            assert image["name"] == expected["name"]

    def test_image_uuids_are_valid(self, client):
        """Test that all image IDs are valid UUIDs."""
        import uuid
        
        response = client.get("/v2/images")
        assert response.status_code == 200
        
        images = response.json()["images"]
        for image in images:
            # Should be able to parse as UUID
            try:
                uuid.UUID(image["id"])
            except ValueError:
                pytest.fail(f"Image ID {image['id']} is not a valid UUID")

    def test_image_sizes_are_realistic(self, client):
        """Test that image sizes are realistic."""
        response = client.get("/v2/images")
        assert response.status_code == 200
        
        images = response.json()["images"]
        for image in images:
            size = image["size"]
            # Image sizes should be reasonable (between 100MB and 10GB)
            assert 100 * 1024 * 1024 <= size <= 10 * 1024 * 1024 * 1024
            assert isinstance(size, int)

    def test_image_timestamps_format(self, client):
        """Test that image timestamps are properly formatted."""
        response = client.get("/v2/images")
        assert response.status_code == 200
        
        images = response.json()["images"]
        for image in images:
            # Should have ISO format timestamps
            assert "created_at" in image
            assert "updated_at" in image
            assert image["created_at"].endswith("Z")
            assert image["updated_at"].endswith("Z")
            
            # Should be parseable as datetime
            from datetime import datetime
            datetime.fromisoformat(image["created_at"].replace("Z", "+00:00"))
            datetime.fromisoformat(image["updated_at"].replace("Z", "+00:00"))

    def test_backward_compatibility_name_mapping(self, client):
        """Test backward compatibility name mappings work."""
        name_mappings = {
            "ubuntu-22.04": "3394d42a-9583-4c79-9a1b-7bb94ae7dc04",
            "centos-8": "c8b1e50a-3c91-4d2e-a5f6-8f7b2a9c1d3e",
            "debian-12": "f2e4d6c8-1a3b-4c5d-9e7f-2b8d4c6e8f0a"
        }
        
        for name, expected_uuid in name_mappings.items():
            response = client.get(f"/v2/images/{name}")
            assert response.status_code == 200
            image = response.json()
            assert image["id"] == expected_uuid