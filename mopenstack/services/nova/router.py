"""Nova API router."""

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session

from ...common.database import get_db
from ...services.keystone.auth import get_current_user_info
from .schemas import (
    Flavor,
    FlavorCreateRequest,
    KeyPair,
    KeyPairCreateRequest,
    Server,
    ServerCreateRequest,
    ServerUpdateRequest,
)
from .service import NovaService

router = APIRouter()


def get_nova_service(db: Session = Depends(get_db)) -> NovaService:
    """Get Nova service instance."""
    return NovaService(db)


@router.get("/")
async def get_version_info(request: Request):
    """Get Nova version information."""
    port = request.url.port or 8774
    base_url = f"http://localhost:{port}"

    return {
        "version": {
            "id": "v2.1",
            "status": "CURRENT",
            "updated": "2023-01-01T00:00:00Z",
            "links": [{"rel": "self", "href": f"{base_url}/v2.1"}],
            "media-types": [
                {
                    "base": "application/json",
                    "type": "application/vnd.openstack.compute+json;version=2.1",
                }
            ],
        }
    }


# Flavor endpoints
@router.post("/flavors", response_model=dict)
async def create_flavor(
    flavor_request: FlavorCreateRequest,
    nova: NovaService = Depends(get_nova_service),
    user_info: dict = Depends(get_current_user_info),
):
    """Create a new flavor."""
    # Only admin users can create flavors in real OpenStack
    db_flavor = nova.create_flavor(flavor_request.flavor)
    return {"flavor": Flavor.model_validate(db_flavor).model_dump()}


@router.get("/flavors")
async def list_flavors(
    nova: NovaService = Depends(get_nova_service),
    user_info: dict = Depends(get_current_user_info),
):
    """List all flavors."""
    flavors = nova.list_flavors(disabled=False)
    return {
        "flavors": [Flavor.model_validate(flavor).model_dump() for flavor in flavors]
    }


@router.get("/flavors/detail")
async def list_flavors_detail(
    is_public: str = None,
    nova: NovaService = Depends(get_nova_service),
    user_info: dict = Depends(get_current_user_info),
):
    """List all flavors with detailed information."""
    flavors = nova.list_flavors(disabled=False)
    return {
        "flavors": [Flavor.model_validate(flavor).model_dump() for flavor in flavors]
    }


@router.get("/flavors/{flavor_identifier}")
async def get_flavor(
    flavor_identifier: str,
    nova: NovaService = Depends(get_nova_service),
    user_info: dict = Depends(get_current_user_info),
):
    """Get flavor by ID or name."""
    flavor = nova._resolve_flavor(flavor_identifier)
    if not flavor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Flavor not found"
        )
    return {"flavor": Flavor.model_validate(flavor).model_dump()}


@router.delete("/flavors/{flavor_identifier}")
async def delete_flavor(
    flavor_identifier: str,
    nova: NovaService = Depends(get_nova_service),
    user_info: dict = Depends(get_current_user_info),
):
    """Delete flavor by ID or name."""
    success = nova.delete_flavor(flavor_identifier)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Flavor not found"
        )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# Server endpoints
@router.post("/servers")
async def create_server(
    request: Request,
    server_request: ServerCreateRequest,
    nova: NovaService = Depends(get_nova_service),
    user_info: dict = Depends(get_current_user_info),
):
    """Create a new server."""
    db_server = nova.create_server(
        server_request.server, user_info["user_id"], user_info["project_id"]
    )

    port = request.url.port or 8774
    base_url = f"http://localhost:{port}"

    server_data = Server.from_db_model(db_server).model_dump()
    server_data["links"] = [
        {"rel": "self", "href": f"{base_url}/v2.1/servers/{db_server.id}"}
    ]

    return {"server": server_data}


@router.get("/servers")
async def list_servers(
    nova: NovaService = Depends(get_nova_service),
    user_info: dict = Depends(get_current_user_info),
):
    """List all servers for the current project."""
    servers = nova.list_servers(project_id=user_info["project_id"])
    return {
        "servers": [Server.from_db_model(server).model_dump() for server in servers]
    }


@router.get("/servers/detail")
async def list_servers_detail(
    deleted: bool = False,
    nova: NovaService = Depends(get_nova_service),
    user_info: dict = Depends(get_current_user_info),
):
    """List all servers with detailed information for the current project."""
    servers = nova.list_servers(project_id=user_info["project_id"])
    return {
        "servers": [Server.from_db_model(server).model_dump() for server in servers]
    }


