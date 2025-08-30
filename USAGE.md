# MockOpenStack Usage Guide

This guide demonstrates how to use MockOpenStack with the OpenStack CLI to manage mock cloud resources.

## Quick Start

1. **Install and start MockOpenStack:**

   ```bash
   make quick-start
   make run
   ```

   **Note**: If port 5000 is in use, MockOpenStack will automatically start on the next available port (e.g., 5001, 5002). Check the startup message for the actual port.

2. **Install OpenStack CLI:**

   ```bash
   pip install python-openstackclient
   ```

3. **Set environment variables (adjust port if needed):**

   ```bash
   # If MockOpenStack is running on port 5000 (default)
   export OS_AUTH_URL=http://localhost:5000/v3

   # If MockOpenStack is running on a different port (check startup message)
   # export OS_AUTH_URL=http://localhost:5001/v3  # or 5002, etc.

   export OS_PROJECT_NAME=admin
   export OS_USERNAME=admin
   export OS_PASSWORD=password
   export OS_PROJECT_DOMAIN_NAME=Default
   export OS_USER_DOMAIN_NAME=Default
   export OS_IDENTITY_API_VERSION=3
   ```

## Authentication

### Get Authentication Token

```bash
# Get an authentication token
openstack token issue

# Example output:
# +------------+---------------------------------------------------------+
# | Field      | Value                                                   |
# +------------+---------------------------------------------------------+
# | expires    | 2024-01-02T14:30:00+0000                              |
# | id         | gAAAAABltx...                                          |
# | project_id | a1b2c3d4-e5f6-7890-abcd-ef1234567890                  |
# | user_id    | f9e8d7c6-b5a4-3210-9876-543210fedcba                  |
# +------------+---------------------------------------------------------+
```

## Identity Management (Keystone)

### Manage Projects

```bash
# List projects
openstack project list

# Create a new project
openstack project create --description "Development Project" dev-project

# Show project details
openstack project show dev-project

# Update project
openstack project set --description "Updated Development Project" dev-project

# Delete project
openstack project delete dev-project
```

### Manage Users

```bash
# List users
openstack user list

# Create a new user
openstack user create --password secret123 --project admin developer

# Show user details
openstack user show developer

# Update user password
openstack user set --password newsecret123 developer

# Delete user
openstack user delete developer
```

### Manage Roles

```bash
# List roles
openstack role list

# Create a custom role
openstack role create developer

# Assign role to user in project
openstack role add --user developer --project dev-project member

# List role assignments
openstack role assignment list

# Remove role assignment
openstack role remove --user developer --project dev-project member
```

### Manage Domains

```bash
# List domains
openstack domain list

# Create a new domain
openstack domain create --description "Corporate Domain" corp

# Show domain details
openstack domain show corp

# Update domain
openstack domain set --description "Updated Corporate Domain" corp
```

## Service Catalog

````bash
# List available services
openstack service list

## Nova (Compute Service)

### Flavors

Flavors define the compute, memory, and storage capacity of nova computing instances.

```bash
# Create a flavor
openstack flavor create --vcpus 2 --ram 4096 --disk 20 m1.medium

# List all flavors
openstack flavor list

# Show flavor details
openstack flavor show m1.medium

# Delete a flavor
openstack flavor delete m1.medium
````

### Servers (Instances)

```bash
# Create a server (instance)
openstack server create --flavor m1.small --image cirros-0.6.2 --key-name mykey test-instance

# List all servers
openstack server list

# Show server details
openstack server show test-instance

# Update server name
openstack server set --name renamed-instance test-instance

# Server actions
openstack server reboot test-instance
openstack server stop test-instance
openstack server start test-instance

# Delete server
openstack server delete test-instance
```

### Key Pairs

SSH key pairs for server access:

```bash
# Create a key pair
openstack keypair create --public-key ~/.ssh/id_rsa.pub mykey

# List key pairs
openstack keypair list

# Show key pair details
openstack keypair show mykey

# Delete key pair
openstack keypair delete mykey
```

### Images

MockOpenStack provides several pre-configured images with proper UUIDs:

```bash
# List available images
openstack image list

# Show image details by UUID
openstack image show 3394d42a-9583-4c79-9a1b-7bb94ae7dc04

# Show image details by name
openstack image show "ubuntu-22"

# Available images:
# - ubuntu-22 (3394d42a-9583-4c79-9a1b-7bb94ae7dc04)
# - centos-8 (c8b1e50a-3c91-4d2e-a5f6-8f7b2a9c1d3e)
# - debian-12 (f2e4d6c8-1a3b-4c5d-9e7f-2b8d4c6e8f0a)
```

### Example Workflow: Creating and Managing Instances

```bash
# 1. Create a flavor
openstack flavor create --vcpus 1 --ram 1024 --disk 10 test.small

# 2. Create a key pair
openstack keypair create --public-key ~/.ssh/id_rsa.pub test-key

# 3. List available images (note: proper UUIDs are used)
openstack image list

# 4. Create an instance
openstack server create \
  --flavor test.small \
  --image 3394d42a-9583-4c79-9a1b-7bb94ae7dc04 \
  --key-name test-key \
  --property test=value \
  test-server

# Alternative: Create instance using image name
openstack server create \
  --flavor test.small \
  --image "ubuntu-22" \
  --key-name test-key \
  test-server-alt

# 4. Check server status
openstack server list

# 5. Show detailed server information
openstack server show test-server

# 6. Perform server actions
openstack server reboot test-server
openstack server stop test-server
openstack server start test-server

# 7. Clean up
openstack server delete test-server
openstack keypair delete test-key
openstack flavor delete test.small
```

# Show service endpoints

openstack endpoint list

# Get service catalog

openstack catalog list

````

## Advanced Identity Operations

### Token Management

```bash
# Revoke current token
openstack token revoke <token-id>

