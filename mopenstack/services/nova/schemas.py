"""Nova API schemas for request/response validation."""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class FlavorBase(BaseModel):
    """Base flavor schema."""

    name: str
    vcpus: int = Field(gt=0, description="Number of VCPUs (must be positive)")
    ram: int = Field(gt=0, description="RAM in MB (must be positive)")
    disk: int = Field(ge=0, description="Disk size in GB (must be non-negative)")
    ephemeral: int = Field(ge=0, default=0, description="Ephemeral disk in GB")
    swap: int = Field(ge=0, default=0, description="Swap space in MB")
    public: bool = True


class FlavorCreate(FlavorBase):
    """Schema for creating a flavor."""

    pass


class Flavor(FlavorBase):
    """Complete flavor schema with generated fields."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    disabled: bool
    created_at: datetime
    updated_at: Optional[datetime] = None


class FlavorCreateRequest(BaseModel):
    """Wrapper for flavor creation requests."""

    flavor: FlavorCreate


class ServerBase(BaseModel):
    """Base server schema."""

    name: str = Field(min_length=1, description="Server name (required)")
    image_ref: str = Field(default="", alias="imageRef")
    flavor_ref: str = Field(default="", alias="flavorRef")
    key_name: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    networks: Optional[List[Dict[str, Any]]] = None
    config_drive: bool = False
    
    # Additional fields that OpenStack CLI may send
    min_count: Optional[int] = 1
    max_count: Optional[int] = 1
    
    model_config = ConfigDict(populate_by_name=True)


class ServerCreate(ServerBase):
    """Schema for creating a server."""

    image_ref: str = Field(min_length=1, alias="imageRef", description="Image reference (required)")
    flavor_ref: str = Field(min_length=1, alias="flavorRef", description="Flavor reference (required)")


class ServerUpdate(BaseModel):
    """Schema for updating a server."""

    name: Optional[str] = None


class Server(ServerBase):
    """Complete server schema with generated fields."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    status: str
    power_state: str
    task_state: Optional[str] = None
    vm_state: str
    user_id: str
    project_id: str
    created_at: datetime
    updated_at: Optional[datetime] = None
    launched_at: Optional[datetime] = None
    terminated_at: Optional[datetime] = None
    
    # Additional fields for OpenStack CLI compatibility
    tenant_id: Optional[str] = None
    image: Optional[Dict[str, Any]] = None
    flavor: Optional[Dict[str, Any]] = None
    created: Optional[datetime] = None  # Alias for created_at
    updated: Optional[datetime] = None  # Alias for updated_at

    # For API response, we'll map model fields
    @classmethod
    def from_db_model(cls, server_model, flavor_model=None):
        """Convert database model to API response format."""
        # Handle potential None values properly
        metadata = server_model.server_metadata if server_model.server_metadata is not None else {}
        networks = server_model.networks if server_model.networks is not None else []
        
        data = {
            "id": server_model.id,
            "name": server_model.name,
            "status": server_model.status,
            "power_state": server_model.power_state,
            "task_state": server_model.task_state,
            "vm_state": server_model.vm_state,
            "user_id": server_model.user_id,
            "project_id": server_model.project_id,
            "created_at": server_model.created_at,
            "updated_at": server_model.updated_at,
            "launched_at": server_model.launched_at,
            "terminated_at": server_model.terminated_at,
            "image_ref": server_model.image_id or "",
            "flavor_ref": server_model.flavor_id or "",
            "key_name": server_model.key_name,
            "metadata": metadata,
            "networks": networks,
            "config_drive": server_model.config_drive,
            # Add OpenStack CLI compatibility fields
            "created": server_model.created_at,  # Alias for created_at
            "updated": server_model.updated_at,  # Alias for updated_at
            "tenant_id": server_model.project_id,  # Alias for project_id
            "image": {"id": server_model.image_id} if server_model.image_id else None,
            "flavor": {"id": server_model.flavor_id} if server_model.flavor_id else None,
        }
        return cls.model_validate(data)


class ServerCreateRequest(BaseModel):
    """Wrapper for server creation requests."""

    server: ServerCreate


class ServerUpdateRequest(BaseModel):
    """Wrapper for server update requests."""

    server: ServerUpdate


class ServerAction(BaseModel):
    """Base schema for server actions."""

    pass


class ServerReboot(ServerAction):
    """Schema for server reboot action."""

    type: str = "SOFT"  # SOFT or HARD


class ServerStart(ServerAction):
    """Schema for server start action."""

    pass


class ServerStop(ServerAction):
    """Schema for server stop action."""

    pass


class ServerDelete(ServerAction):
    """Schema for server delete action."""

    pass


class KeyPairBase(BaseModel):
    """Base key pair schema."""

    name: str = Field(min_length=1, description="Key pair name (required)")
    public_key: Optional[str] = None
    type: str = Field(default="ssh", pattern="^(ssh|x509|rsa)$", description="Key type (ssh, x509, or rsa)")


class KeyPairCreate(KeyPairBase):
    """Schema for creating a key pair."""

    pass


class KeyPair(KeyPairBase):
    """Complete key pair schema."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    fingerprint: str
    created_at: datetime


class KeyPairCreateRequest(BaseModel):
    """Wrapper for key pair creation requests."""

    keypair: KeyPairCreate
