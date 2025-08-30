"""Keystone API schemas using Pydantic."""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict


class DomainBase(BaseModel):
    name: str
    description: Optional[str] = None
    enabled: bool = True


class Domain(DomainBase):
    id: str
    created_at: datetime
    updated_at: Optional[datetime] = None
    links: Optional[dict] = None  # OpenStack API compatibility

    model_config = ConfigDict(from_attributes=True)


class ProjectBase(BaseModel):
    name: str
    description: Optional[str] = None
    enabled: bool = True
    domain_id: Optional[str] = None  # Will default to "Default" domain if not provided
    parent_id: Optional[str] = None


class Project(ProjectBase):
    id: str
    created_at: datetime
    updated_at: Optional[datetime] = None
    links: Optional[dict] = None  # OpenStack API compatibility

    model_config = ConfigDict(from_attributes=True)


class UserBase(BaseModel):
    name: str
    email: Optional[str] = None
    enabled: bool = True
    domain_id: Optional[str] = None  # Will default to "Default" domain if not provided
    default_project_id: Optional[str] = None


class UserCreate(UserBase):
    password: str


class User(UserBase):
    id: str
    created_at: datetime
    updated_at: Optional[datetime] = None
    links: Optional[dict] = None  # OpenStack API compatibility

    model_config = ConfigDict(from_attributes=True)


class RoleBase(BaseModel):
    name: str
    description: Optional[str] = None


class Role(RoleBase):
    id: str
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class TokenRequest(BaseModel):
    identity: dict
    scope: Optional[dict] = None


class TokenResponse(BaseModel):
    token: str
    expires_at: datetime
    user: User
    project: Optional[Project] = None


class AuthRequest(BaseModel):
    auth: TokenRequest


class ServiceCatalogEntry(BaseModel):
    type: str
    name: str
    endpoints: List[dict]


class TokenValidation(BaseModel):
    token: dict
    user: User
    project: Optional[Project] = None
    catalog: List[ServiceCatalogEntry]


# Update schemas
class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    enabled: Optional[bool] = None


# Request wrappers for OpenStack API compatibility
class ProjectCreateRequest(BaseModel):
    project: ProjectBase


class ProjectUpdateRequest(BaseModel):
    project: ProjectUpdate


class DomainCreateRequest(BaseModel):
    domain: DomainBase


class UserCreateRequest(BaseModel):
    user: UserCreate
