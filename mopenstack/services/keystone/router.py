"""Keystone API router."""

from fastapi import APIRouter, Depends, Header, HTTPException, Request, Response, status
from sqlalchemy.orm import Session

from ...common.database import get_db
from .schemas import (
    AuthRequest,
    Domain,
    DomainCreateRequest,
    Project,
    ProjectCreateRequest,
    ProjectUpdateRequest,
    ServiceCatalogEntry,
    User,
    UserCreateRequest,
)
from .service import KeystoneService

router = APIRouter()


def get_keystone_service(db: Session = Depends(get_db)) -> KeystoneService:
    """Get Keystone service instance."""
    return KeystoneService(db)


@router.get("/")
async def get_version_info(request: Request):
    """Get Keystone version information."""
    port = request.url.port or 5000
    base_url = f"http://localhost:{port}"

    return {
        "version": {
            "id": "v3.14",
            "status": "stable",
            "updated": "2023-01-01T00:00:00Z",
            "links": [{"rel": "self", "href": f"{base_url}/v3"}],
            "media-types": [
                {
                    "base": "application/json",
                    "type": "application/vnd.openstack.identity-v3+json",
                }
            ],
        }
    }


@router.post("/auth/tokens")
async def create_token(
    auth_request: AuthRequest,
    request: Request,
    response: Response,
    keystone: KeystoneService = Depends(get_keystone_service),
):
    """Authenticate and create token."""
    identity = auth_request.auth.identity

    # Handle password authentication
    if "password" in identity:
        password_data = identity["password"]
        user_data = password_data["user"]

        username = user_data["name"]
        password = user_data["password"]
        domain_spec = user_data.get("domain", {})
        domain_id = domain_spec.get("id", "default")

        # Handle "default" domain name -> find actual domain ID
        if domain_id == "default":
            domains = keystone.list_domains()
            default_domain = next(
                (d for d in domains if d.name.lower() == "default"), None
            )
            if default_domain:
                domain_id = default_domain.id

        # Authenticate user
        user = keystone.authenticate_user(username, password, domain_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
            )

        # Get project if specified in scope
        project_id = None
        project = None
        if auth_request.auth.scope and "project" in auth_request.auth.scope:
            project_spec = auth_request.auth.scope["project"]
            project_id = project_spec.get("id")
            project_name = project_spec.get("name")

            if project_id:
                project = keystone.get_project(project_id)
            elif project_name:
                # Find project by name
                projects = keystone.list_projects()
                project = next((p for p in projects if p.name == project_name), None)
                if project:
                    project_id = project.id

            if not project:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail="Project not found"
                )

        # Create token
        db_token, access_token = keystone.create_token(user, project_id)

        # Get the actual running port from the request
        port = request.url.port or 5000
        base_url = f"http://localhost:{port}"

        # Build service catalog
        catalog = [
            ServiceCatalogEntry(
                type="identity",
                name="keystone",
                endpoints=[
                    {
                        "id": "keystone-public",
                        "interface": "public",
                        "url": f"{base_url}/v3",
                    }
                ],
            ),
            ServiceCatalogEntry(
                type="compute",
                name="nova",
                endpoints=[
                    {
                        "id": "nova-public",
                        "interface": "public",
                        "url": f"{base_url}/v2.1",
                    }
                ],
            ),
            ServiceCatalogEntry(
                type="network",
                name="neutron",
                endpoints=[
                    {
                        "id": "neutron-public",
                        "interface": "public",
                        "url": f"{base_url}/v2.0",
                    }
                ],
            ),
            ServiceCatalogEntry(
                type="image",
                name="glance",
                endpoints=[
                    {
                        "id": "glance-public",
                        "interface": "public",
                        "url": f"{base_url}/v2",
                    }
                ],
            ),
        ]

        response_data = {
            "token": {
                "expires_at": db_token.expires_at.isoformat() + "Z",
                "issued_at": db_token.created_at.isoformat() + "Z",
                "methods": ["password"],
                "user": {
                    "id": user.id,
                    "name": user.name,
                    "domain": {"id": user.domain_id, "name": "Default"},
                },
                "catalog": [cat.model_dump() for cat in catalog],
            }
        }

        if project:
            response_data["token"]["project"] = {
                "id": project.id,
                "name": project.name,
                "domain": {"id": project.domain_id, "name": "Default"},
            }

        # Set token in response header
        response.headers["X-Subject-Token"] = access_token
        return response_data

    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Unsupported authentication method",
    )


