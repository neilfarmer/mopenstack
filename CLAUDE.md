# MockOpenStack Development Configuration

## Project Context
This is MockOpenStack (mopenstack) - a local mock environment for OpenStack APIs, similar to LocalStack for AWS. It enables testing infrastructure-as-code tools and OpenStack applications locally without requiring a full OpenStack deployment.

## Architecture Overview
- **Language**: Python 3.9+ with FastAPI
- **Database**: SQLite (dev) / PostgreSQL (prod)
- **Containerization**: Docker + docker-compose
- **Testing**: pytest with comprehensive coverage

## Key Services Implementation
1. **Keystone** - Identity and authentication service
2. **Nova** - Compute service for instance management  
3. **Neutron** - Networking service for networks, subnets, security groups (no floating IPs)
4. **Glance** - Image service for VM image metadata
5. **Cinder** - Block storage for volumes
6. **Swift** - Object storage service
7. **Octavia** - Load balancer service
8. **Designate** - DNS service

## Development Commands
```bash
# Install dependencies
poetry install

# Start development environment
docker-compose up -d

# Run the application directly
poetry run mopenstack

# Bootstrap with default data
poetry run mopenstack-bootstrap

# Run tests
poetry run pytest

# Format code
poetry run black mopenstack/ tests/
poetry run isort mopenstack/ tests/

# Type checking
poetry run mypy mopenstack/

# Lint code  
poetry run flake8 mopenstack/ tests/
```

## Project Structure
```
mopenstack/
├── mopenstack/           # Main application code
│   ├── services/         # OpenStack service implementations
│   ├── models/           # Database models
│   ├── auth/            # Authentication and authorization
│   ├── common/          # Shared utilities and base classes
│   └── main.py          # FastAPI application entry point
├── tests/               # Test suite
├── docker/              # Docker configuration
├── docs/                # Documentation
└── examples/            # Usage examples and demos
```

## API Compatibility Goals
- Full compatibility with OpenStack APIs
- Support for Terraform OpenStack provider
- Compatible with OpenStackSDK and python-openstackclient
- Proper HTTP status codes and error responses
- Standard OpenStack authentication flows

## Testing Strategy
- Unit tests for all service implementations
- Integration tests with popular IaC tools (Terraform, Ansible)
- API compatibility validation against OpenStack specifications
- Performance and load testing
- Docker container testing

## Development Guidelines
- Follow OpenStack API specifications exactly
- Maintain backward compatibility
- Comprehensive logging for debugging
- Clear error messages and proper HTTP status codes
- Modular design for easy service addition/removal

## Code Quality Standards
- **Zero Warnings Policy**: All code must pass tests without warnings
- **Modern Python**: Use latest stable features, avoid deprecated APIs
- **Type Safety**: Full type hints with mypy validation
- **Code Formatting**: Black + isort for consistent style

## Warning Prevention Guidelines

### Pydantic Models
```python
# ✅ Use modern ConfigDict instead of Config class
from pydantic import BaseModel, ConfigDict

class MyModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
# ✅ Use model_dump() instead of .dict()
data = model.model_dump()

# ✅ Use model_validate() instead of from_orm()
instance = MyModel.model_validate(db_object)
```

### DateTime Handling
```python
# ✅ Use timezone-aware datetime
from datetime import datetime, timezone

expire_time = datetime.now(timezone.utc) + timedelta(hours=24)

# ❌ Avoid deprecated utcnow()
# expire_time = datetime.utcnow() + timedelta(hours=24)
```

### SQLAlchemy Imports
```python
# ✅ Use modern declarative_base import
from sqlalchemy.orm import declarative_base

# ❌ Avoid deprecated import
# from sqlalchemy.ext.declarative import declarative_base
```

### Test Functions
```python
# ✅ Test functions should not return values
def test_something(client):
    result = client.get("/endpoint")
    assert result.status_code == 200
    # Don't return anything

# ❌ Avoid returning from test functions
# return result.headers.get("token")
```

### Warning Suppression
For unavoidable third-party warnings, use pytest configuration:
```toml
[tool.pytest.ini_options]
filterwarnings = [
    "ignore::pydantic.warnings.PydanticDeprecatedSince20",
    "ignore::DeprecationWarning:pydantic._internal._config",
]
```

## Pre-commit Checklist
Before any commit, ensure:
1. `make test` - All tests pass with zero warnings
2. `make lint` - Code passes all linting checks
3. `make type-check` - MyPy validation succeeds
4. `make format` - Code is properly formatted