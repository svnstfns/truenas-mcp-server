"""Security and validation rules for Docker Compose and TrueNAS configurations."""

import re
from typing import List, Tuple

import structlog
import yaml

logger = structlog.get_logger(__name__)


class ComposeValidator:
    """Validates Docker Compose YAML for security and TrueNAS compatibility."""

    # Security violation patterns
    SECURITY_VIOLATIONS = [
        (r"privileged:\s*true", "Privileged containers are not allowed"),
        (r"--privileged", "Privileged mode is not allowed"),
        (r"network_mode:\s*host", "Host network mode should be avoided"),
        (r"pid:\s*host", "Host PID namespace is not allowed"),
        (r"ipc:\s*host", "Host IPC namespace is not allowed"),
        (r"user:\s*root", "Running as root user is discouraged"),
        (r"user:\s*0", "Running as UID 0 (root) is discouraged"),
    ]

    # Dangerous bind mount patterns
    DANGEROUS_MOUNTS = [
        (r"(/etc/|/var/lib/docker/|/proc/|/sys/).*:", "System directory bind mounts are not allowed"),
        (r"/dev/.*:", "Device bind mounts require special consideration"),
        (r"/var/run/docker.sock:", "Docker socket access is not allowed"),
    ]

    # Warning patterns (not errors, but should be flagged)
    WARNING_PATTERNS = [
        (r"restart:\s*always", "Consider using 'unless-stopped' instead of 'always'"),
        (r"ports:.*\*:", "Avoid binding to all interfaces (*) for security"),
        (r"ports:.*0\.0\.0\.0:", "Avoid binding to all interfaces (0.0.0.0) for security"),
    ]

    async def validate(self, compose_yaml: str, check_security: bool = True) -> Tuple[bool, List[str]]:
        """Validate Docker Compose YAML."""
        logger.info("Validating Docker Compose", check_security=check_security)
        
        issues = []
        
        # YAML syntax validation
        try:
            compose_data = yaml.safe_load(compose_yaml)
        except yaml.YAMLError as e:
            issues.append(f"Invalid YAML syntax: {e}")
            return False, issues
        
        # Basic structure validation
        structure_issues = self._validate_structure(compose_data)
        issues.extend(structure_issues)
        
        # Security validation
        if check_security:
            security_issues = self._validate_security(compose_yaml, compose_data)
            issues.extend(security_issues)
        
        # TrueNAS compatibility validation
        compatibility_issues = self._validate_truenas_compatibility(compose_data)
        issues.extend(compatibility_issues)
        
        # Separate errors from warnings
        errors = [issue for issue in issues if any(
            error_pattern in issue.lower() 
            for error_pattern in ["not allowed", "invalid", "missing", "required"]
        )]
        
        is_valid = len(errors) == 0
        
        logger.info(
            "Validation complete",
            is_valid=is_valid,
            total_issues=len(issues),
            errors=len(errors),
        )
        
        return is_valid, issues

    def _validate_structure(self, compose_data: dict) -> List[str]:
        """Validate basic Docker Compose structure."""
        issues = []
        
        if not isinstance(compose_data, dict):
            issues.append("Docker Compose must be a YAML object")
            return issues
        
        # Check for required fields
        if "services" not in compose_data:
            issues.append("Missing required 'services' section")
        elif not compose_data["services"]:
            issues.append("Services section cannot be empty")
        
        # Validate version if present
        version = compose_data.get("version")
        if version:
            try:
                version_float = float(version)
                if version_float < 2.0:
                    issues.append("Docker Compose version should be 2.0 or higher")
            except (ValueError, TypeError):
                issues.append("Invalid Docker Compose version format")
        
        # Validate services
        services = compose_data.get("services", {})
        for service_name, service_config in services.items():
            if not isinstance(service_config, dict):
                issues.append(f"Service '{service_name}' must be an object")
                continue
            
            # Check for image
            if "image" not in service_config and "build" not in service_config:
                issues.append(f"Service '{service_name}' must have either 'image' or 'build'")
            
            # Validate service name
            if not re.match(r"^[a-zA-Z0-9][a-zA-Z0-9_.-]*$", service_name):
                issues.append(f"Service name '{service_name}' contains invalid characters")
        
        return issues

    def _validate_security(self, compose_yaml: str, compose_data: dict) -> List[str]:
        """Validate security constraints."""
        issues = []
        
        # Check for security violations in raw YAML
        for pattern, message in self.SECURITY_VIOLATIONS:
            if re.search(pattern, compose_yaml, re.IGNORECASE | re.MULTILINE):
                issues.append(message)
        
        # Check for dangerous bind mounts
        for pattern, message in self.DANGEROUS_MOUNTS:
            if re.search(pattern, compose_yaml, re.IGNORECASE | re.MULTILINE):
                issues.append(message)
        
        # Check warning patterns
        for pattern, message in self.WARNING_PATTERNS:
            if re.search(pattern, compose_yaml, re.IGNORECASE | re.MULTILINE):
                issues.append(f"Warning: {message}")
        
        # Validate capabilities
        services = compose_data.get("services", {})
        for service_name, service_config in services.items():
            cap_add = service_config.get("cap_add", [])
            if cap_add:
                dangerous_caps = ["SYS_ADMIN", "NET_ADMIN", "SYS_MODULE", "SYS_RAWIO"]
                for cap in cap_add:
                    if cap in dangerous_caps:
                        issues.append(f"Service '{service_name}': Capability {cap} is not allowed")
        
        return issues

    def _validate_truenas_compatibility(self, compose_data: dict) -> List[str]:
        """Validate TrueNAS Custom App compatibility."""
        issues = []
        
        services = compose_data.get("services", {})
        
        # TrueNAS-specific validations
        for service_name, service_config in services.items():
            
            # Check volumes format
            volumes = service_config.get("volumes", [])
            for volume in volumes:
                if isinstance(volume, str):
                    if volume.startswith("./") or volume.startswith("../"):
                        issues.append(
                            f"Service '{service_name}': Relative paths in volumes are not supported"
                        )
                    
                    # Validate TrueNAS path conventions
                    if ":" in volume:
                        host_path = volume.split(":")[0]
                        if host_path.startswith("/") and not host_path.startswith("/mnt/"):
                            issues.append(
                                f"Service '{service_name}': Host paths should start with /mnt/ "
                                f"to use TrueNAS pools"
                            )
            
            # Check port format
            ports = service_config.get("ports", [])
            for port in ports:
                if isinstance(port, str):
                    try:
                        if ":" in port:
                            host_port = port.split(":")[0]
                            host_port_int = int(host_port)
                            if host_port_int < 1024 and host_port_int != 80 and host_port_int != 443:
                                issues.append(
                                    f"Service '{service_name}': Privileged ports (<1024) "
                                    f"may require special configuration"
                                )
                    except ValueError:
                        issues.append(f"Service '{service_name}': Invalid port format '{port}'")
        
        # Check for external networks (not directly supported)
        networks = compose_data.get("networks", {})
        for network_name, network_config in networks.items():
            if isinstance(network_config, dict) and network_config.get("external"):
                issues.append(f"External network '{network_name}' may not work as expected")
        
        return issues

    def validate_app_name(self, app_name: str) -> List[str]:
        """Validate Custom App name."""
        issues = []
        
        if not app_name:
            issues.append("App name cannot be empty")
            return issues
        
        if len(app_name) < 2:
            issues.append("App name must be at least 2 characters long")
        
        if len(app_name) > 50:
            issues.append("App name must be 50 characters or less")
        
        if not re.match(r"^[a-z0-9][a-z0-9-]*[a-z0-9]$", app_name):
            issues.append(
                "App name must start and end with alphanumeric characters, "
                "and can only contain lowercase letters, numbers, and hyphens"
            )
        
        if "--" in app_name:
            issues.append("App name cannot contain consecutive hyphens")
        
        return issues