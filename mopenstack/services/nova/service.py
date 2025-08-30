"""Nova service implementation."""

import hashlib
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from ...models.nova import Flavor, KeyPair, Server
from .schemas import FlavorCreate, KeyPairCreate, ServerCreate, ServerUpdate


class NovaService:
    """Nova Compute Service implementation."""

    def __init__(self, db: Session):
        self.db = db

    # Flavor operations
    def create_flavor(self, flavor_data: FlavorCreate) -> Flavor:
        """Create a new flavor."""
        # Check if flavor name already exists
        existing = self.db.query(Flavor).filter(Flavor.name == flavor_data.name).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Flavor with name '{flavor_data.name}' already exists",
            )

        db_flavor = Flavor(**flavor_data.model_dump())
        self.db.add(db_flavor)
        self.db.commit()
        self.db.refresh(db_flavor)
        return db_flavor

    def get_flavor(self, flavor_id: str) -> Optional[Flavor]:
        """Get flavor by ID."""
        return self.db.query(Flavor).filter(Flavor.id == flavor_id).first()

    def get_flavor_by_name(self, flavor_name: str) -> Optional[Flavor]:
        """Get flavor by name."""
        return self.db.query(Flavor).filter(Flavor.name == flavor_name).first()

    def _resolve_flavor(self, flavor_identifier: str) -> Optional[Flavor]:
        """Resolve flavor by ID or name."""
        flavor = self.get_flavor(flavor_identifier)
        if not flavor:
            flavor = self.get_flavor_by_name(flavor_identifier)
        return flavor

    def list_flavors(self, disabled: Optional[bool] = None) -> List[Flavor]:
        """List all flavors."""
        query = self.db.query(Flavor)
        if disabled is not None:
            query = query.filter(Flavor.disabled == disabled)
        return query.all()

    def delete_flavor(self, flavor_identifier: str) -> bool:
        """Delete a flavor by ID or name."""
        db_flavor = self._resolve_flavor(flavor_identifier)
        if not db_flavor:
            return False

        # Check if flavor is in use by any servers
        servers_using_flavor = (
            self.db.query(Server).filter(Server.flavor_id == db_flavor.id).first()
        )
        if servers_using_flavor:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Flavor '{db_flavor.name}' is in use by existing servers",
            )

        self.db.delete(db_flavor)
        self.db.commit()
        return True

    # Server operations
    def create_server(
        self, server_data: ServerCreate, user_id: str, project_id: str
    ) -> Server:
        """Create a new server."""
        # Validate flavor exists
        flavor = self._resolve_flavor(server_data.flavor_ref)
        if not flavor:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Flavor '{server_data.flavor_ref}' not found",
            )

        # For mock service, we don't validate image exists
        # In real OpenStack, this would check Glance
        if not server_data.image_ref:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Image reference is required",
            )

        # Create server record
        server_dict = server_data.model_dump()
        server_dict.update(
            {
                "user_id": user_id,
                "project_id": project_id,
                "status": "BUILD",
                "power_state": "NOSTATE",
                "task_state": "spawning",
                "vm_state": "building",
                "image_id": server_data.image_ref,
                "flavor_id": flavor.id,
                "server_metadata": server_data.metadata or {},
                "networks": server_data.networks or [],
            }
        )

        # Remove API field names that don't match DB model
        server_dict.pop("image_ref", None)
        server_dict.pop("flavor_ref", None)
        server_dict.pop("metadata", None)
        # Remove API-only fields that aren't in the database model
        server_dict.pop("min_count", None)
        server_dict.pop("max_count", None)

        db_server = Server(**server_dict)
        self.db.add(db_server)
        self.db.commit()
        self.db.refresh(db_server)

        # Simulate server boot process (in real implementation, this would be async)
        self._simulate_server_boot(db_server)

        return db_server

    def _simulate_server_boot(self, server: Server) -> None:
        """Simulate the server boot process."""
        # In a real implementation, this would be handled by a background task
        # For the mock, we'll just update the server to ACTIVE state immediately
        server.status = "ACTIVE"
        server.power_state = "Running"
        server.task_state = None
        server.vm_state = "active"
        server.launched_at = datetime.now(timezone.utc)
        self.db.commit()

    def get_server(self, server_id: str) -> Optional[Server]:
        """Get server by ID."""
        return self.db.query(Server).filter(Server.id == server_id).first()

    def get_server_by_name(self, server_name: str, project_id: str) -> Optional[Server]:
        """Get server by name within a project."""
        return (
            self.db.query(Server)
            .filter(Server.name == server_name, Server.project_id == project_id)
            .first()
        )

    def _resolve_server(
        self, server_identifier: str, project_id: Optional[str] = None
    ) -> Optional[Server]:
        """Resolve server by ID or name."""
        server = self.get_server(server_identifier)
        if not server and project_id:
            server = self.get_server_by_name(server_identifier, project_id)
        return server

    def list_servers(
        self, project_id: Optional[str] = None, user_id: Optional[str] = None
    ) -> List[Server]:
        """List servers, optionally filtered by project or user."""
        query = self.db.query(Server)
        if project_id:
            query = query.filter(Server.project_id == project_id)
        if user_id:
            query = query.filter(Server.user_id == user_id)
        return query.all()

    def update_server(
        self,
        server_identifier: str,
        server_data: ServerUpdate,
        project_id: Optional[str] = None,
    ) -> Optional[Server]:
        """Update a server."""
        db_server = self._resolve_server(server_identifier, project_id)
        if not db_server:
            return None

        # Update only provided fields
        update_data = server_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_server, field, value)

        self.db.commit()
        self.db.refresh(db_server)
        return db_server

    def delete_server(
        self, server_identifier: str, project_id: Optional[str] = None
    ) -> bool:
        """Delete a server."""
        db_server = self._resolve_server(server_identifier, project_id)
        if not db_server:
            return False

        # Mark as deleting, then remove
        db_server.status = "DELETING"
        db_server.task_state = "deleting"
        db_server.terminated_at = datetime.now(timezone.utc)
        self.db.commit()

        # In real OpenStack, cleanup would be async
        # For mock, we'll delete immediately
        self.db.delete(db_server)
        self.db.commit()
        return True

    # Server actions
    def reboot_server(
        self,
        server_identifier: str,
        reboot_type: str = "SOFT",
        project_id: Optional[str] = None,
    ) -> bool:
        """Reboot a server."""
        db_server = self._resolve_server(server_identifier, project_id)
        if not db_server:
            return False

        if db_server.status != "ACTIVE":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Server must be in ACTIVE state to reboot (current: {db_server.status})",
            )

        # Simulate reboot
        db_server.task_state = "rebooting"
        self.db.commit()

        # In real implementation, this would be async
        db_server.task_state = None
        db_server.power_state = "Running"
        self.db.commit()

        return True

    def start_server(
        self, server_identifier: str, project_id: Optional[str] = None
    ) -> bool:
        """Start a server."""
        db_server = self._resolve_server(server_identifier, project_id)
        if not db_server:
            return False

        if db_server.status not in ["SHUTOFF", "STOPPED"]:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Server must be in SHUTOFF state to start (current: {db_server.status})",
            )

        db_server.status = "ACTIVE"
        db_server.power_state = "Running"
        db_server.vm_state = "active"
        db_server.task_state = None
        self.db.commit()

        return True

    def stop_server(
        self, server_identifier: str, project_id: Optional[str] = None
    ) -> bool:
        """Stop a server."""
        db_server = self._resolve_server(server_identifier, project_id)
        if not db_server:
            return False

        if db_server.status != "ACTIVE":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Server must be in ACTIVE state to stop (current: {db_server.status})",
            )

        db_server.status = "SHUTOFF"
        db_server.power_state = "Shutdown"
        db_server.vm_state = "stopped"
        db_server.task_state = None
        self.db.commit()

        return True

    # Key pair operations
    def create_keypair(self, keypair_data: KeyPairCreate, user_id: str) -> KeyPair:
        """Create a new key pair."""
        # Check if keypair name already exists for this user
        existing = (
            self.db.query(KeyPair)
            .filter(KeyPair.name == keypair_data.name, KeyPair.user_id == user_id)
            .first()
        )
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Key pair with name '{keypair_data.name}' already exists",
            )

        # Generate a mock fingerprint if public key is provided
        fingerprint = "mock:fingerprint"
        if keypair_data.public_key:
            fingerprint = hashlib.md5(keypair_data.public_key.encode()).hexdigest()
            fingerprint = ":".join(
                [fingerprint[i : i + 2] for i in range(0, len(fingerprint), 2)]
            )

        db_keypair = KeyPair(
            name=keypair_data.name,
            user_id=user_id,
            public_key=keypair_data.public_key or "mock-public-key",
            fingerprint=fingerprint,
            type=keypair_data.type,
        )
        self.db.add(db_keypair)
        self.db.commit()
        self.db.refresh(db_keypair)
        return db_keypair

    def get_keypair(self, keypair_name: str, user_id: str) -> Optional[KeyPair]:
        """Get key pair by name and user."""
        return (
            self.db.query(KeyPair)
            .filter(KeyPair.name == keypair_name, KeyPair.user_id == user_id)
            .first()
        )

    def list_keypairs(self, user_id: str) -> List[KeyPair]:
        """List key pairs for a user."""
        return self.db.query(KeyPair).filter(KeyPair.user_id == user_id).all()

    def delete_keypair(self, keypair_name: str, user_id: str) -> bool:
        """Delete a key pair."""
        db_keypair = self.get_keypair(keypair_name, user_id)
        if not db_keypair:
            return False

        self.db.delete(db_keypair)
        self.db.commit()
        return True
