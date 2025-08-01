"""Mock TrueNAS client for development and testing."""

import asyncio
import random
from typing import Any, Dict, List, Optional, Tuple

import structlog

logger = structlog.get_logger(__name__)


class MockTrueNASClient:
    """Mock TrueNAS client for development without real TrueNAS access."""

    def __init__(self) -> None:
        """Initialize mock client."""
        self.connected = False
        self.authenticated = False
        
        # Mock data
        self.mock_apps = {
            "nginx-demo": {
                "name": "nginx-demo",
                "status": "running",
                "containers": ["nginx-demo-web-1"],
                "ports": ["8080:80"],
                "created": "2025-07-30T10:00:00Z",
            },
            "plex-server": {
                "name": "plex-server",
                "status": "stopped",
                "containers": ["plex-server-plex-1"],
                "ports": ["32400:32400"],
                "created": "2025-07-29T15:30:00Z",
            },
            "home-assistant": {
                "name": "home-assistant",
                "status": "running",
                "containers": ["home-assistant-hass-1"],
                "ports": ["8123:8123"],
                "created": "2025-07-28T09:15:00Z",
            },
        }

    async def connect(self) -> None:
        """Mock connection to TrueNAS."""
        logger.info("Mock: Connecting to TrueNAS")
        await asyncio.sleep(0.1)  # Simulate connection delay
        self.connected = True
        self.authenticated = True
        logger.info("Mock: Connected and authenticated successfully")

    async def disconnect(self) -> None:
        """Mock disconnection."""
        logger.info("Mock: Disconnecting from TrueNAS")
        self.connected = False
        self.authenticated = False

    async def test_connection(self) -> bool:
        """Mock connection test."""
        logger.info("Mock: Testing connection")
        await asyncio.sleep(0.1)  # Simulate API call
        return True

    async def list_custom_apps(self, status_filter: str = "all") -> List[Dict[str, Any]]:
        """Mock list Custom Apps."""
        logger.info("Mock: Listing Custom Apps", filter=status_filter)
        await asyncio.sleep(0.2)  # Simulate API call
        
        apps = list(self.mock_apps.values())
        
        if status_filter != "all":
            apps = [app for app in apps if app["status"] == status_filter]
        
        return apps

    async def get_app_status(self, app_name: str) -> str:
        """Mock get Custom App status."""
        logger.info("Mock: Getting app status", app=app_name)
        await asyncio.sleep(0.1)
        
        if app_name not in self.mock_apps:
            raise Exception(f"App '{app_name}' not found")
        
        return self.mock_apps[app_name]["status"]

    async def start_app(self, app_name: str) -> bool:
        """Mock start Custom App."""
        logger.info("Mock: Starting app", app=app_name)
        await asyncio.sleep(0.5)  # Simulate start time
        
        if app_name not in self.mock_apps:
            return False
        
        self.mock_apps[app_name]["status"] = "running"
        return True

    async def stop_app(self, app_name: str) -> bool:
        """Mock stop Custom App."""
        logger.info("Mock: Stopping app", app=app_name)
        await asyncio.sleep(0.3)  # Simulate stop time
        
        if app_name not in self.mock_apps:
            return False
        
        self.mock_apps[app_name]["status"] = "stopped"
        return True

    async def deploy_app(
        self,
        app_name: str,
        compose_yaml: str,
        auto_start: bool = True,
    ) -> bool:
        """Mock deploy Custom App."""
        logger.info("Mock: Deploying app", app=app_name, auto_start=auto_start)
        await asyncio.sleep(1.0)  # Simulate deployment time
        
        # Simulate deployment success/failure (90% success rate)
        if random.random() < 0.9:
            # Add new app to mock data
            self.mock_apps[app_name] = {
                "name": app_name,
                "status": "running" if auto_start else "stopped",
                "containers": [f"{app_name}-service-1"],
                "ports": ["8080:80"],  # Mock port
                "created": "2025-07-30T12:00:00Z",
            }
            return True
        else:
            logger.warning("Mock: Simulated deployment failure")
            return False

    async def update_app(
        self,
        app_name: str,
        compose_yaml: str,
        force_recreate: bool = False,
    ) -> bool:
        """Mock update Custom App."""
        logger.info("Mock: Updating app", app=app_name, force_recreate=force_recreate)
        await asyncio.sleep(0.8)  # Simulate update time
        
        if app_name not in self.mock_apps:
            return False
        
        # Simulate update (always successful in mock)
        logger.info("Mock: App updated successfully")
        return True

    async def delete_app(self, app_name: str, delete_volumes: bool = False) -> bool:
        """Mock delete Custom App."""
        logger.info("Mock: Deleting app", app=app_name, delete_volumes=delete_volumes)
        await asyncio.sleep(0.4)  # Simulate deletion time
        
        if app_name not in self.mock_apps:
            return False
        
        # Remove app from mock data
        del self.mock_apps[app_name]
        return True

    async def validate_compose(
        self,
        compose_yaml: str,
        check_security: bool = True,
    ) -> Tuple[bool, List[str]]:
        """Mock validate Docker Compose."""
        logger.info("Mock: Validating Docker Compose", check_security=check_security)
        await asyncio.sleep(0.2)
        
        issues = []
        
        # Mock validation logic
        if "version" not in compose_yaml:
            issues.append("Missing version field in Docker Compose")
        
        if "services" not in compose_yaml:
            issues.append("No services defined in Docker Compose")
        
        if check_security:
            if "privileged: true" in compose_yaml:
                issues.append("Privileged containers are not allowed")
            
            if "/etc/" in compose_yaml:
                issues.append("Mounting system directories is discouraged")
        
        # Mock some warnings
        if "ports:" in compose_yaml and random.random() < 0.3:
            issues.append("Consider using specific port bindings instead of ranges")
        
        is_valid = len([issue for issue in issues if "not allowed" in issue]) == 0
        
        return is_valid, issues

    async def get_app_logs(
        self,
        app_name: str,
        lines: int = 100,
        service_name: Optional[str] = None,
    ) -> str:
        """Mock get Custom App logs."""
        logger.info("Mock: Getting app logs", app=app_name, lines=lines, service=service_name)
        await asyncio.sleep(0.3)
        
        if app_name not in self.mock_apps:
            return "App not found"
        
        # Generate mock logs
        mock_logs = []
        for i in range(min(lines, 20)):  # Limit to 20 lines for mock
            timestamp = f"2025-07-30T12:{30 + i:02d}:{random.randint(10, 59):02d}Z"
            level = random.choice(["INFO", "WARN", "ERROR", "DEBUG"])
            message = random.choice([
                "Service started successfully",
                "Processing request",
                "Database connection established",
                "Configuration loaded",
                "Health check passed",
                "Request completed",
                "Cache updated",
                "Background task finished",
            ])
            mock_logs.append(f"[{timestamp}] {level}: {message}")
        
        return "\\n".join(mock_logs)