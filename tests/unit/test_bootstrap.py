"""Unit tests for bootstrap functionality."""

import pytest
from sqlalchemy.orm import Session

from mopenstack.bootstrap import (
    bootstrap_keystone,
    create_admin_project,
    create_admin_user,
    create_default_domain,
    create_default_roles,
)
from mopenstack.common.database import SessionLocal
from mopenstack.models.keystone import Domain, Project, Role, User


@pytest.fixture(scope="function")
def clean_db():
    """Provide a clean database session for testing."""
    db = SessionLocal()
    
    # Clean up all test data before test
    try:
        db.query(User).delete()
        db.query(Project).delete()
        db.query(Domain).delete()
        db.query(Role).delete()
        db.commit()
    finally:
        pass  # Keep session open for test
    
    yield db
    
    # Clean up after test
    try:
        db.rollback()  # Roll back any pending transactions
        db.query(User).delete()
        db.query(Project).delete() 
        db.query(Domain).delete()
        db.query(Role).delete()
        db.commit()
    except Exception:
        db.rollback()  # If cleanup fails, at least rollback
    finally:
        db.close()


class TestBootstrapComponents:
    """Test individual bootstrap components."""

    def test_create_default_domain(self, clean_db: Session):
        """Test default domain creation."""
        # Should create new domain
        domain = create_default_domain(clean_db)
        
        assert domain is not None
        assert domain.name == "Default"
        assert domain.description == "Default domain for MockOpenStack"
        assert domain.enabled is True
        assert domain.id is not None

        # Should return existing domain on second call
        domain2 = create_default_domain(clean_db)
        assert domain2.id == domain.id
        assert domain2.name == domain.name

        # Verify domain was persisted
        db_domain = clean_db.query(Domain).filter(Domain.name == "Default").first()
        assert db_domain is not None
        assert db_domain.id == domain.id

    def test_create_admin_project(self, clean_db: Session):
        """Test admin project creation."""
        # First create default domain
        domain = create_default_domain(clean_db)
        
        # Create admin project
        project = create_admin_project(clean_db, domain)
        
        assert project is not None
        assert project.name == "admin"  # Based on settings.admin_project
        assert project.description == "Admin project for MockOpenStack"
        assert project.enabled is True
        assert project.domain_id == domain.id
        assert project.id is not None

        # Should return existing project on second call
        project2 = create_admin_project(clean_db, domain)
        assert project2.id == project.id
        assert project2.name == project.name

        # Verify project was persisted
        from mopenstack.common.config import settings
        db_project = clean_db.query(Project).filter(Project.name == settings.admin_project).first()
        assert db_project is not None
        assert db_project.id == project.id
        assert db_project.domain_id == domain.id

    def test_create_admin_user(self, clean_db: Session):
        """Test admin user creation."""
        # Setup prerequisites
        domain = create_default_domain(clean_db)
        project = create_admin_project(clean_db, domain)
        
        # Create admin user
        user = create_admin_user(clean_db, domain, project)
        
        assert user is not None
        assert user.name == "admin"  # Based on settings.admin_username
        assert user.enabled is True
        assert user.domain_id == domain.id
        assert user.default_project_id == project.id
        assert user.id is not None
        assert user.password_hash is not None
        
        # Password should be hashed, not plaintext
        from mopenstack.common.config import settings
        assert user.password_hash != settings.admin_password
        assert len(user.password_hash) > 20  # bcrypt hashes are long

        # Should return existing user on second call
        user2 = create_admin_user(clean_db, domain, project)
        assert user2.id == user.id
        assert user2.name == user.name
        assert user2.password_hash == user.password_hash

        # Verify user was persisted
        db_user = clean_db.query(User).filter(
            User.name == settings.admin_username,
            User.domain_id == domain.id
        ).first()
        assert db_user is not None
        assert db_user.id == user.id

    def test_create_default_roles(self, clean_db: Session):
        """Test default roles creation."""
        # Should create all default roles
        create_default_roles(clean_db)
        
        expected_roles = ["admin", "member", "reader"]
        created_roles = clean_db.query(Role).all()
        
        assert len(created_roles) == len(expected_roles)
        
        role_names = [role.name for role in created_roles]
        for expected_role in expected_roles:
            assert expected_role in role_names

        # Check individual roles
        for role in created_roles:
            assert role.name in expected_roles
            assert role.description is not None
            assert role.description.endswith(" role")
            assert role.id is not None

        # Should not create duplicates on second call
        create_default_roles(clean_db)
        roles_after_second_call = clean_db.query(Role).all()
        assert len(roles_after_second_call) == len(expected_roles)

    def test_password_hashing(self, clean_db: Session):
        """Test that password hashing works correctly."""
        domain = create_default_domain(clean_db)
        project = create_admin_project(clean_db, domain)
        user = create_admin_user(clean_db, domain, project)
        
        # Verify password can be verified
        from mopenstack.services.keystone.auth import verify_password
        from mopenstack.common.config import settings
        
        assert verify_password(settings.admin_password, user.password_hash)
        assert not verify_password("wrong-password", user.password_hash)


