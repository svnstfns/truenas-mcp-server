"""Pytest configuration and shared fixtures."""

import pytest
import asyncio
from unittest.mock import patch
import os

# Configure asyncio event loop for pytest-asyncio
@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for the test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_environment():
    """Mock environment variables for testing."""
    test_env = {
        "TRUENAS_HOST": "test.example.com",
        "TRUENAS_API_KEY": "test-api-key-123",
        "TRUENAS_PORT": "443",
        "TRUENAS_PROTOCOL": "wss",
        "TRUENAS_SSL_VERIFY": "false",
        "DEBUG_MODE": "false",
        "MOCK_TRUENAS": "true",
    }
    
    with patch.dict(os.environ, test_env, clear=False):
        yield test_env


@pytest.fixture
def sample_docker_compose():
    """Sample Docker Compose YAML for testing."""
    return """
version: '3.8'
services:
  web:
    image: nginx:1.25
    ports:
      - "8080:80"
      - "8443:443"
    environment:
      - NGINX_HOST=localhost
      - NGINX_PORT=80
    volumes:
      - /mnt/pool/nginx/html:/usr/share/nginx/html:ro
      - /mnt/pool/nginx/config:/etc/nginx/conf.d
      - web_data:/var/lib/nginx
    restart: unless-stopped
    
volumes:
  web_data:
"""


@pytest.fixture
def sample_truenas_config():
    """Sample TrueNAS Custom App configuration."""
    return {
        "name": "nginx-app",
        "image": {
            "repository": "nginx",
            "tag": "1.25"
        },
        "network": {
            "type": "bridge",
            "port_forwards": [
                {
                    "host_port": 8080,
                    "container_port": 80,
                    "protocol": "tcp"
                },
                {
                    "host_port": 8443,
                    "container_port": 443,
                    "protocol": "tcp"
                }
            ]
        },
        "storage": {
            "html": {
                "type": "host_path",
                "host_path": "/mnt/pool/nginx/html",
                "mount_path": "/usr/share/nginx/html",
                "read_only": True
            },
            "config": {
                "type": "host_path",
                "host_path": "/mnt/pool/nginx/config",
                "mount_path": "/etc/nginx/conf.d",
                "read_only": False
            },
            "data": {
                "type": "ix_volume",
                "ix_volume_config": {
                    "dataset_name": "web_data",
                    "acl_enable": False
                },
                "mount_path": "/var/lib/nginx"
            }
        },
        "environment": {
            "NGINX_HOST": "localhost",
            "NGINX_PORT": "80"
        },
        "restart_policy": "unless-stopped"
    }


@pytest.fixture
def invalid_docker_compose_samples():
    """Collection of invalid Docker Compose samples for testing."""
    return {
        "invalid_yaml": """
version: '3'
services:
  web:
    image: nginx
    - invalid_syntax
""",
        
        "missing_services": """
version: '3'
networks:
  mynet:
""",
        
        "privileged_container": """
version: '3'
services:
  web:
    image: nginx
    privileged: true
""",
        
        "dangerous_bind_mount": """
version: '3'
services:
  web:
    image: nginx
    volumes:
      - /etc/passwd:/etc/passwd:ro
""",
        
        "no_image_or_build": """
version: '3'
services:
  web:
    ports:
      - "8080:80"
""",
    }


@pytest.fixture
def mock_truenas_api_responses():
    """Mock TrueNAS API responses for testing."""
    return {
        "auth_success": {
            "id": 1,
            "jsonrpc": "2.0",
            "result": True
        },
        
        "auth_failure": {
            "id": 1,
            "jsonrpc": "2.0",
            "error": {
                "code": -1,
                "message": "Invalid API key"
            }
        },
        
        "list_apps": {
            "id": 2,
            "jsonrpc": "2.0",
            "result": [
                {
                    "name": "nginx-demo",
                    "status": "running",
                    "created": "2025-07-30T10:00:00Z"
                },
                {
                    "name": "plex-server",
                    "status": "stopped",
                    "created": "2025-07-29T15:30:00Z"
                }
            ]
        },
        
        "app_status": {
            "id": 3,
            "jsonrpc": "2.0",
            "result": {
                "name": "nginx-demo",
                "status": "running",
                "containers": ["nginx-demo-web-1"]
            }
        },
        
        "start_app_success": {
            "id": 4,
            "jsonrpc": "2.0",
            "result": {"message": "App started successfully"}
        },
        
        "deploy_app_success": {
            "id": 5,
            "jsonrpc": "2.0",
            "result": {"id": "new-app", "status": "deployed"}
        },
        
        "api_error": {
            "id": 6,
            "jsonrpc": "2.0",
            "error": {
                "code": -2,
                "message": "App not found"
            }
        }
    }


# Pytest markers
pytest_plugins = ["pytest_asyncio"]

# Configure pytest-asyncio
@pytest.fixture(scope="session")
def anyio_backends():
    """Configure anyio backends."""
    return ["asyncio"]


# Test configuration
def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers", "unit: mark test as a unit test"
    )
    config.addinivalue_line(
        "markers", "integration: mark test as an integration test"
    )
    config.addinivalue_line(
        "markers", "mcp: mark test as MCP protocol test"
    )
    config.addinivalue_line(
        "markers", "security: mark test as security validation test"
    )
    config.addinivalue_line(
        "markers", "compose: mark test as Docker Compose related test"
    )


# Cleanup fixtures
@pytest.fixture(autouse=True)
def cleanup_environment():
    """Cleanup environment after each test."""
    yield
    # Clean up any test artifacts if needed
    pass