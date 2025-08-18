"""Security configuration validation and utilities."""

import os
import re
from typing import Dict, List, Tuple

import structlog

logger = structlog.get_logger(__name__)


class SecurityConfigError(Exception):
    """Security configuration error."""


def is_production_environment() -> bool:
    """Detect if we're running in a production environment."""
    env_indicators = [
        os.getenv("ENVIRONMENT", "").lower() == "production",
        os.getenv("PROD", "").lower() == "true",
        os.getenv("NODE_ENV", "").lower() == "production",
        os.getenv("TRUENAS_PRODUCTION", "").lower() == "true",
    ]
    return any(env_indicators)


def validate_host_configuration(host: str) -> Tuple[bool, List[str]]:
    """Validate TrueNAS host configuration for security issues."""
    issues = []
    
    # Check for localhost in production
    if is_production_environment() and host.lower() in ["localhost", "127.0.0.1", "::1"]:
        issues.append("Production environment should not use localhost for TrueNAS host")
    
    # Check for private network hostnames that might be leaked
    private_patterns = [
        r".*\.pvnkn3t\.lan$",  # The original hardcoded domain
        r".*\.local$",
        r".*\.lan$",
        r".*\.internal$",
    ]
    
    for pattern in private_patterns:
        if re.match(pattern, host, re.IGNORECASE):
            logger.warning("Host appears to be on private network", host=host)
            break
    
    # Check for valid hostname format
    hostname_pattern = r"^[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?)*$"
    if not re.match(hostname_pattern, host):
        issues.append(f"Invalid hostname format: {host}")
    
    return len(issues) == 0, issues


def validate_ssl_configuration(ssl_verify: bool, host: str) -> Tuple[bool, List[str]]:
    """Validate SSL configuration for security issues."""
    issues = []
    
    # SSL verification disabled in production is critical
    if is_production_environment() and not ssl_verify:
        issues.append("SSL certificate verification MUST be enabled in production environments")
    
    # Warn about SSL verification disabled for non-localhost
    if not ssl_verify and host.lower() not in ["localhost", "127.0.0.1", "::1"]:
        issues.append(f"SSL verification disabled for remote host {host} - this is insecure")
    
    return len(issues) == 0, issues


def validate_api_key_configuration(api_key: str | None) -> Tuple[bool, List[str]]:
    """Validate API key configuration."""
    issues = []
    
    if not api_key:
        issues.append("TRUENAS_API_KEY environment variable is required")
        return False, issues
    
    # TrueNAS generates API keys, so we only check for presence
    # No validation of format, length, or entropy since we don't control generation
    return True, issues


def validate_mock_mode_configuration(mock_mode: bool) -> Tuple[bool, List[str]]:
    """Validate mock mode configuration."""
    issues = []
    
    if mock_mode and is_production_environment():
        issues.append("Mock mode MUST NOT be enabled in production environments")
    
    if mock_mode:
        logger.warning("Mock mode is enabled - this bypasses all TrueNAS authentication")
    
    return len(issues) == 0, issues


def validate_all_security_configuration(config: Dict[str, any]) -> Tuple[bool, List[str]]:
    """Validate all security configuration settings."""
    all_issues = []
    overall_valid = True
    
    # Validate host configuration
    host_valid, host_issues = validate_host_configuration(config.get("truenas_host", ""))
    if not host_valid:
        overall_valid = False
    all_issues.extend(host_issues)
    
    # Validate SSL configuration
    ssl_valid, ssl_issues = validate_ssl_configuration(
        config.get("ssl_verify", True),
        config.get("truenas_host", "")
    )
    if not ssl_valid:
        overall_valid = False
    all_issues.extend(ssl_issues)
    
    # Validate API key
    api_key_valid, api_key_issues = validate_api_key_configuration(
        config.get("truenas_api_key")
    )
    if not api_key_valid:
        overall_valid = False
    all_issues.extend(api_key_issues)
    
    # Validate mock mode
    mock_valid, mock_issues = validate_mock_mode_configuration(
        config.get("mock_mode", False)
    )
    if not mock_valid:
        overall_valid = False
    all_issues.extend(mock_issues)
    
    # Log security validation results
    if all_issues:
        logger.warning("Security configuration issues found", issues=all_issues)
    else:
        logger.info("Security configuration validation passed")
    
    return overall_valid, all_issues


def enforce_production_security_requirements(config: Dict[str, any]) -> None:
    """Enforce security requirements for production environments."""
    if not is_production_environment():
        return
    
    valid, issues = validate_all_security_configuration(config)
    
    if not valid:
        critical_issues = [
            issue for issue in issues 
            if "MUST" in issue or "production" in issue.lower()
        ]
        
        if critical_issues:
            error_msg = f"Critical security issues in production: {'; '.join(critical_issues)}"
            logger.error("Production security validation failed", issues=critical_issues)
            raise SecurityConfigError(error_msg)