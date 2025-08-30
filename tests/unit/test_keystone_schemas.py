"""Unit tests for Keystone schemas."""

import pytest
from pydantic import ValidationError

from mopenstack.services.keystone.schemas import (
    AuthRequest,
    Domain,
    DomainBase,
    DomainCreateRequest,
    Project,
    ProjectBase,
    ProjectCreateRequest,
    ProjectUpdate,
    ProjectUpdateRequest,
    ServiceCatalogEntry,
    User,
    UserCreate,
    UserCreateRequest,
)


class TestAuthSchemas:
    """Test authentication-related schemas."""

    def test_auth_request_password_auth(self):
        """Test AuthRequest with password authentication."""
        auth_data = {
            "auth": {
                "identity": {
                    "methods": ["password"],
                    "password": {
                        "user": {
                            "name": "admin",
                            "password": "secret",
                            "domain": {"id": "default"}
                        }
                    }
                },
                "scope": {
                    "project": {
                        "name": "admin",
                        "domain": {"name": "Default"}
                    }
                }
            }
        }
        
        request = AuthRequest(**auth_data)
        assert "password" in request.auth.identity["methods"]
        assert request.auth.identity["password"]["user"]["name"] == "admin"
        assert request.auth.identity["password"]["user"]["password"] == "secret"
        assert request.auth.scope["project"]["name"] == "admin"

    def test_auth_request_validation_errors(self):
        """Test AuthRequest validation errors."""
        # Missing auth field
        with pytest.raises(ValidationError):
            AuthRequest()

        # Invalid structure
        with pytest.raises(ValidationError):
            AuthRequest(auth={"invalid": "structure"})


class TestDomainSchemas:
    """Test Domain-related schemas."""

    def test_domain_create_validation(self):
        """Test DomainBase schema validation."""
        domain_data = {
            "name": "test-domain",
            "description": "Test domain for unit tests",
            "enabled": True
        }
        domain = DomainBase(**domain_data)
        assert domain.name == "test-domain"
        assert domain.description == "Test domain for unit tests"
        assert domain.enabled is True

    def test_domain_create_minimal(self):
        """Test DomainBase with minimal data."""
        minimal_data = {"name": "minimal-domain"}
        domain = DomainBase(**minimal_data)
        assert domain.name == "minimal-domain"
        assert domain.description is None  # Default value
        assert domain.enabled is True  # Default value

    def test_domain_create_request(self):
        """Test DomainCreateRequest wrapper."""
        domain_data = {"name": "request-domain"}
        request = DomainCreateRequest(domain=DomainBase(**domain_data))
        assert request.domain.name == "request-domain"

    def test_domain_full_schema(self):
        """Test complete Domain schema."""
        from datetime import datetime
        domain_data = {
            "id": "domain-123",
            "name": "full-domain", 
            "description": "Full domain schema",
            "enabled": True,
            "created_at": datetime(2023, 1, 1),
            "updated_at": datetime(2023, 1, 1)
        }
        domain = Domain(**domain_data)
        assert domain.id == "domain-123"
        assert domain.name == "full-domain"
        assert domain.created_at == datetime(2023, 1, 1)

    def test_domain_validation_errors(self):
        """Test Domain validation errors."""
        # Missing required name
        with pytest.raises(ValidationError):
            DomainBase()


class TestProjectSchemas:
    """Test Project-related schemas."""

    def test_project_create_validation(self):
        """Test ProjectBase schema validation."""
        project_data = {
            "name": "test-project",
            "description": "Test project",
            "enabled": True,
            "domain_id": "domain-123",
            "parent_id": "parent-456"
        }
        project = ProjectBase(**project_data)
        assert project.name == "test-project"
        assert project.description == "Test project"
        assert project.domain_id == "domain-123"
        assert project.parent_id == "parent-456"

    def test_project_create_minimal(self):
        """Test ProjectBase with minimal data."""
        minimal_data = {"name": "minimal-project"}
        project = ProjectBase(**minimal_data)
        assert project.name == "minimal-project"
        assert project.description is None  # Default
        assert project.enabled is True  # Default
        assert project.domain_id is None  # Default
        assert project.parent_id is None  # Default

    def test_project_update_schema(self):
        """Test ProjectUpdate schema."""
        update_data = {
            "name": "updated-project",
            "description": "Updated description",
            "enabled": False
        }
        update = ProjectUpdate(**update_data)
        assert update.name == "updated-project"
        assert update.description == "Updated description"
        assert update.enabled is False

        # Test with empty data (all fields optional)
        empty_update = ProjectUpdate()
        assert empty_update.name is None
        assert empty_update.description is None
        assert empty_update.enabled is None

    def test_project_create_request(self):
        """Test ProjectCreateRequest wrapper."""
        project_data = {"name": "request-project"}
        request = ProjectCreateRequest(project=ProjectBase(**project_data))
        assert request.project.name == "request-project"

    def test_project_update_request(self):
        """Test ProjectUpdateRequest wrapper."""
        update_data = {"name": "updated-project"}
        request = ProjectUpdateRequest(project=ProjectUpdate(**update_data))
        assert request.project.name == "updated-project"

    def test_project_full_schema(self):
        """Test complete Project schema."""
        project_data = {
            "id": "project-123",
            "name": "full-project",
            "description": "Full project schema",
            "enabled": True,
            "domain_id": "domain-456",
            "parent_id": "parent-789",
            "created_at": "2023-01-01T00:00:00",
            "updated_at": "2023-01-01T00:00:00"
        }
        project = Project(**project_data)
        assert project.id == "project-123"
        assert project.domain_id == "domain-456"
        assert project.parent_id == "parent-789"

    def test_project_validation_errors(self):
        """Test Project validation errors."""
        # Missing required name
        with pytest.raises(ValidationError):
            ProjectBase()


