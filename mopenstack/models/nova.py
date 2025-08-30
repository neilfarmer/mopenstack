"""Nova (Compute Service) database models."""

import uuid

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from ..common.database import Base


class Flavor(Base):
    """Flavor model for Nova."""

    __tablename__ = "flavors"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, unique=True, nullable=False)
    vcpus = Column(Integer, nullable=False)
    ram = Column(Integer, nullable=False)  # MB
    disk = Column(Integer, nullable=False)  # GB
    ephemeral = Column(Integer, default=0)  # GB
    swap = Column(Integer, default=0)  # MB
    public = Column(Boolean, default=True, nullable=False)
    disabled = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    servers = relationship("Server", back_populates="flavor")


class Server(Base):
    """Server (Instance) model for Nova."""

    __tablename__ = "servers"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False)
    status = Column(
        String, default="BUILD", nullable=False
    )  # BUILD, ACTIVE, SHUTOFF, ERROR, etc.
    power_state = Column(String, default="NOSTATE", nullable=False)
    task_state = Column(String)  # spawning, rebooting, etc.
    vm_state = Column(String, default="building", nullable=False)

    # Resource configuration
    flavor_id = Column(String, ForeignKey("flavors.id"), nullable=False)
    image_id = Column(String, nullable=False)  # Reference to Glance image

    # Ownership
    user_id = Column(String, nullable=False)
    project_id = Column(String, nullable=False)

    # Metadata and configuration
    server_metadata = Column(JSON, default=dict)
    config_drive = Column(Boolean, default=False)
    key_name = Column(String)  # SSH key pair name

    # Networking (simplified)
    networks = Column(JSON, default=list)  # List of network attachments

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    launched_at = Column(DateTime(timezone=True))
    terminated_at = Column(DateTime(timezone=True))

    # Relationships
    flavor = relationship("Flavor", back_populates="servers")


class KeyPair(Base):
    """SSH Key Pair model for Nova."""

    __tablename__ = "keypairs"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False)
    user_id = Column(String, nullable=False)
    public_key = Column(Text, nullable=False)
    fingerprint = Column(String, nullable=False)
    type = Column(String, default="ssh", nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