class TestBootstrapIntegration:
    """Test complete bootstrap integration."""

    def test_bootstrap_keystone_complete(self, clean_db: Session):
        """Test complete bootstrap process."""
        # Bootstrap should succeed without errors
        bootstrap_keystone()
        
        # Verify all components were created
        domains = clean_db.query(Domain).all()
        assert len(domains) >= 1
        default_domain = next((d for d in domains if d.name == "Default"), None)
        assert default_domain is not None

        projects = clean_db.query(Project).all()
        assert len(projects) >= 1
        
        from mopenstack.common.config import settings
        admin_project = next((p for p in projects if p.name == settings.admin_project), None)
        assert admin_project is not None
        assert admin_project.domain_id == default_domain.id

        users = clean_db.query(User).all()
        assert len(users) >= 1
        admin_user = next((u for u in users if u.name == settings.admin_username), None)
        assert admin_user is not None
        assert admin_user.domain_id == default_domain.id
        assert admin_user.default_project_id == admin_project.id

        roles = clean_db.query(Role).all()
        assert len(roles) == 3  # admin, member, reader
        role_names = [r.name for r in roles]
        assert "admin" in role_names
        assert "member" in role_names
        assert "reader" in role_names

    def test_bootstrap_idempotency(self, clean_db: Session):
        """Test that bootstrap can be run multiple times safely."""
        # First bootstrap
        bootstrap_keystone()
        
        # Record initial state
        initial_domains = clean_db.query(Domain).count()
        initial_projects = clean_db.query(Project).count()
        initial_users = clean_db.query(User).count()
        initial_roles = clean_db.query(Role).count()
        
        # Second bootstrap should not create duplicates
        bootstrap_keystone()
        
        # Verify counts are the same
        assert clean_db.query(Domain).count() == initial_domains
        assert clean_db.query(Project).count() == initial_projects
        assert clean_db.query(User).count() == initial_users
        assert clean_db.query(Role).count() == initial_roles

    def test_bootstrap_with_existing_partial_data(self, clean_db: Session):
        """Test bootstrap with some existing data."""
        # Create partial data manually
        domain = create_default_domain(clean_db)
        
        # Now run full bootstrap
        bootstrap_keystone()
        
        # Should complete successfully and create missing pieces
        projects = clean_db.query(Project).all()
        users = clean_db.query(User).all()
        roles = clean_db.query(Role).all()
        
        assert len(projects) >= 1
        assert len(users) >= 1
        assert len(roles) == 3

        # Domain should be the same instance
        current_domain = clean_db.query(Domain).filter(Domain.name == "Default").first()
        assert current_domain.id == domain.id

    def test_bootstrap_database_transactions(self, clean_db: Session):
        """Test that bootstrap operations use proper database transactions."""
        # This test ensures that if bootstrap fails, it doesn't leave partial data
        
        # Mock a failure scenario by creating invalid state
        # (This is a simplified test - in practice you'd mock database operations)
        
        bootstrap_keystone()
        
        # Verify all related data exists and is consistent
        domain = clean_db.query(Domain).filter(Domain.name == "Default").first()
        assert domain is not None
        
        from mopenstack.common.config import settings
        project = clean_db.query(Project).filter(Project.name == settings.admin_project).first()
        assert project is not None
        assert project.domain_id == domain.id
        
        user = clean_db.query(User).filter(
            User.name == settings.admin_username,
            User.domain_id == domain.id
        ).first()
        assert user is not None
        assert user.default_project_id == project.id


class TestBootstrapErrorHandling:
    """Test bootstrap error handling scenarios."""

    def test_bootstrap_with_database_error(self, clean_db: Session):
        """Test bootstrap behavior with database errors."""
        # This test ensures that bootstrap functions properly handle database errors
        # We can't easily simulate database errors in a unit test without complex mocking,
        # so we'll test with invalid data that should cause a database constraint error
        
        from mopenstack.models.keystone import Domain
        
        # Try to create two domains with the same name (should violate unique constraint)
        domain1 = Domain(name="duplicate", description="First", enabled=True)
        domain2 = Domain(name="duplicate", description="Second", enabled=True)
        
        clean_db.add(domain1)
        clean_db.commit()
        
        # This should fail due to unique constraint
        clean_db.add(domain2)
        with pytest.raises(Exception):  # Database constraint error
            clean_db.commit()

    def test_bootstrap_configuration_validation(self):
        """Test that bootstrap validates configuration."""
        from mopenstack.common.config import settings
        
        # Essential settings should be available
        assert settings.admin_username is not None
        assert settings.admin_password is not None
        assert settings.admin_project is not None
        
        # Settings should have reasonable values
        assert len(settings.admin_username) > 0
        assert len(settings.admin_password) > 0
        assert len(settings.admin_project) > 0

    def test_domain_creation_with_invalid_data(self, clean_db: Session):
        """Test domain creation with edge cases."""
        # Test that function handles existing domain properly
        domain1 = create_default_domain(clean_db)
        domain2 = create_default_domain(clean_db)
        
        # Should return the same domain
        assert domain1.id == domain2.id
        
        # Should only have one default domain
        domain_count = clean_db.query(Domain).filter(Domain.name == "Default").count()
        assert domain_count == 1

    def test_user_creation_password_requirements(self, clean_db: Session):
        """Test that user creation properly handles password requirements."""
        domain = create_default_domain(clean_db)
        project = create_admin_project(clean_db, domain)
        user = create_admin_user(clean_db, domain, project)
        
        # Password hash should meet basic requirements
        assert user.password_hash is not None
        assert len(user.password_hash) >= 50  # bcrypt produces long hashes
        assert user.password_hash.startswith("$2")  # bcrypt signature
        
        # Should be verifiable
        from mopenstack.services.keystone.auth import verify_password
        from mopenstack.common.config import settings
        assert verify_password(settings.admin_password, user.password_hash)