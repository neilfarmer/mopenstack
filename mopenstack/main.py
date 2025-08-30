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
from .models import keystone  # noqa: F401

# Import service routers
from .services.keystone.router import router as keystone_router

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
            f"⚠️  Port {original_port} is in use. "
            f"Starting on port {port} instead."
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
