"""Unit tests for Nova schemas."""

import pytest
from pydantic import ValidationError

from mopenstack.services.nova.schemas import (
    Flavor,
    FlavorCreate,
    FlavorCreateRequest,
    KeyPair,
    KeyPairCreate,
    KeyPairCreateRequest,
    Server,
    ServerCreate,
    ServerCreateRequest,
    ServerUpdate,
    ServerUpdateRequest,
)


class TestFlavorSchemas:
    """Test Flavor-related schemas."""

    def test_flavor_create_validation(self):
        """Test FlavorCreate schema validation."""
        # Valid flavor data
        valid_data = {
            "name": "test-flavor",
            "vcpus": 2,
            "ram": 4096,
            "disk": 20,
            "ephemeral": 0,
            "swap": 0,
            "public": True,
        }
        flavor = FlavorCreate(**valid_data)
        assert flavor.name == "test-flavor"
        assert flavor.vcpus == 2
        assert flavor.ram == 4096
        assert flavor.disk == 20

    def test_flavor_create_minimal(self):
        """Test FlavorCreate with minimal required fields."""
        minimal_data = {
            "name": "minimal-flavor",
            "vcpus": 1,
            "ram": 1024,
            "disk": 10,
        }
        flavor = FlavorCreate(**minimal_data)
        assert flavor.name == "minimal-flavor"
        assert flavor.ephemeral == 0  # Default value
        assert flavor.swap == 0  # Default value
        assert flavor.public is True  # Default value

    def test_flavor_create_validation_errors(self):
        """Test FlavorCreate validation errors."""
        # Missing required fields
        with pytest.raises(ValidationError) as exc_info:
            FlavorCreate(name="test")
        assert "vcpus" in str(exc_info.value)

        # Invalid data types
        with pytest.raises(ValidationError):
            FlavorCreate(name="test", vcpus="invalid", ram=1024, disk=10)

    def test_flavor_create_request(self):
        """Test FlavorCreateRequest wrapper."""
        flavor_data = {
            "name": "request-flavor",
            "vcpus": 1,
            "ram": 512,
            "disk": 5,
        }
        request = FlavorCreateRequest(flavor=FlavorCreate(**flavor_data))
        assert request.flavor.name == "request-flavor"

    def test_flavor_full_schema(self):
        """Test complete Flavor schema with generated fields."""
        # Test data that would come from database
        db_data = {
            "id": "flavor-123",
            "name": "db-flavor",
            "vcpus": 4,
            "ram": 8192,
            "disk": 40,
            "ephemeral": 10,
            "swap": 1024,
            "public": True,
            "disabled": False,
            "created_at": "2023-01-01T00:00:00",
            "updated_at": "2023-01-01T00:00:00",
        }
        flavor = Flavor(**db_data)
        assert flavor.id == "flavor-123"
        assert flavor.name == "db-flavor"
        assert flavor.disabled is False


class TestServerSchemas:
    """Test Server-related schemas."""

    def test_server_create_validation(self):
        """Test ServerCreate schema validation."""
        # Test with camelCase API format
        api_data = {
            "name": "test-server",
            "imageRef": "image-123",
            "flavorRef": "flavor-456",
            "key_name": "my-key",
            "metadata": {"env": "test"},
            "networks": [{"uuid": "net-789"}],
            "config_drive": False,
            "min_count": 1,
            "max_count": 1,
        }
        server = ServerCreate(**api_data)
        assert server.name == "test-server"
        assert server.image_ref == "image-123"
        assert server.flavor_ref == "flavor-456"
        assert server.key_name == "my-key"
        assert server.metadata == {"env": "test"}
        assert server.min_count == 1

    def test_server_create_snake_case(self):
        """Test ServerCreate with snake_case field names."""
        data = {
            "name": "test-server",
            "image_ref": "image-123",
            "flavor_ref": "flavor-456",
        }
        server = ServerCreate(**data)
        assert server.name == "test-server"
        assert server.image_ref == "image-123"
        assert server.flavor_ref == "flavor-456"

    def test_server_create_required_fields(self):
        """Test ServerCreate required field validation."""
        # Missing image_ref (but has imageRef alias)
        with pytest.raises(ValidationError) as exc_info:
            ServerCreate(name="test", flavor_ref="flavor-123")
        error_str = str(exc_info.value)
        assert "image_ref" in error_str or "imageRef" in error_str

        # Missing flavor_ref (but has flavorRef alias)  
        with pytest.raises(ValidationError) as exc_info:
            ServerCreate(name="test", image_ref="image-123")
        error_str = str(exc_info.value)
        assert "flavor_ref" in error_str or "flavorRef" in error_str

    def test_server_create_request(self):
        """Test ServerCreateRequest wrapper."""
        server_data = {
            "name": "request-server",
            "imageRef": "image-123",
            "flavorRef": "flavor-456",
        }
        request = ServerCreateRequest(server=ServerCreate(**server_data))
        assert request.server.name == "request-server"
        assert request.server.image_ref == "image-123"

    def test_server_update_schema(self):
        """Test ServerUpdate schema."""
        update_data = {"name": "updated-server"}
        update = ServerUpdate(**update_data)
        assert update.name == "updated-server"

        # Test with empty data (all fields optional)
        empty_update = ServerUpdate()
        assert empty_update.name is None

    def test_server_from_db_model(self):
        """Test Server.from_db_model class method."""
        # Mock database model
        class MockServerModel:
            id = "server-123"
            name = "db-server"
            status = "ACTIVE"
            power_state = "Running"
            task_state = None
            vm_state = "active"
            user_id = "user-456"
            project_id = "project-789"
            created_at = "2023-01-01T00:00:00"
            updated_at = "2023-01-01T00:00:00"
            launched_at = "2023-01-01T00:00:00"
            terminated_at = None
            image_id = "image-123"
            flavor_id = "flavor-456"
            key_name = "test-key"
            server_metadata = {"env": "production"}
            networks = [{"uuid": "net-123"}]
            config_drive = False

        mock_model = MockServerModel()
        server = Server.from_db_model(mock_model)

        assert server.id == "server-123"
        assert server.name == "db-server"
        assert server.status == "ACTIVE"
        assert server.user_id == "user-456"
        assert server.project_id == "project-789"
        assert server.image_ref == "image-123"
        assert server.flavor_ref == "flavor-456"
        assert server.metadata == {"env": "production"}
        assert server.networks == [{"uuid": "net-123"}]
        # OpenStack CLI compatibility fields
        assert server.tenant_id == "project-789"
        assert server.image == {"id": "image-123"}
        assert server.flavor == {"id": "flavor-456"}

    def test_server_from_db_model_none_handling(self):
        """Test Server.from_db_model handles None values correctly."""
        class MockServerModelWithNones:
            id = "server-123"
            name = "db-server"
            status = "ACTIVE"
            power_state = "Running"
            task_state = None
            vm_state = "active"
            user_id = "user-456"
            project_id = "project-789"
            created_at = "2023-01-01T00:00:00"
            updated_at = None
            launched_at = None
            terminated_at = None
            image_id = None
            flavor_id = "flavor-456"
            key_name = None
            server_metadata = None  # This was causing the NoneType error
            networks = None  # This was also problematic
            config_drive = False

        mock_model = MockServerModelWithNones()
        server = Server.from_db_model(mock_model)

        assert server.metadata == {}  # Should default to empty dict
        assert server.networks == []  # Should default to empty list
        assert server.image is None  # Should be None when image_id is None
        assert server.flavor == {"id": "flavor-456"}  # Should work when present
        assert server.image_ref == ""  # Should be empty string when image_id is None


