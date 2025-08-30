"""Main FastAPI application for MockOpenStack."""

import io
import os
import sys
import warnings

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Suppress bcrypt warnings during runtime
warnings.filterwarnings("ignore", category=UserWarning)
warnings.filterwarnings("ignore", category=DeprecationWarning)
os.environ["PYTHONWARNINGS"] = "ignore"

# Fix bcrypt version detection issue
def fix_bcrypt_version():
    """Fix bcrypt version detection for passlib compatibility."""
    try:
        import bcrypt
        if not hasattr(bcrypt, '__about__'):
            # Create a mock __about__ module with version
            class MockAbout:
                __version__ = getattr(bcrypt, '__version__', '4.0.0')
            bcrypt.__about__ = MockAbout()
    except ImportError:
        pass

# Apply bcrypt fix before any imports
fix_bcrypt_version()

# Capture stderr to suppress bcrypt messages during imports
original_stderr = sys.stderr
captured_stderr = io.StringIO()
sys.stderr = captured_stderr

try:
    from .common.config import settings
    from .common.database import Base, engine
finally:
    sys.stderr = original_stderr

# Import models to ensure they're registered
from .models import keystone, nova  # noqa: F401

# Import service routers
from .services.keystone.router import router as keystone_router
from .services.nova.router import router as nova_router

# Create database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="MockOpenStack",
    description="A local mock environment for OpenStack APIs",
    version="0.1.0",
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include service routers
app.include_router(keystone_router, prefix="/v3", tags=["identity"])
app.include_router(nova_router, prefix="/v2.1", tags=["compute"])

# Add basic Glance endpoints for CLI compatibility
from fastapi import APIRouter, HTTPException, status as http_status
glance_router = APIRouter()

# Mock image database with proper UUIDs
MOCK_IMAGES = {
    "3394d42a-9583-4c79-9a1b-7bb94ae7dc04": {
        "id": "3394d42a-9583-4c79-9a1b-7bb94ae7dc04",
        "name": "ubuntu-22",
        "status": "active",
        "visibility": "public",
        "container_format": "bare",
        "disk_format": "qcow2",
        "size": 2361393152,
        "created_at": "2025-01-01T00:00:00Z",
        "updated_at": "2025-01-01T00:00:00Z"
    },
    "c8b1e50a-3c91-4d2e-a5f6-8f7b2a9c1d3e": {
        "id": "c8b1e50a-3c91-4d2e-a5f6-8f7b2a9c1d3e", 
        "name": "centos-8",
        "status": "active",
        "visibility": "public",
        "container_format": "bare",
        "disk_format": "qcow2",
        "size": 1073741824,
        "created_at": "2025-01-01T00:00:00Z",
        "updated_at": "2025-01-01T00:00:00Z"
    },
    "f2e4d6c8-1a3b-4c5d-9e7f-2b8d4c6e8f0a": {
        "id": "f2e4d6c8-1a3b-4c5d-9e7f-2b8d4c6e8f0a",
        "name": "debian-12",
        "status": "active", 
        "visibility": "public",
        "container_format": "bare",
        "disk_format": "qcow2",
        "size": 805306368,
        "created_at": "2025-01-01T00:00:00Z",
        "updated_at": "2025-01-01T00:00:00Z"
    }
}

# Name to UUID mapping for backward compatibility
IMAGE_NAME_MAP = {
    "ubuntu-22.04": "3394d42a-9583-4c79-9a1b-7bb94ae7dc04",
    "centos-8": "c8b1e50a-3c91-4d2e-a5f6-8f7b2a9c1d3e", 
    "debian-12": "f2e4d6c8-1a3b-4c5d-9e7f-2b8d4c6e8f0a"
}

@glance_router.get("/images")
async def list_images(name: str = None):
    """Mock image listing for CLI compatibility."""
    images = list(MOCK_IMAGES.values())
    
    # Filter by name if provided
    if name:
        images = [img for img in images if img["name"].lower() == name.lower() or name in IMAGE_NAME_MAP]
        
    return {"images": images}

@glance_router.get("/images/{image_id}")
async def get_image(image_id: str):
    """Mock get image endpoint."""
    # Check if it's a UUID
    if image_id in MOCK_IMAGES:
        return MOCK_IMAGES[image_id]
    
    # Check if it's a name alias
    if image_id in IMAGE_NAME_MAP:
        uuid = IMAGE_NAME_MAP[image_id]
        return MOCK_IMAGES[uuid]
    
    # Not found
    raise HTTPException(
        status_code=http_status.HTTP_404_NOT_FOUND,
        detail=f"Image {image_id} not found"
    )

app.include_router(glance_router, prefix="/v2", tags=["image"])


@app.get("/")
async def root():
    """Root endpoint returning service information."""
    return {
        "name": "MockOpenStack",
        "version": "0.1.0",
        "description": "Local mock environment for OpenStack APIs",
        "services": {
            "keystone": f"http://localhost:{settings.keystone_port}/v3",
            "nova": f"http://localhost:{settings.nova_port}/v2.1",
            "neutron": f"http://localhost:{settings.neutron_port}/v2.0",
            "glance": f"http://localhost:{settings.glance_port}/v2",
            "cinder": f"http://localhost:{settings.cinder_port}/v3",
            "swift": f"http://localhost:{settings.swift_port}/v1",
            "octavia": f"http://localhost:{settings.octavia_port}/v2",
            "designate": f"http://localhost:{settings.designate_port}/v2",
        },
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok"}


def main():
    """Main entry point for the application."""
    import socket

    port = settings.keystone_port

    # Check if port is available, find alternative if not
    def find_free_port(start_port: int) -> int:
        for port_attempt in range(start_port, start_port + 100):
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                try:
                    s.bind(("0.0.0.0", port_attempt))
                    return port_attempt
                except OSError:
                    continue
        raise RuntimeError(f"No free ports found starting from {start_port}")

    try:
        # Test if the default port is available
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(("0.0.0.0", port))
    except OSError:
        # Port is in use, find a free one
        original_port = port
        port = find_free_port(port + 1)
        print(
            f"⚠️  Port {original_port} is in use. " f"Starting on port {port} instead."
        )
        print(f"🌐 MockOpenStack will be available at: http://localhost:{port}")
        print(f"📚 API documentation at: http://localhost:{port}/docs")

    uvicorn.run(
        "mopenstack.main:app",
        host="0.0.0.0",
        port=port,
        reload=settings.debug,
    )


if __name__ == "__main__":
    main()
