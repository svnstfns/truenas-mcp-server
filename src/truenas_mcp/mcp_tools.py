"""MCP Tools implementation for TrueNAS Scale Custom Apps."""

from typing import Any, Dict, List, Optional

import structlog
from mcp.types import TextContent, Tool
from pydantic import BaseModel, Field, validator

from .truenas_client import TrueNASClient

logger = structlog.get_logger(__name__)


class MCPToolsHandler:
    """Handler for all MCP tools."""

    def __init__(self, truenas_client: TrueNASClient) -> None:
        """Initialize tools handler."""
        self.client = truenas_client

    async def list_tools(self) -> List[Tool]:
        """List all available MCP tools."""
        return [
            # Connection Management
            Tool(
                name="test_connection",
                description="Test TrueNAS API connectivity and authentication",
                inputSchema={
                    "type": "object",
                    "properties": {},
                    "additionalProperties": False,
                },
            ),
            
            # Custom App Management
            Tool(
                name="list_custom_apps",
                description="List all Custom Apps with status information",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "status_filter": {
                            "type": "string",
                            "enum": ["running", "stopped", "error", "all"],
                            "default": "all",
                            "description": "Filter apps by status",
                        }
                    },
                    "additionalProperties": False,
                },
            ),
            
            Tool(
                name="get_custom_app_status",
                description="Get detailed status information for a specific Custom App",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "app_name": {
                            "type": "string",
                            "pattern": "^[a-z0-9][a-z0-9-]*[a-z0-9]$",
                            "minLength": 2,
                            "maxLength": 50,
                            "description": "Name of the Custom App",
                        }
                    },
                    "required": ["app_name"],
                    "additionalProperties": False,
                },
            ),
            
            Tool(
                name="start_custom_app",
                description="Start a stopped Custom App",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "app_name": {
                            "type": "string",
                            "pattern": "^[a-z0-9][a-z0-9-]*[a-z0-9]$",
                            "description": "Name of the Custom App to start",
                        }
                    },
                    "required": ["app_name"],
                    "additionalProperties": False,
                },
            ),
            
            Tool(
                name="stop_custom_app",
                description="Stop a running Custom App",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "app_name": {
                            "type": "string",
                            "pattern": "^[a-z0-9][a-z0-9-]*[a-z0-9]$",
                            "description": "Name of the Custom App to stop",
                        }
                    },
                    "required": ["app_name"],
                    "additionalProperties": False,
                },
            ),
            
            # Deployment Tools
            Tool(
                name="deploy_custom_app",
                description="Deploy a new Custom App from Docker Compose configuration",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "app_name": {
                            "type": "string",
                            "pattern": "^[a-z0-9][a-z0-9-]*[a-z0-9]$",
                            "minLength": 2,
                            "maxLength": 50,
                            "description": "Unique name for the Custom App",
                        },
                        "compose_yaml": {
                            "type": "string",
                            "minLength": 10,
                            "maxLength": 100000,
                            "description": "Docker Compose YAML content",
                        },
                        "auto_start": {
                            "type": "boolean",
                            "default": True,
                            "description": "Whether to start the app after deployment",
                        },
                    },
                    "required": ["app_name", "compose_yaml"],
                    "additionalProperties": False,
                },
            ),
            
            Tool(
                name="update_custom_app",
                description="Update an existing Custom App with new Docker Compose configuration",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "app_name": {
                            "type": "string",
                            "pattern": "^[a-z0-9][a-z0-9-]*[a-z0-9]$",
                            "description": "Name of the Custom App to update",
                        },
                        "compose_yaml": {
                            "type": "string",
                            "minLength": 10,
                            "maxLength": 100000,
                            "description": "New Docker Compose YAML content",
                        },
                        "force_recreate": {
                            "type": "boolean",
                            "default": False,
                            "description": "Force recreation of containers",
                        },
                    },
                    "required": ["app_name", "compose_yaml"],
                    "additionalProperties": False,
                },
            ),
            
            Tool(
                name="delete_custom_app",
                description="Delete a Custom App and optionally its data volumes",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "app_name": {
                            "type": "string",
                            "pattern": "^[a-z0-9][a-z0-9-]*[a-z0-9]$",
                            "description": "Name of the Custom App to delete",
                        },
                        "delete_volumes": {
                            "type": "boolean",
                            "default": False,
                            "description": "Whether to delete associated data volumes",
                        },
                        "confirm_deletion": {
                            "type": "boolean",
                            "description": "Safety confirmation for destructive operation",
                        },
                    },
                    "required": ["app_name", "confirm_deletion"],
                    "additionalProperties": False,
                },
            ),
            
            # Validation Tools
            Tool(
                name="validate_compose",
                description="Validate Docker Compose YAML for TrueNAS compatibility",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "compose_yaml": {
                            "type": "string",
                            "minLength": 10,
                            "maxLength": 100000,
                            "description": "Docker Compose YAML to validate",
                        },
                        "check_security": {
                            "type": "boolean",
                            "default": True,
                            "description": "Whether to perform security validation",
                        },
                    },
                    "required": ["compose_yaml"],
                    "additionalProperties": False,
                },
            ),
            
            Tool(
                name="get_app_logs",
                description="Retrieve logs from a Custom App",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "app_name": {
                            "type": "string",
                            "pattern": "^[a-z0-9][a-z0-9-]*[a-z0-9]$",
                            "description": "Name of the Custom App",
                        },
                        "lines": {
                            "type": "integer",
                            "minimum": 1,
                            "maximum": 1000,
                            "default": 100,
                            "description": "Number of log lines to retrieve",
                        },
                        "service_name": {
                            "type": "string",
                            "description": "Specific service within the app (optional)",
                        },
                    },
                    "required": ["app_name"],
                    "additionalProperties": False,
                },
            ),
        ]

    async def call_tool(self, name: str, arguments: Dict[str, Any]) -> TextContent:
        """Execute an MCP tool by name."""
        logger.info("Executing MCP tool", tool=name, args=arguments)
        
        try:
            # Connection Management Tools
            if name == "test_connection":
                return await self._test_connection()
            
            # Custom App Management Tools
            elif name == "list_custom_apps":
                return await self._list_custom_apps(
                    status_filter=arguments.get("status_filter", "all")
                )
            
            elif name == "get_custom_app_status":
                return await self._get_custom_app_status(arguments["app_name"])
            
            elif name == "start_custom_app":
                return await self._start_custom_app(arguments["app_name"])
            
            elif name == "stop_custom_app":
                return await self._stop_custom_app(arguments["app_name"])
            
            # Deployment Tools
            elif name == "deploy_custom_app":
                return await self._deploy_custom_app(
                    app_name=arguments["app_name"],
                    compose_yaml=arguments["compose_yaml"],
                    auto_start=arguments.get("auto_start", True),
                )
            
            elif name == "update_custom_app":
                return await self._update_custom_app(
                    app_name=arguments["app_name"],
                    compose_yaml=arguments["compose_yaml"],
                    force_recreate=arguments.get("force_recreate", False),
                )
            
            elif name == "delete_custom_app":
                return await self._delete_custom_app(
                    app_name=arguments["app_name"],
                    delete_volumes=arguments.get("delete_volumes", False),
                    confirm_deletion=arguments["confirm_deletion"],
                )
            
            # Validation Tools
            elif name == "validate_compose":
                return await self._validate_compose(
                    compose_yaml=arguments["compose_yaml"],
                    check_security=arguments.get("check_security", True),
                )
            
            elif name == "get_app_logs":
                return await self._get_app_logs(
                    app_name=arguments["app_name"],
                    lines=arguments.get("lines", 100),
                    service_name=arguments.get("service_name"),
                )
            
            else:
                raise ValueError(f"Unknown tool: {name}")
                
        except Exception as e:
            logger.error("Tool execution failed", tool=name, error=str(e), exc_info=True)
            return TextContent(
                type="text",
                text=f"❌ Error executing {name}: {str(e)}"
            )

    # Tool Implementation Methods (Stubs for now)
    
    async def _test_connection(self) -> TextContent:
        """Test TrueNAS connection."""
        success = await self.client.test_connection()
        if success:
            return TextContent(
                type="text",
                text="✅ TrueNAS connection successful"
            )
        else:
            return TextContent(
                type="text",
                text="❌ TrueNAS connection failed"
            )
    
    async def _list_custom_apps(self, status_filter: str) -> TextContent:
        """List Custom Apps."""
        apps = await self.client.list_custom_apps(status_filter)
        if not apps:
            return TextContent(
                type="text",
                text="No Custom Apps found"
            )
        
        result = "Custom Apps:\\n"
        for app in apps:
            result += f"- {app['name']}: {app['status']}\\n"
        
        return TextContent(type="text", text=result)
    
    async def _get_custom_app_status(self, app_name: str) -> TextContent:
        """Get Custom App status."""
        status = await self.client.get_app_status(app_name)
        return TextContent(
            type="text",
            text=f"App '{app_name}' status: {status}"
        )
    
    async def _start_custom_app(self, app_name: str) -> TextContent:
        """Start Custom App."""
        success = await self.client.start_app(app_name)
        if success:
            return TextContent(
                type="text",
                text=f"✅ Started Custom App '{app_name}'"
            )
        else:
            return TextContent(
                type="text",
                text=f"❌ Failed to start Custom App '{app_name}'"
            )
    
    async def _stop_custom_app(self, app_name: str) -> TextContent:
        """Stop Custom App."""
        success = await self.client.stop_app(app_name)
        if success:
            return TextContent(
                type="text",
                text=f"✅ Stopped Custom App '{app_name}'"
            )
        else:
            return TextContent(
                type="text",
                text=f"❌ Failed to stop Custom App '{app_name}'"
            )
    
    async def _deploy_custom_app(
        self,
        app_name: str,
        compose_yaml: str,
        auto_start: bool,
    ) -> TextContent:
        """Deploy Custom App."""
        success = await self.client.deploy_app(app_name, compose_yaml, auto_start)
        if success:
            return TextContent(
                type="text",
                text=f"✅ Deployed Custom App '{app_name}' successfully"
            )
        else:
            return TextContent(
                type="text",
                text=f"❌ Failed to deploy Custom App '{app_name}'"
            )
    
    async def _update_custom_app(
        self,
        app_name: str,
        compose_yaml: str,
        force_recreate: bool,
    ) -> TextContent:
        """Update Custom App."""
        success = await self.client.update_app(app_name, compose_yaml, force_recreate)
        if success:
            return TextContent(
                type="text",
                text=f"✅ Updated Custom App '{app_name}' successfully"
            )
        else:
            return TextContent(
                type="text",
                text=f"❌ Failed to update Custom App '{app_name}'"
            )
    
    async def _delete_custom_app(
        self,
        app_name: str,
        delete_volumes: bool,
        confirm_deletion: bool,
    ) -> TextContent:
        """Delete Custom App."""
        if not confirm_deletion:
            return TextContent(
                type="text",
                text="❌ Deletion not confirmed. Set confirm_deletion=true to proceed."
            )
        
        success = await self.client.delete_app(app_name, delete_volumes)
        if success:
            return TextContent(
                type="text",
                text=f"✅ Deleted Custom App '{app_name}' successfully"
            )
        else:
            return TextContent(
                type="text",
                text=f"❌ Failed to delete Custom App '{app_name}'"
            )
    
    async def _validate_compose(
        self,
        compose_yaml: str,
        check_security: bool,
    ) -> TextContent:
        """Validate Docker Compose."""
        is_valid, issues = await self.client.validate_compose(compose_yaml, check_security)
        
        if is_valid and not issues:
            return TextContent(
                type="text",
                text="✅ Docker Compose is valid and secure"
            )
        elif is_valid and issues:
            warnings = "\\n".join([f"⚠️ {issue}" for issue in issues])
            return TextContent(
                type="text",
                text=f"✅ Docker Compose is valid but has warnings:\\n{warnings}"
            )
        else:
            errors = "\\n".join([f"❌ {issue}" for issue in issues])
            return TextContent(
                type="text",
                text=f"❌ Docker Compose validation failed:\\n{errors}"
            )
    
    async def _get_app_logs(
        self,
        app_name: str,
        lines: int,
        service_name: Optional[str],
    ) -> TextContent:
        """Get Custom App logs."""
        logs = await self.client.get_app_logs(app_name, lines, service_name)
        
        if logs:
            return TextContent(
                type="text",
                text=f"Logs for '{app_name}':\\n{logs}"
            )
        else:
            return TextContent(
                type="text",
                text=f"No logs found for '{app_name}'"
            )