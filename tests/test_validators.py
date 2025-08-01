"""Tests for security and validation rules."""

import pytest

from truenas_mcp.validators import ComposeValidator


class TestComposeValidator:
    """Test Docker Compose validation functionality."""

    @pytest.fixture
    def validator(self):
        """Create validator instance."""
        return ComposeValidator()

    @pytest.mark.asyncio
    async def test_valid_compose(self, validator):
        """Test validation of valid Docker Compose."""
        compose_yaml = """
version: '3.8'
services:
  web:
    image: nginx:1.25
    ports:
      - "8080:80"
    volumes:
      - /mnt/pool/data:/app/data
    environment:
      - NGINX_HOST=localhost
    restart: unless-stopped
"""
        
        is_valid, issues = await validator.validate(compose_yaml, check_security=True)
        
        assert is_valid is True
        assert isinstance(issues, list)
        # May have warnings but no errors

    @pytest.mark.asyncio
    async def test_invalid_yaml_syntax(self, validator):
        """Test validation with invalid YAML syntax."""
        invalid_yaml = """
version: '3'
services:
  web:
    image: nginx
    ports:
      - "8080:80"
    - invalid_syntax
"""
        
        is_valid, issues = await validator.validate(invalid_yaml, check_security=True)
        
        assert is_valid is False
        assert len(issues) > 0
        assert any("Invalid YAML syntax" in issue for issue in issues)

    @pytest.mark.asyncio
    async def test_missing_services(self, validator):
        """Test validation with missing services section."""
        compose_yaml = """
version: '3'
networks:
  mynet:
"""
        
        is_valid, issues = await validator.validate(compose_yaml, check_security=True)
        
        assert is_valid is False
        assert any("Missing required 'services' section" in issue for issue in issues)

    @pytest.mark.asyncio
    async def test_empty_services(self, validator):
        """Test validation with empty services."""
        compose_yaml = """
version: '3'
services: {}
"""
        
        is_valid, issues = await validator.validate(compose_yaml, check_security=True)
        
        assert is_valid is False
        assert any("Services section cannot be empty" in issue for issue in issues)

    @pytest.mark.asyncio
    async def test_old_compose_version(self, validator):
        """Test validation with old Docker Compose version."""
        compose_yaml = """
version: '1'
services:
  web:
    image: nginx
"""
        
        is_valid, issues = await validator.validate(compose_yaml, check_security=True)
        
        assert any("version should be 2.0 or higher" in issue for issue in issues)

    @pytest.mark.asyncio
    async def test_service_without_image_or_build(self, validator):
        """Test validation of service without image or build."""
        compose_yaml = """
version: '3'
services:
  web:
    ports:
      - "8080:80"
"""
        
        is_valid, issues = await validator.validate(compose_yaml, check_security=True)
        
        assert is_valid is False
        assert any("must have either 'image' or 'build'" in issue for issue in issues)

    @pytest.mark.asyncio
    async def test_invalid_service_name(self, validator):
        """Test validation with invalid service name."""
        compose_yaml = """
version: '3'
services:
  "invalid-service-name!":
    image: nginx
"""
        
        is_valid, issues = await validator.validate(compose_yaml, check_security=True)
        
        assert any("contains invalid characters" in issue for issue in issues)

    @pytest.mark.asyncio
    async def test_security_privileged_container(self, validator):
        """Test security validation catches privileged containers."""
        compose_yaml = """
version: '3'
services:
  web:
    image: nginx
    privileged: true
"""
        
        is_valid, issues = await validator.validate(compose_yaml, check_security=True)
        
        assert is_valid is False
        assert any("Privileged containers are not allowed" in issue for issue in issues)

    @pytest.mark.asyncio
    async def test_security_host_network(self, validator):
        """Test security validation catches host network mode."""
        compose_yaml = """
version: '3'
services:
  web:
    image: nginx
    network_mode: host
"""
        
        is_valid, issues = await validator.validate(compose_yaml, check_security=True)
        
        assert any("Host network mode should be avoided" in issue for issue in issues)

    @pytest.mark.asyncio
    async def test_security_dangerous_bind_mounts(self, validator):
        """Test security validation catches dangerous bind mounts."""
        compose_yaml = """
version: '3'
services:
  web:
    image: nginx
    volumes:
      - /etc/passwd:/etc/passwd:ro
      - /var/run/docker.sock:/var/run/docker.sock
"""
        
        is_valid, issues = await validator.validate(compose_yaml, check_security=True)
        
        assert is_valid is False
        assert any("System directory bind mounts are not allowed" in issue for issue in issues)
        assert any("Docker socket access is not allowed" in issue for issue in issues)

    @pytest.mark.asyncio
    async def test_security_dangerous_capabilities(self, validator):
        """Test security validation catches dangerous capabilities."""
        compose_yaml = """
version: '3'
services:
  web:
    image: nginx
    cap_add:
      - SYS_ADMIN
      - NET_ADMIN
"""
        
        is_valid, issues = await validator.validate(compose_yaml, check_security=True)
        
        assert is_valid is False
        assert any("SYS_ADMIN" in issue and "not allowed" in issue for issue in issues)
        assert any("NET_ADMIN" in issue and "not allowed" in issue for issue in issues)

    @pytest.mark.asyncio
    async def test_security_warnings(self, validator):
        """Test security validation generates warnings for risky patterns."""
        compose_yaml = """
version: '3'
services:
  web:
    image: nginx
    ports:
      - "*:80"
    restart: always
"""
        
        is_valid, issues = await validator.validate(compose_yaml, check_security=True)
        
        # Should be valid but with warnings
        assert is_valid is True
        assert any("binding to all interfaces" in issue.lower() for issue in issues)
        assert any("consider using 'unless-stopped'" in issue.lower() for issue in issues)

    @pytest.mark.asyncio
    async def test_security_disabled(self, validator):
        """Test validation with security checks disabled."""
        compose_yaml = """
version: '3'
services:
  web:
    image: nginx
    privileged: true
    volumes:
      - /etc/passwd:/etc/passwd
"""
        
        is_valid, issues = await validator.validate(compose_yaml, check_security=False)
        
        # Should not catch security issues when disabled
        security_issues = [issue for issue in issues if "not allowed" in issue.lower()]
        assert len(security_issues) == 0

    @pytest.mark.asyncio
    async def test_truenas_compatibility_relative_paths(self, validator):
        """Test TrueNAS compatibility validation catches relative paths."""
        compose_yaml = """
version: '3'
services:
  web:
    image: nginx
    volumes:
      - ./data:/app/data
      - ../config:/app/config
"""
        
        is_valid, issues = await validator.validate(compose_yaml, check_security=True)
        
        assert is_valid is False
        assert any("Relative paths in volumes are not supported" in issue for issue in issues)

    @pytest.mark.asyncio
    async def test_truenas_compatibility_non_pool_paths(self, validator):
        """Test TrueNAS compatibility validation suggests pool paths."""
        compose_yaml = """
version: '3'
services:
  web:
    image: nginx
    volumes:
      - /home/user/data:/app/data
"""
        
        is_valid, issues = await validator.validate(compose_yaml, check_security=True)
        
        assert any("should start with /mnt/" in issue for issue in issues)

    @pytest.mark.asyncio
    async def test_truenas_compatibility_privileged_ports(self, validator):
        """Test TrueNAS compatibility validation warns about privileged ports."""
        compose_yaml = """
version: '3'
services:
  web:
    image: nginx
    ports:
      - "22:22"
      - "80:80"
"""
        
        is_valid, issues = await validator.validate(compose_yaml, check_security=True)
        
        # Port 22 should trigger warning, port 80 is allowed
        assert any("Privileged ports" in issue and "22" in issue for issue in issues)

    @pytest.mark.asyncio
    async def test_truenas_compatibility_external_networks(self, validator):
        """Test TrueNAS compatibility validation warns about external networks."""
        compose_yaml = """
version: '3'
services:
  web:
    image: nginx
networks:
  external_net:
    external: true
"""
        
        is_valid, issues = await validator.validate(compose_yaml, check_security=True)
        
        assert any("External network" in issue and "may not work" in issue for issue in issues)

    @pytest.mark.asyncio
    async def test_truenas_compatibility_invalid_ports(self, validator):
        """Test TrueNAS compatibility validation catches invalid port formats."""
        compose_yaml = """
version: '3'
services:
  web:
    image: nginx
    ports:
      - "invalid:port"
      - "abc:80"
"""
        
        is_valid, issues = await validator.validate(compose_yaml, check_security=True)
        
        assert is_valid is False
        assert any("Invalid port format" in issue for issue in issues)

    def test_validate_app_name_valid(self, validator):
        """Test app name validation with valid names."""
        valid_names = [
            "nginx-app",
            "my-service-v2",
            "app123",
            "web-server",
            "test-app-1",
        ]
        
        for name in valid_names:
            issues = validator.validate_app_name(name)
            assert len(issues) == 0, f"Valid name '{name}' should not have issues: {issues}"

    def test_validate_app_name_invalid(self, validator):
        """Test app name validation with invalid names."""
        invalid_cases = [
            ("", "App name cannot be empty"),
            ("a", "must be at least 2 characters"),
            ("x" * 51, "must be 50 characters or less"),
            ("-invalid", "must start and end with alphanumeric"),
            ("invalid-", "must start and end with alphanumeric"),
            ("Invalid-Name", "lowercase letters"),
            ("app_name", "lowercase letters"),  # underscores not allowed
            ("app--name", "consecutive hyphens"),
            ("app.name", "lowercase letters"),  # dots not allowed
            ("app name", "lowercase letters"),  # spaces not allowed
        ]
        
        for name, expected_error in invalid_cases:
            issues = validator.validate_app_name(name)
            assert len(issues) > 0, f"Invalid name '{name}' should have issues"
            assert any(expected_error in issue for issue in issues), \
                f"Expected error '{expected_error}' not found in {issues}"

    @pytest.mark.asyncio
    async def test_complex_validation_scenario(self, validator):
        """Test complex validation scenario with multiple issues."""
        compose_yaml = """
version: '2.4'
services:
  "web-app!":
    image: nginx
    privileged: true
    network_mode: host
    ports:
      - "*:80"
    volumes:
      - /etc/passwd:/etc/passwd
      - ./data:/app/data
      - /mnt/pool/data:/app/pool-data
    cap_add:
      - SYS_ADMIN
    restart: always
    
  db:
    ports:
      - "5432:5432"
      # Missing image
      
networks:
  external_net:
    external: true
"""
        
        is_valid, issues = await validator.validate(compose_yaml, check_security=True)
        
        # Should not be valid due to multiple security violations
        assert is_valid is False
        
        # Check for various types of issues
        issue_text = " ".join(issues).lower()
        
        # Security violations
        assert "privileged containers are not allowed" in issue_text
        assert "system directory bind mounts are not allowed" in issue_text
        assert "sys_admin" in issue_text and "not allowed" in issue_text
        
        # Structure issues
        assert "invalid characters" in issue_text  # service name
        assert "must have either 'image' or 'build'" in issue_text  # db service
        
        # TrueNAS compatibility issues
        assert "relative paths" in issue_text
        assert "external network" in issue_text
        
        # Warnings
        assert "binding to all interfaces" in issue_text
        assert "unless-stopped" in issue_text