@router.get("/auth/tokens")
async def validate_token(
    x_auth_token: str = Header(...),
    x_subject_token: str = Header(...),
    keystone: KeystoneService = Depends(get_keystone_service),
):
    """Validate authentication token."""
    # Validate the subject token
    payload = keystone.validate_token(x_subject_token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Token not found"
        )

    # Get user info
    user = keystone.get_user(payload["sub"])
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    response_data = {
        "token": {
            "methods": ["password"],
            "user": {
                "id": user.id,
                "name": user.name,
                "domain": {"id": user.domain_id, "name": "Default"},
            },
        }
    }

    if "project_id" in payload and payload["project_id"]:
        project = keystone.get_project(payload["project_id"])
        if project:
            response_data["token"]["project"] = {
                "id": project.id,
                "name": project.name,
                "domain": {"id": project.domain_id, "name": "Default"},
            }

    return response_data


# Domain endpoints
@router.post("/domains", response_model=dict)
async def create_domain(
    domain_request: DomainCreateRequest,
    keystone: KeystoneService = Depends(get_keystone_service),
):
    """Create a new domain."""
    db_domain = keystone.create_domain(domain_request.domain)
    return {"domain": Domain.model_validate(db_domain).model_dump()}


@router.get("/domains/{domain_id}")
async def get_domain(
    domain_id: str, keystone: KeystoneService = Depends(get_keystone_service)
):
    """Get domain by ID."""
    domain = keystone.get_domain(domain_id)
    if not domain:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Domain not found"
        )
    return {"domain": Domain.model_validate(domain).model_dump()}


@router.get("/domains")
async def list_domains(keystone: KeystoneService = Depends(get_keystone_service)):
    """List all domains."""
    domains = keystone.list_domains()
    return {
        "domains": [Domain.model_validate(domain).model_dump() for domain in domains]
    }


# Project endpoints
@router.post("/projects")
async def create_project(
    request: Request,
    project_request: ProjectCreateRequest,
    keystone: KeystoneService = Depends(get_keystone_service),
):
    """Create a new project."""
    db_project = keystone.create_project(project_request.project)
    port = request.url.port or 5000
    base_url = f"http://localhost:{port}"

    project_data = Project.model_validate(db_project).model_dump()
    project_data["links"] = {"self": f"{base_url}/v3/projects/{db_project.id}"}

    return {"project": project_data}


@router.get("/projects/{project_identifier}")
async def get_project(
    project_identifier: str, keystone: KeystoneService = Depends(get_keystone_service)
):
    """Get project by ID or name."""
    project = keystone._resolve_project(project_identifier)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Project not found"
        )
    return {"project": Project.model_validate(project).model_dump()}


@router.get("/projects")
async def list_projects(keystone: KeystoneService = Depends(get_keystone_service)):
    """List all projects."""
    projects = keystone.list_projects()
    return {
        "projects": [
            Project.model_validate(project).model_dump() for project in projects
        ]
    }


@router.patch("/projects/{project_identifier}")
async def update_project(
    request: Request,
    project_identifier: str,
    project_request: ProjectUpdateRequest,
    keystone: KeystoneService = Depends(get_keystone_service),
):
    """Update project by ID or name."""
    updated_project = keystone.update_project(
        project_identifier, project_request.project
    )
    if not updated_project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Project not found"
        )

    port = request.url.port or 5000
    base_url = f"http://localhost:{port}"

    project_data = Project.model_validate(updated_project).model_dump()
    project_data["links"] = {"self": f"{base_url}/v3/projects/{updated_project.id}"}

    return {"project": project_data}


@router.delete("/projects/{project_identifier}")
async def delete_project(
    project_identifier: str, keystone: KeystoneService = Depends(get_keystone_service)
):
    """Delete project by ID or name."""
    success = keystone.delete_project(project_identifier)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Project not found"
        )

    return Response(status_code=status.HTTP_204_NO_CONTENT)


# User endpoints
@router.post("/users")
async def create_user(
    user_request: UserCreateRequest,
    keystone: KeystoneService = Depends(get_keystone_service),
):
    """Create a new user."""
    db_user = keystone.create_user(user_request.user)
    return {"user": User.model_validate(db_user).model_dump()}


@router.get("/users/{user_id}")
async def get_user(
    user_id: str, keystone: KeystoneService = Depends(get_keystone_service)
):
    """Get user by ID."""
    user = keystone.get_user(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )
    return {"user": User.model_validate(user).model_dump()}


@router.get("/users")
async def list_users(keystone: KeystoneService = Depends(get_keystone_service)):
    """List all users."""
    users = keystone.list_users()
    return {"users": [User.model_validate(user).model_dump() for user in users]}
