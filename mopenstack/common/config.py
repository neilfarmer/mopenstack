"""Configuration management for MockOpenStack."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings."""

    debug: bool = False
    database_url: str = "sqlite:///./mopenstack.db"
    secret_key: str = "mock-openstack-secret-key-change-in-production"

    # Service endpoints
    keystone_port: int = 5000
    nova_port: int = 8774
    neutron_port: int = 9696
    glance_port: int = 9292
    cinder_port: int = 8776
    swift_port: int = 8080
    octavia_port: int = 9876
    designate_port: int = 9001

    # Default admin credentials
    admin_username: str = "admin"
    admin_password: str = "password"
    admin_project: str = "admin"

    class Config:
        env_file = ".env"


settings = Settings()