@router.get("/servers/{server_identifier}")
async def get_server(
    server_identifier: str,
    nova: NovaService = Depends(get_nova_service),
    user_info: dict = Depends(get_current_user_info),
):
    """Get server by ID or name."""
    server = nova._resolve_server(server_identifier, user_info["project_id"])
    if not server:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Server not found"
        )

    # Check if user has access to this server
    if server.project_id != user_info["project_id"]:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Server not found"
        )

    return {"server": Server.from_db_model(server).model_dump()}


@router.put("/servers/{server_identifier}")
async def update_server(
    request: Request,
    server_identifier: str,
    server_request: ServerUpdateRequest,
    nova: NovaService = Depends(get_nova_service),
    user_info: dict = Depends(get_current_user_info),
):
    """Update server by ID or name."""
    updated_server = nova.update_server(
        server_identifier, server_request.server, user_info["project_id"]
    )
    if not updated_server:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Server not found"
        )

    # Check if user has access to this server
    if updated_server.project_id != user_info["project_id"]:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Server not found"
        )

    port = request.url.port or 8774
    base_url = f"http://localhost:{port}"

    server_data = Server.from_db_model(updated_server).model_dump()
    server_data["links"] = [
        {"rel": "self", "href": f"{base_url}/v2.1/servers/{updated_server.id}"}
    ]

    return {"server": server_data}


@router.delete("/servers/{server_identifier}")
async def delete_server(
    server_identifier: str,
    nova: NovaService = Depends(get_nova_service),
    user_info: dict = Depends(get_current_user_info),
):
    """Delete server by ID or name."""
    success = nova.delete_server(server_identifier, user_info["project_id"])
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Server not found"
        )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# Server actions
@router.post("/servers/{server_identifier}/action")
async def server_action(
    server_identifier: str,
    action_data: dict,
    nova: NovaService = Depends(get_nova_service),
    user_info: dict = Depends(get_current_user_info),
):
    """Perform action on server."""
    # Check server exists and user has access
    server = nova._resolve_server(server_identifier, user_info["project_id"])
    if not server or server.project_id != user_info["project_id"]:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Server not found"
        )

    # Handle different action types
    if "reboot" in action_data:
        reboot_type = action_data["reboot"].get("type", "SOFT")
        success = nova.reboot_server(
            server_identifier, reboot_type, user_info["project_id"]
        )
    elif "os-start" in action_data:
        success = nova.start_server(server_identifier, user_info["project_id"])
    elif "os-stop" in action_data:
        success = nova.stop_server(server_identifier, user_info["project_id"])
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported server action"
        )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Server not found"
        )

    return Response(status_code=status.HTTP_202_ACCEPTED)


# Key pair endpoints
@router.post("/os-keypairs")
async def create_keypair(
    keypair_request: KeyPairCreateRequest,
    nova: NovaService = Depends(get_nova_service),
    user_info: dict = Depends(get_current_user_info),
):
    """Create a new key pair."""
    db_keypair = nova.create_keypair(keypair_request.keypair, user_info["user_id"])
    return {"keypair": KeyPair.model_validate(db_keypair).model_dump()}


@router.get("/os-keypairs")
async def list_keypairs(
    nova: NovaService = Depends(get_nova_service),
    user_info: dict = Depends(get_current_user_info),
):
    """List key pairs for the current user."""
    keypairs = nova.list_keypairs(user_info["user_id"])
    return {
        "keypairs": [
            {"keypair": KeyPair.model_validate(kp).model_dump()} for kp in keypairs
        ]
    }


@router.get("/os-keypairs/{keypair_name}")
async def get_keypair(
    keypair_name: str,
    nova: NovaService = Depends(get_nova_service),
    user_info: dict = Depends(get_current_user_info),
):
    """Get key pair by name."""
    keypair = nova.get_keypair(keypair_name, user_info["user_id"])
    if not keypair:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Key pair not found"
        )
    return {"keypair": KeyPair.model_validate(keypair).model_dump()}


@router.delete("/os-keypairs/{keypair_name}")
async def delete_keypair(
    keypair_name: str,
    nova: NovaService = Depends(get_nova_service),
    user_info: dict = Depends(get_current_user_info),
):
    """Delete key pair by name."""
    success = nova.delete_keypair(keypair_name, user_info["user_id"])
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Key pair not found"
        )
    return Response(status_code=status.HTTP_202_ACCEPTED)
