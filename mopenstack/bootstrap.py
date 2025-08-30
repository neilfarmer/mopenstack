"""Bootstrap script to initialize MockOpenStack with default data."""

import io
import os
import sys
import warnings

from sqlalchemy.orm import Session

# Comprehensive warning suppression for bcrypt
warnings.filterwarnings("ignore", category=UserWarning)
warnings.filterwarnings("ignore", category=DeprecationWarning)

# Set environment variable to suppress bcrypt warnings at the C level
os.environ["PYTHONWARNINGS"] = "ignore"

# Capture all stderr output during imports
original_stderr = sys.stderr
captured_stderr = io.StringIO()

# Redirect stderr completely during all imports
sys.stderr = captured_stderr

try:
    from .common.config import settings
    from .common.database import Base, SessionLocal, engine
    from .models.keystone import Domain, Project, Role, User
    from .services.keystone.auth import get_password_hash
finally:
    # Restore stderr after all imports
    sys.stderr = original_stderr


def create_default_domain(db: Session) -> Domain:
    """Create default domain."""
    domain = db.query(Domain).filter(Domain.name == "Default").first()
    if not domain:
        domain = Domain(
            name="Default",
            description="Default domain for MockOpenStack",
            enabled=True,
        )
        db.add(domain)
        db.commit()
        db.refresh(domain)
    return domain


def create_admin_project(db: Session, domain: Domain) -> Project:
    """Create admin project."""
    project = (
        db.query(Project)
        .filter(Project.name == settings.admin_project)
        .first()
    )
    if not project:
        project = Project(
            name=settings.admin_project,
            description="Admin project for MockOpenStack",
            enabled=True,
            domain_id=domain.id,
        )
        db.add(project)
        db.commit()
        db.refresh(project)
    return project


def create_admin_user(db: Session, domain: Domain, project: Project) -> User:
    """Create admin user."""
    admin_user = (
        db.query(User)
        .filter(
            User.name == settings.admin_username, User.domain_id == domain.id
        )
        .first()
    )
    if not admin_user:
        password_hash = get_password_hash(settings.admin_password)
        admin_user = User(
            name=settings.admin_username,
            password_hash=password_hash,
            enabled=True,
            domain_id=domain.id,
            default_project_id=project.id,
        )
        db.add(admin_user)
        db.commit()
        db.refresh(admin_user)
    return admin_user


def create_default_roles(db: Session):
    """Create default roles."""
    roles = ["admin", "member", "reader"]
    for role_name in roles:
        role = db.query(Role).filter(Role.name == role_name).first()
        if not role:
            role = Role(
                name=role_name, description=f"{role_name.capitalize()} role"
            )
            db.add(role)
    db.commit()


def bootstrap_keystone():
    """Bootstrap Keystone with default data."""
    print("Bootstrapping MockOpenStack...")

    # Create database tables
    Base.metadata.create_all(bind=engine)

    # Create session
    db = SessionLocal()

    try:
        # Create default domain
        print("Creating default domain...")
        domain = create_default_domain(db)

        # Create admin project
        print("Creating admin project...")
        project = create_admin_project(db, domain)

        # Create admin user
        print("Creating admin user...")
        create_admin_user(db, domain, project)

        # Create default roles
        print("Creating default roles...")
        create_default_roles(db)

        print("Bootstrap complete!")
        print(
            f"Admin credentials: {settings.admin_username} / "
            f"{settings.admin_password}"
        )
        print(f"Admin project: {settings.admin_project}")

    finally:
        db.close()


if __name__ == "__main__":
    bootstrap_keystone()
