"""Keystone service implementation."""

from datetime import datetime, timedelta, timezone
from typing import List, Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from ...models.keystone import Domain, Project, Role, Token, User
from .auth import create_access_token, get_password_hash, verify_password
from .schemas import DomainBase, ProjectBase, ProjectUpdate, RoleBase, UserCreate


class KeystoneService:
    """Keystone Identity Service implementation."""

    def __init__(self, db: Session):
        self.db = db

    # Domain operations
    def create_domain(self, domain_data: DomainBase) -> Domain:
        """Create a new domain."""
        db_domain = Domain(**domain_data.model_dump())
        self.db.add(db_domain)
        self.db.commit()
        self.db.refresh(db_domain)
        return db_domain

    def get_domain(self, domain_id: str) -> Optional[Domain]:
        """Get domain by ID."""
        return self.db.query(Domain).filter(Domain.id == domain_id).first()

    def list_domains(self) -> List[Domain]:
        """List all domains."""
        return self.db.query(Domain).all()

    # Project operations
    def create_project(self, project_data: ProjectBase) -> Project:
        """Create a new project."""
        # If no domain_id provided, use the default domain
        domain_id = project_data.domain_id
        if not domain_id:
            domains = self.list_domains()
            default_domain = next(
                (d for d in domains if d.name.lower() == "default"), None
            )
            if default_domain:
                domain_id = default_domain.id
            else:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail="Default domain not found"
                )

        # Verify domain exists
        domain = self.get_domain(domain_id)
        if not domain:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Domain not found"
            )

        project_dict = project_data.model_dump()
        project_dict["domain_id"] = domain_id
        db_project = Project(**project_dict)
        self.db.add(db_project)
        self.db.commit()
        self.db.refresh(db_project)
        return db_project

    def get_project(self, project_id: str) -> Optional[Project]:
        """Get project by ID."""
        return self.db.query(Project).filter(Project.id == project_id).first()

    def list_projects(self) -> List[Project]:
        """List all projects."""
        return self.db.query(Project).all()

    def update_project(self, project_id: str, project_data: ProjectUpdate) -> Optional[Project]:
        """Update a project."""
        db_project = self.get_project(project_id)
        if not db_project:
            return None

        # Update only provided fields
        update_data = project_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_project, field, value)

        self.db.commit()
        self.db.refresh(db_project)
        return db_project

    def delete_project(self, project_id: str) -> bool:
        """Delete a project."""
        db_project = self.get_project(project_id)
        if not db_project:
            return False

        self.db.delete(db_project)
        self.db.commit()
        return True

    # User operations
    def create_user(self, user_data: UserCreate) -> User:
        """Create a new user."""
        # If no domain_id provided, use the default domain
        domain_id = user_data.domain_id
        if not domain_id:
            domains = self.list_domains()
            default_domain = next(
                (d for d in domains if d.name.lower() == "default"), None
            )
            if default_domain:
                domain_id = default_domain.id
            else:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail="Default domain not found"
                )

        # Verify domain exists
        domain = self.get_domain(domain_id)
        if not domain:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Domain not found"
            )

        # Hash password
        password_hash = get_password_hash(user_data.password)

        user_dict = user_data.model_dump()
        user_dict.pop("password")
        user_dict["domain_id"] = domain_id
        user_dict["password_hash"] = password_hash

        db_user = User(**user_dict)
        self.db.add(db_user)
        self.db.commit()
        self.db.refresh(db_user)
        return db_user

    def get_user(self, user_id: str) -> Optional[User]:
        """Get user by ID."""
        return self.db.query(User).filter(User.id == user_id).first()

    def get_user_by_name(self, username: str, domain_id: str) -> Optional[User]:
        """Get user by name and domain."""
        return (
            self.db.query(User)
            .filter(User.name == username, User.domain_id == domain_id)
            .first()
        )

    def list_users(self) -> List[User]:
        """List all users."""
        return self.db.query(User).all()

    def authenticate_user(
        self, username: str, password: str, domain_id: str
    ) -> Optional[User]:
        """Authenticate user with username and password."""
        user = self.get_user_by_name(username, domain_id)
        if not user or not verify_password(password, user.password_hash):
            return None
        if not user.enabled:
            return None
        return user

    # Role operations
    def create_role(self, role_data: RoleBase) -> Role:
        """Create a new role."""
        db_role = Role(**role_data.model_dump())
        self.db.add(db_role)
        self.db.commit()
        self.db.refresh(db_role)
        return db_role

    def get_role(self, role_id: str) -> Optional[Role]:
        """Get role by ID."""
        return self.db.query(Role).filter(Role.id == role_id).first()

    def list_roles(self) -> List[Role]:
        """List all roles."""
        return self.db.query(Role).all()

    # Token operations
    def create_token(self, user: User, project_id: Optional[str] = None) -> Token:
        """Create authentication token for user."""
        # Generate JWT token
        token_data = {
            "sub": user.id,
            "username": user.name,
            "domain_id": user.domain_id,
        }
        if project_id:
            token_data["project_id"] = project_id

        access_token = create_access_token(
            token_data, expires_delta=timedelta(hours=24)
        )

        # Store token in database (in a real implementation, we'd hash this)
        # For this mock, we'll store the token directly for simplicity
        db_token = Token(
            token_hash=access_token,  # Using token directly for mock
            user_id=user.id,
            project_id=project_id,
            expires_at=datetime.now(timezone.utc) + timedelta(hours=24),
        )
        self.db.add(db_token)
        self.db.commit()
        self.db.refresh(db_token)

        return db_token, access_token

    def validate_token(self, token: str) -> Optional[dict]:
        """Validate authentication token."""
        from .auth import verify_token

        payload = verify_token(token)
        if not payload:
            return None

        # Check if token exists in database and is not expired
        # In this mock, we store tokens directly (not hashed)
        db_token = (
            self.db.query(Token)
            .filter(
                Token.token_hash == token, Token.expires_at > datetime.now(timezone.utc)
            )
            .first()
        )

        if not db_token:
            return None

        return payload