class TestUserSchemas:
    """Test User-related schemas."""

    def test_user_create_validation(self):
        """Test UserCreate schema validation."""
        user_data = {
            "name": "testuser",
            "password": "secret123",
            "email": "test@example.com",
            "description": "Test user",
            "enabled": True,
            "domain_id": "domain-123",
            "default_project_id": "project-456"
        }
        user = UserCreate(**user_data)
        assert user.name == "testuser"
        assert user.password == "secret123"
        assert user.email == "test@example.com"
        assert user.domain_id == "domain-123"

    def test_user_create_minimal(self):
        """Test UserCreate with minimal data."""
        minimal_data = {"name": "minimal-user", "password": "secret123"}
        user = UserCreate(**minimal_data)
        assert user.name == "minimal-user"
        assert user.password == "secret123"  # Required
        assert user.email is None  # Optional
        assert user.enabled is True  # Default
        assert user.domain_id is None  # Optional

    def test_user_create_request(self):
        """Test UserCreateRequest wrapper."""
        user_data = {"name": "request-user", "password": "secret"}
        request = UserCreateRequest(user=UserCreate(**user_data))
        assert request.user.name == "request-user"
        assert request.user.password == "secret"

    def test_user_full_schema(self):
        """Test complete User schema."""
        user_data = {
            "id": "user-123",
            "name": "fulluser",
            "email": "full@example.com",
            "description": "Full user schema",
            "enabled": True,
            "domain_id": "domain-456",
            "default_project_id": "project-789",
            "created_at": "2023-01-01T00:00:00",
            "updated_at": "2023-01-01T00:00:00"
        }
        user = User(**user_data)
        assert user.id == "user-123"
        assert user.email == "full@example.com"
        assert user.default_project_id == "project-789"

    def test_user_validation_errors(self):
        """Test User validation errors."""
        # Missing required name
        with pytest.raises(ValidationError):
            UserCreate()


class TestServiceCatalogSchemas:
    """Test service catalog schemas."""

    def test_service_catalog_entry(self):
        """Test ServiceCatalogEntry schema."""
        catalog_data = {
            "type": "compute",
            "name": "nova",
            "endpoints": [
                {
                    "id": "nova-public",
                    "interface": "public",
                    "url": "http://localhost:8774/v2.1"
                }
            ]
        }
        entry = ServiceCatalogEntry(**catalog_data)
        assert entry.type == "compute"
        assert entry.name == "nova"
        assert len(entry.endpoints) == 1
        assert entry.endpoints[0]["interface"] == "public"

    def test_service_catalog_multiple_endpoints(self):
        """Test ServiceCatalogEntry with multiple endpoints."""
        catalog_data = {
            "type": "identity",
            "name": "keystone",
            "endpoints": [
                {
                    "id": "keystone-public",
                    "interface": "public", 
                    "url": "http://localhost:5000/v3"
                },
                {
                    "id": "keystone-admin",
                    "interface": "admin",
                    "url": "http://localhost:35357/v3"
                }
            ]
        }
        entry = ServiceCatalogEntry(**catalog_data)
        assert len(entry.endpoints) == 2
        interfaces = [ep["interface"] for ep in entry.endpoints]
        assert "public" in interfaces
        assert "admin" in interfaces


class TestSchemaIntegration:
    """Test schema integration and compatibility."""

    def test_openstack_auth_flow(self):
        """Test complete OpenStack authentication flow schemas."""
        # Typical authentication request
        auth_request = {
            "auth": {
                "identity": {
                    "methods": ["password"],
                    "password": {
                        "user": {
                            "name": "admin",
                            "password": "password",
                            "domain": {"name": "Default"}
                        }
                    }
                },
                "scope": {
                    "project": {
                        "name": "admin",
                        "domain": {"name": "Default"}
                    }
                }
            }
        }
        
        request = AuthRequest(**auth_request)
        assert request.auth.identity["password"]["user"]["name"] == "admin"
        assert request.auth.scope["project"]["name"] == "admin"

    def test_domain_project_hierarchy(self):
        """Test domain and project relationship schemas."""
        # Domain creation
        domain = DomainBase(name="corp", description="Corporate domain")
        assert domain.name == "corp"
        
        # Project under domain
        project = ProjectBase(
            name="corp-project",
            description="Corporate project", 
            domain_id="domain-123"
        )
        assert project.domain_id == "domain-123"

    def test_user_project_assignment(self):
        """Test user and project relationship schemas."""
        # User with default project
        user = UserCreate(
            name="employee",
            password="secret",
            domain_id="domain-123",
            default_project_id="project-456"
        )
        assert user.default_project_id == "project-456"
        assert user.domain_id == "domain-123"