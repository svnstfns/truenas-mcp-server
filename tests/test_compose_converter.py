"""Tests for Docker Compose to TrueNAS converter."""

import pytest
from unittest.mock import AsyncMock

from truenas_mcp.compose_converter import DockerComposeConverter


class TestDockerComposeConverter:
    """Test Docker Compose conversion functionality."""

    @pytest.fixture
    def converter(self):
        """Create converter instance."""
        return DockerComposeConverter()

    @pytest.mark.asyncio
    async def test_basic_conversion(self, converter):
        """Test basic Docker Compose conversion."""
        compose_yaml = """
version: '3'
services:
  web:
    image: nginx:1.25
    ports:
      - "8080:80"
    environment:
      - NGINX_HOST=localhost
      - NGINX_PORT=80
    volumes:
      - /mnt/pool/nginx/html:/usr/share/nginx/html:ro
      - web_config:/etc/nginx/conf.d
volumes:
  web_config:
"""
        
        result = await converter.convert(compose_yaml, "nginx-app")
        
        # Check basic structure
        assert result["name"] == "nginx-app"
        assert "image" in result
        assert "network" in result
        assert "storage" in result
        assert "environment" in result
        assert result["restart_policy"] == "unless-stopped"
        
        # Check image conversion
        assert result["image"]["repository"] == "nginx"
        assert result["image"]["tag"] == "1.25"

    @pytest.mark.asyncio
    async def test_image_conversion_no_tag(self, converter):
        """Test image conversion without explicit tag."""
        compose_yaml = """
version: '3'
services:
  web:
    image: nginx
"""
        
        result = await converter.convert(compose_yaml, "test-app")
        
        assert result["image"]["repository"] == "nginx"
        assert result["image"]["tag"] == "latest"

    @pytest.mark.asyncio
    async def test_network_conversion_simple_ports(self, converter):
        """Test network conversion with simple port mapping."""
        compose_yaml = """
version: '3'
services:
  web:
    image: nginx
    ports:
      - "8080:80"
      - "8443:443"
"""
        
        result = await converter.convert(compose_yaml, "test-app")
        
        network = result["network"]
        assert network["type"] == "bridge"
        assert "port_forwards" in network
        
        port_forwards = network["port_forwards"]
        assert len(port_forwards) == 2
        
        # Check first port mapping
        assert port_forwards[0]["host_port"] == 8080
        assert port_forwards[0]["container_port"] == 80
        assert port_forwards[0]["protocol"] == "tcp"
        
        # Check second port mapping
        assert port_forwards[1]["host_port"] == 8443
        assert port_forwards[1]["container_port"] == 443
        assert port_forwards[1]["protocol"] == "tcp"

    @pytest.mark.asyncio
    async def test_network_conversion_no_ports(self, converter):
        """Test network conversion without port mappings."""
        compose_yaml = """
version: '3'
services:
  web:
    image: nginx
"""
        
        result = await converter.convert(compose_yaml, "test-app")
        
        network = result["network"]
        assert network["type"] == "bridge"
        assert "port_forwards" not in network

    @pytest.mark.asyncio
    async def test_storage_conversion_host_paths(self, converter):
        """Test storage conversion with host path volumes."""
        compose_yaml = """
version: '3'
services:
  web:
    image: nginx
    volumes:
      - /mnt/pool/data:/var/data
      - /mnt/pool/config:/etc/config:ro
"""
        
        result = await converter.convert(compose_yaml, "test-app")
        
        storage = result["storage"]
        assert len(storage) == 2
        
        # Check first volume
        volume_0 = storage["volume_0"]
        assert volume_0["type"] == "host_path"
        assert volume_0["host_path"] == "/mnt/pool/data"
        assert volume_0["mount_path"] == "/var/data"
        assert volume_0["read_only"] is False
        
        # Check second volume (read-only)
        volume_1 = storage["volume_1"]
        assert volume_1["type"] == "host_path"
        assert volume_1["host_path"] == "/mnt/pool/config"
        assert volume_1["mount_path"] == "/etc/config"
        assert volume_1["read_only"] is True

    @pytest.mark.asyncio
    async def test_storage_conversion_named_volumes(self, converter):
        """Test storage conversion with named volumes (IX volumes)."""
        compose_yaml = """
version: '3'
services:
  web:
    image: nginx
    volumes:
      - app_data:/var/lib/app
      - cache_data:/var/cache
volumes:
  app_data:
  cache_data:
"""
        
        result = await converter.convert(compose_yaml, "test-app")
        
        storage = result["storage"]
        assert len(storage) == 2
        
        # Check named volumes become IX volumes
        volume_0 = storage["volume_0"]
        assert volume_0["type"] == "ix_volume"
        assert "ix_volume_config" in volume_0
        assert volume_0["ix_volume_config"]["dataset_name"] == "app_data"
        assert volume_0["ix_volume_config"]["acl_enable"] is False
        assert volume_0["mount_path"] == "/var/lib/app"

    @pytest.mark.asyncio
    async def test_environment_conversion_list_format(self, converter):
        """Test environment variable conversion from list format."""
        compose_yaml = """
version: '3'
services:
  web:
    image: nginx
    environment:
      - NGINX_HOST=localhost
      - NGINX_PORT=80
      - DEBUG=true
"""
        
        result = await converter.convert(compose_yaml, "test-app")
        
        environment = result["environment"]
        assert environment["NGINX_HOST"] == "localhost"
        assert environment["NGINX_PORT"] == "80"
        assert environment["DEBUG"] == "true"

    @pytest.mark.asyncio
    async def test_environment_conversion_dict_format(self, converter):
        """Test environment variable conversion from dict format."""
        compose_yaml = """
version: '3'
services:
  web:
    image: nginx
    environment:
      NGINX_HOST: localhost
      NGINX_PORT: 80
      DEBUG: true
"""
        
        result = await converter.convert(compose_yaml, "test-app")
        
        environment = result["environment"]
        assert environment["NGINX_HOST"] == "localhost"
        assert environment["NGINX_PORT"] == 80
        assert environment["DEBUG"] is True

    @pytest.mark.asyncio
    async def test_environment_conversion_no_env(self, converter):
        """Test environment conversion with no environment variables."""
        compose_yaml = """
version: '3'
services:
  web:
    image: nginx
"""
        
        result = await converter.convert(compose_yaml, "test-app")
        
        environment = result["environment"]
        assert environment == {}

    @pytest.mark.asyncio
    async def test_invalid_yaml(self, converter):
        """Test conversion with invalid YAML."""
        invalid_yaml = """
invalid yaml content:
  - this is not valid
    - nested incorrectly
"""
        
        with pytest.raises(ValueError, match="Invalid YAML"):
            await converter.convert(invalid_yaml, "test-app")

    @pytest.mark.asyncio
    async def test_no_services(self, converter):
        """Test conversion with no services defined."""
        compose_yaml = """
version: '3'
networks:
  mynet:
"""
        
        with pytest.raises(ValueError, match="No services found"):
            await converter.convert(compose_yaml, "test-app")

    @pytest.mark.asyncio
    async def test_empty_services(self, converter):
        """Test conversion with empty services."""
        compose_yaml = """
version: '3'
services: {}
"""
        
        with pytest.raises(ValueError, match="No services found"):
            await converter.convert(compose_yaml, "test-app")

    @pytest.mark.asyncio
    async def test_multi_service_conversion(self, converter):
        """Test conversion takes first service when multiple services exist."""
        compose_yaml = """
version: '3'
services:
  web:
    image: nginx:1.25
    ports:
      - "8080:80"
  db:
    image: postgres:13
    ports:
      - "5432:5432"
"""
        
        result = await converter.convert(compose_yaml, "multi-app")
        
        # Should use first service (web)
        assert result["image"]["repository"] == "nginx"
        assert result["image"]["tag"] == "1.25"
        
        # Should have web service ports, not db ports
        port_forwards = result["network"]["port_forwards"]
        assert port_forwards[0]["host_port"] == 8080
        assert port_forwards[0]["container_port"] == 80

    @pytest.mark.asyncio
    async def test_complex_compose_conversion(self, converter):
        """Test conversion of complex Docker Compose file."""
        compose_yaml = """
version: '3.8'
services:
  webapp:
    image: myapp:v2.1.0
    ports:
      - "3000:3000"
      - "3001:3001"
    environment:
      - NODE_ENV=production
      - DATABASE_URL=postgresql://user:pass@db:5432/myapp
      - REDIS_URL=redis://redis:6379
    volumes:
      - /mnt/pool/app/data:/app/data
      - /mnt/pool/app/logs:/app/logs:ro
      - app_uploads:/app/uploads
      - cache_data:/tmp/cache
    restart: unless-stopped
    
volumes:
  app_uploads:
  cache_data:

networks:
  app_network:
    driver: bridge
"""
        
        result = await converter.convert(compose_yaml, "complex-app")
        
        # Check image
        assert result["image"]["repository"] == "myapp"
        assert result["image"]["tag"] == "v2.1.0"
        
        # Check network with multiple ports
        port_forwards = result["network"]["port_forwards"]
        assert len(port_forwards) == 2
        assert port_forwards[0]["host_port"] == 3000
        assert port_forwards[1]["host_port"] == 3001
        
        # Check environment variables
        env = result["environment"]
        assert env["NODE_ENV"] == "production"
        assert "postgresql://" in env["DATABASE_URL"]
        assert env["REDIS_URL"] == "redis://redis:6379"
        
        # Check storage with mixed volume types
        storage = result["storage"]
        assert len(storage) == 4
        
        # Host path volumes
        volume_0 = storage["volume_0"]
        assert volume_0["type"] == "host_path"
        assert volume_0["host_path"] == "/mnt/pool/app/data"
        
        # Named volumes become IX volumes
        found_ix_volume = False
        for vol_key, vol_config in storage.items():
            if vol_config["type"] == "ix_volume":
                found_ix_volume = True
                assert "ix_volume_config" in vol_config
                assert "dataset_name" in vol_config["ix_volume_config"]
        
        assert found_ix_volume, "Should have IX volumes for named volumes"