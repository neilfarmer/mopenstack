# MockOpenStack

A local mock environment for OpenStack APIs, similar to LocalStack for AWS.

## Overview

MockOpenStack provides a lightweight, local implementation of OpenStack APIs that enables developers to:
- Test infrastructure-as-code tools locally
- Develop OpenStack applications without a full deployment
- Simulate OpenStack environments for CI/CD pipelines
- Learn OpenStack APIs without complex setup

## Quick Start

```bash
# Install dependencies and set up environment
make quick-start

# Start the development server (handles port conflicts automatically)
make run

# If port 5000 is in use, kill conflicts and run
make run-clean

# Or run with Docker
make docker-run
```

### Troubleshooting

**Port 5000 in use error:**
```bash
# Check what's using port 5000
make check-port

# Kill processes using port 5000
make kill-port

# Then run normally
make run
```

**bcrypt version warnings:**
These are suppressed automatically but if you see them, update dependencies:
```bash
poetry lock --no-update
poetry install
```

## Supported Services

- **Keystone** (Identity) - Authentication and authorization
- **Nova** (Compute) - Instance management
- **Neutron** (Network) - Networking and security groups
- **Glance** (Image) - Image metadata management
- **Cinder** (Block Storage) - Volume management
- **Swift** (Object Storage) - Object storage operations
- **Octavia** (Load Balancer) - Load balancing services
- **Designate** (DNS) - DNS management

## Default Credentials

- **Username**: admin
- **Password**: password  
- **Project**: admin

## API Endpoints

- Identity (Keystone): http://localhost:5000/v3
- API Documentation: http://localhost:5000/docs
- Health Check: http://localhost:5000/health

## Development

```bash
# Set up development environment
make dev-setup

# Run tests
make test

# Code formatting and linting
make format
make lint

# Type checking
make type-check
```

## Docker

```bash
# Build and run with Docker
make docker-build
make docker-run

# View logs
make docker-logs

# Stop and clean up
make docker-stop
```

## Contributing

This project uses Poetry for dependency management and Make for task automation.

See `make help` for all available commands.