# Validate token
curl -H "X-Auth-Token: <token>" \
     -H "X-Subject-Token: <token-to-validate>" \
     http://localhost:5000/v3/auth/tokens
````

### Project Hierarchies

```bash
# Create parent project
openstack project create --description "Parent Project" parent-proj

# Create child project
openstack project create --description "Child Project" --parent parent-proj child-proj

# List project hierarchy
openstack project list --long
```

### User Groups

```bash
# Create a group
openstack group create --description "Development Team" dev-team

# Add user to group
openstack group add user dev-team developer

# List group members
openstack group contains user dev-team developer

# Assign role to group
openstack role add --group dev-team --project dev-project member
```

## Testing Infrastructure-as-Code Tools

### Terraform Example

Create a `main.tf` file:

```hcl
terraform {
  required_providers {
    openstack = {
      source = "terraform-provider-openstack/openstack"
    }
  }
}

provider "openstack" {
  auth_url    = "http://localhost:5000/v3"
  tenant_name = "admin"
  user_name   = "admin"
  password    = "password"
  region      = "RegionOne"
  domain_name = "Default"
}

resource "openstack_identity_project_v3" "test_project" {
  name        = "test-terraform"
  description = "Project created by Terraform"
}

resource "openstack_identity_user_v3" "test_user" {
  name               = "terraform-user"
  description        = "User created by Terraform"
  default_project_id = openstack_identity_project_v3.test_project.id
  password           = "terraform123"
}
```

Run Terraform:

```bash
terraform init
terraform plan
terraform apply
```

## Development Workflow

### Testing OpenStack Applications

1. **Start MockOpenStack:**

   ```bash
   make run
   ```

2. **Set up your test environment:**

   ```bash
   source openstack-env.sh  # Your environment file
   ```

3. **Run your application tests:**

   ```bash
   python test_openstack_app.py
   ```

4. **Clean up between tests:**
   ```bash
   make clean
   make bootstrap
   ```

### Continuous Integration

Add MockOpenStack to your CI pipeline:

```yaml
# .github/workflows/test.yml
name: Test OpenStack Integration
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2

      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: 3.9

      - name: Start MockOpenStack
        run: |
          git clone https://github.com/your-org/mopenstack
          cd mopenstack
          make quick-start
          make run &
          sleep 5  # Wait for server to start

      - name: Run OpenStack tests
        env:
          OS_AUTH_URL: http://localhost:5000/v3
          OS_USERNAME: admin
          OS_PASSWORD: password
          OS_PROJECT_NAME: admin
          OS_PROJECT_DOMAIN_NAME: Default
          OS_USER_DOMAIN_NAME: Default
        run: |
          pip install python-openstackclient
          openstack token issue  # Verify connection
          python run_tests.py
```

## Troubleshooting

### Common Issues

1. **Connection refused:**

   ```bash
   # Check if MockOpenStack is running
   curl http://localhost:5000/health

   # Check what's using the port
   make check-port
   ```

2. **Authentication failed:**

   ```bash
   # Verify credentials
   openstack --debug token issue

   # Reset bootstrap data
   make clean
   make bootstrap
   ```

3. **Port conflicts:**
   ```bash
   # Kill conflicting processes
   make kill-port
   make run
   ```

### Environment File Template

Create `openstack-env.sh`:

```bash
#!/bin/bash
# Check if MockOpenStack is running and get the port
MOCK_PORT=$(curl -s http://localhost:5000/health > /dev/null 2>&1 && echo "5000" || \
           curl -s http://localhost:5001/health > /dev/null 2>&1 && echo "5001" || \
           curl -s http://localhost:5002/health > /dev/null 2>&1 && echo "5002" || \
           echo "5000")

export OS_AUTH_URL=http://localhost:${MOCK_PORT}/v3
export OS_PROJECT_NAME=admin
export OS_USERNAME=admin
export OS_PASSWORD=password
export OS_PROJECT_DOMAIN_NAME=Default
export OS_USER_DOMAIN_NAME=Default
export OS_IDENTITY_API_VERSION=3
export OS_REGION_NAME=RegionOne

echo "OpenStack environment configured for MockOpenStack"
echo "Auth URL: $OS_AUTH_URL"
echo "Project: $OS_PROJECT_NAME"
echo "User: $OS_USERNAME"
```

Use it:

```bash
source openstack-env.sh
openstack token issue
```

### Quick Port Detection

If you're unsure which port MockOpenStack is using:

```bash
# Check common ports
for port in 5000 5001 5002 5003; do
  if curl -s http://localhost:$port/health > /dev/null 2>&1; then
    echo "MockOpenStack is running on port $port"
    export OS_AUTH_URL=http://localhost:$port/v3
    break
  fi
done

# Verify connection
openstack token issue
```

## Next Steps

- Explore the [API Documentation](http://localhost:5000/docs) when MockOpenStack is running
- Check the [README.md](README.md) for development setup
- See the [Makefile](Makefile) for all available commands

## Supported Services Status

- ✅ **Keystone (Identity)** - Fully implemented
- 🚧 **Nova (Compute)** - Models ready, API pending
- 🚧 **Neutron (Network)** - Models ready, API pending
- 🚧 **Glance (Image)** - Planned
- 🚧 **Cinder (Block Storage)** - Planned
- 🚧 **Swift (Object Storage)** - Planned
- 🚧 **Octavia (Load Balancer)** - Planned
- 🚧 **Designate (DNS)** - Planned

This guide focuses on Identity (Keystone) operations as it's the only fully implemented service in the current version.
