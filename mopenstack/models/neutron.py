"""Neutron (Networking Service) database models."""

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


class Network(Base):
    """Network model for Neutron."""

    __tablename__ = "networks"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False)
    description = Column(Text)
    status = Column(String, default="ACTIVE", nullable=False)
    admin_state_up = Column(Boolean, default=True, nullable=False)
    shared = Column(Boolean, default=False, nullable=False)
    external = Column(Boolean, default=False, nullable=False)

    # Ownership
    project_id = Column(String, nullable=False)

    # Network type (flat, vlan, vxlan, etc.)
    network_type = Column(String, default="flat")
    physical_network = Column(String)
    segmentation_id = Column(Integer)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    subnets = relationship("Subnet", back_populates="network")
    ports = relationship("Port", back_populates="network")


class Subnet(Base):
    """Subnet model for Neutron."""

    __tablename__ = "subnets"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False)
    description = Column(Text)
    network_id = Column(String, ForeignKey("networks.id"), nullable=False)
    project_id = Column(String, nullable=False)

    # IP configuration
    cidr = Column(String, nullable=False)  # e.g., "192.168.1.0/24"
    ip_version = Column(Integer, default=4, nullable=False)
    gateway_ip = Column(String)
    enable_dhcp = Column(Boolean, default=True, nullable=False)

    # DNS and allocation pools
    dns_nameservers = Column(JSON, default=list)
    allocation_pools = Column(JSON, default=list)
    host_routes = Column(JSON, default=list)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    network = relationship("Network", back_populates="subnets")


class Port(Base):
    """Port model for Neutron."""

    __tablename__ = "ports"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String)
    description = Column(Text)
    network_id = Column(String, ForeignKey("networks.id"), nullable=False)
    project_id = Column(String, nullable=False)

    # Port configuration
    mac_address = Column(String, nullable=False)
    status = Column(
        String, default="DOWN", nullable=False
    )  # ACTIVE, DOWN, BUILD, ERROR
    admin_state_up = Column(Boolean, default=True, nullable=False)

    # Device attachment
    device_id = Column(String)  # Server UUID if attached
    device_owner = Column(String)  # compute:nova, network:router_interface, etc.

    # IP allocation
    fixed_ips = Column(
        JSON, default=list
    )  # [{"subnet_id": "...", "ip_address": "..."}]

    # Security groups
    security_groups = Column(JSON, default=list)  # List of security group IDs

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    network = relationship("Network", back_populates="ports")


class SecurityGroup(Base):
    """Security Group model for Neutron."""

    __tablename__ = "security_groups"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False)
    description = Column(Text)
    project_id = Column(String, nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    rules = relationship("SecurityGroupRule", back_populates="security_group")


class SecurityGroupRule(Base):
    """Security Group Rule model for Neutron."""

    __tablename__ = "security_group_rules"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    security_group_id = Column(String, ForeignKey("security_groups.id"), nullable=False)

    # Rule configuration
    direction = Column(String, nullable=False)  # ingress, egress
    ethertype = Column(String, default="IPv4", nullable=False)  # IPv4, IPv6
    protocol = Column(String)  # tcp, udp, icmp, etc.
    port_range_min = Column(Integer)
    port_range_max = Column(Integer)
    remote_ip_prefix = Column(String)  # CIDR
    remote_group_id = Column(String)  # Reference to another security group

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    security_group = relationship("SecurityGroup", back_populates="rules")