class TestKeyPairSchemas:
    """Test KeyPair-related schemas."""

    def test_keypair_create_validation(self):
        """Test KeyPairCreate schema validation."""
        kp_data = {
            "name": "test-keypair",
            "public_key": "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQ...",
            "type": "ssh",
        }
        keypair = KeyPairCreate(**kp_data)
        assert keypair.name == "test-keypair"
        assert keypair.type == "ssh"
        assert "ssh-rsa" in keypair.public_key

    def test_keypair_create_minimal(self):
        """Test KeyPairCreate with minimal data."""
        minimal_data = {"name": "minimal-key"}
        keypair = KeyPairCreate(**minimal_data)
        assert keypair.name == "minimal-key"
        assert keypair.public_key is None  # Optional
        assert keypair.type == "ssh"  # Default

    def test_keypair_create_request(self):
        """Test KeyPairCreateRequest wrapper."""
        kp_data = {"name": "request-key", "type": "ssh"}
        request = KeyPairCreateRequest(keypair=KeyPairCreate(**kp_data))
        assert request.keypair.name == "request-key"

    def test_keypair_full_schema(self):
        """Test complete KeyPair schema."""
        kp_data = {
            "id": "kp-123",
            "name": "full-keypair",
            "public_key": "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQ...",
            "type": "ssh",
            "user_id": "user-456",
            "fingerprint": "ab:cd:ef:gh:ij:kl:mn:op",
            "created_at": "2023-01-01T00:00:00",
        }
        keypair = KeyPair(**kp_data)
        assert keypair.id == "kp-123"
        assert keypair.user_id == "user-456"
        assert keypair.fingerprint == "ab:cd:ef:gh:ij:kl:mn:op"

    def test_keypair_validation_errors(self):
        """Test KeyPair validation errors."""
        # Missing required name
        with pytest.raises(ValidationError):
            KeyPairCreate()

        # The type field accepts any string, so no validation error here
        # Just test that it works with valid values
        kp = KeyPairCreate(name="test", type="rsa")
        assert kp.type == "rsa"


class TestSchemaCompatibility:
    """Test schema compatibility with OpenStack API."""

    def test_server_create_openstack_cli_format(self):
        """Test ServerCreate works with actual OpenStack CLI request format."""
        # This is the actual format sent by OpenStack CLI
        cli_request = {
            "server": {
                "name": "cli-server",
                "imageRef": "3394d42a-9583-4c79-9a1b-7bb94ae7dc04",
                "flavorRef": "d17a7718-05e3-497d-9854-9654f5000e7f", 
                "min_count": 1,
                "max_count": 1
            }
        }
        
        request = ServerCreateRequest(**cli_request)
        assert request.server.name == "cli-server"
        assert request.server.image_ref == "3394d42a-9583-4c79-9a1b-7bb94ae7dc04"
        assert request.server.flavor_ref == "d17a7718-05e3-497d-9854-9654f5000e7f"
        assert request.server.min_count == 1
        assert request.server.max_count == 1

    def test_flavor_create_openstack_format(self):
        """Test FlavorCreate works with OpenStack API format."""
        openstack_request = {
            "flavor": {
                "name": "m1.small",
                "vcpus": 1,
                "ram": 2048,
                "disk": 20,
                "ephemeral": 0,
                "swap": 0,
                "public": True
            }
        }
        
        request = FlavorCreateRequest(**openstack_request)
        assert request.flavor.name == "m1.small"
        assert request.flavor.vcpus == 1
        assert request.flavor.ram == 2048
        assert request.flavor.public is True