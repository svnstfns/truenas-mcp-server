"""Tests for MCP tools implementation."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from truenas_mcp.mcp_tools import MCPToolsHandler
from truenas_mcp.mock_client import MockTrueNASClient


class TestMCPToolsHandler:
    """Test MCP tools functionality."""

    @pytest.fixture
    async def mock_client(self):
        """Create mock TrueNAS client."""
        return MockTrueNASClient()

    @pytest.fixture
    async def tools_handler(self, mock_client):
        """Create tools handler with mock client."""
        await mock_client.connect()
        return MCPToolsHandler(mock_client)

    @pytest.mark.asyncio
    async def test_list_tools(self, tools_handler):
        """Test tool listing returns all 11 tools."""
        tools = await tools_handler.list_tools()
        
        assert len(tools) == 11
        
        tool_names = [tool.name for tool in tools]
        expected_tools = [
            "test_connection",
            "list_custom_apps",
            "get_custom_app_status", 
            "start_custom_app",
            "stop_custom_app",
            "deploy_custom_app",
            "update_custom_app",
            "delete_custom_app",
            "validate_compose",
            "get_app_logs",
        ]
        
        for expected_tool in expected_tools:
            assert expected_tool in tool_names

    @pytest.mark.asyncio
    async def test_test_connection_success(self, tools_handler):
        """Test connection testing tool."""
        result = await tools_handler.call_tool("test_connection", {})
        
        assert result.type == "text"
        assert "✅" in result.text
        assert "connection successful" in result.text.lower()

    @pytest.mark.asyncio
    async def test_list_custom_apps_all(self, tools_handler):
        """Test listing all Custom Apps."""
        result = await tools_handler.call_tool("list_custom_apps", {"status_filter": "all"})
        
        assert result.type == "text"
        assert "Custom Apps:" in result.text
        assert "nginx-demo" in result.text
        assert "plex-server" in result.text
        assert "home-assistant" in result.text

    @pytest.mark.asyncio
    async def test_list_custom_apps_running_only(self, tools_handler):
        """Test listing only running Custom Apps."""
        result = await tools_handler.call_tool("list_custom_apps", {"status_filter": "running"})
        
        assert result.type == "text"
        assert "nginx-demo" in result.text
        assert "home-assistant" in result.text
        assert "plex-server" not in result.text  # This one is stopped

    @pytest.mark.asyncio
    async def test_get_custom_app_status(self, tools_handler):
        """Test getting Custom App status."""
        result = await tools_handler.call_tool("get_custom_app_status", {"app_name": "nginx-demo"})
        
        assert result.type == "text"
        assert "nginx-demo" in result.text
        assert "running" in result.text

    @pytest.mark.asyncio
    async def test_start_custom_app(self, tools_handler):
        """Test starting Custom App."""
        result = await tools_handler.call_tool("start_custom_app", {"app_name": "plex-server"})
        
        assert result.type == "text"
        assert "✅" in result.text
        assert "Started" in result.text
        assert "plex-server" in result.text

    @pytest.mark.asyncio
    async def test_stop_custom_app(self, tools_handler):
        """Test stopping Custom App."""
        result = await tools_handler.call_tool("stop_custom_app", {"app_name": "nginx-demo"})
        
        assert result.type == "text"
        assert "✅" in result.text
        assert "Stopped" in result.text
        assert "nginx-demo" in result.text

    @pytest.mark.asyncio
    async def test_deploy_custom_app(self, tools_handler):
        """Test deploying new Custom App."""
        compose_yaml = """
version: '3'
services:
  web:
    image: nginx:latest
    ports:
      - "8080:80"
"""
        
        result = await tools_handler.call_tool("deploy_custom_app", {
            "app_name": "test-nginx",
            "compose_yaml": compose_yaml,
            "auto_start": True
        })
        
        assert result.type == "text"
        assert "✅" in result.text
        assert "Deployed" in result.text
        assert "test-nginx" in result.text

    @pytest.mark.asyncio
    async def test_update_custom_app(self, tools_handler):
        """Test updating existing Custom App."""
        compose_yaml = """
version: '3'
services:
  web:
    image: nginx:1.25
    ports:
      - "8080:80"
"""
        
        result = await tools_handler.call_tool("update_custom_app", {
            "app_name": "nginx-demo",
            "compose_yaml": compose_yaml,
            "force_recreate": False
        })
        
        assert result.type == "text"
        assert "✅" in result.text
        assert "Updated" in result.text
        assert "nginx-demo" in result.text

    @pytest.mark.asyncio
    async def test_delete_custom_app_confirmed(self, tools_handler):
        """Test deleting Custom App with confirmation."""
        result = await tools_handler.call_tool("delete_custom_app", {
            "app_name": "test-app",
            "delete_volumes": False,
            "confirm_deletion": True
        })
        
        assert result.type == "text"
        assert "✅" in result.text
        assert "Deleted" in result.text
        assert "test-app" in result.text

    @pytest.mark.asyncio
    async def test_delete_custom_app_not_confirmed(self, tools_handler):
        """Test deleting Custom App without confirmation fails."""
        result = await tools_handler.call_tool("delete_custom_app", {
            "app_name": "test-app",
            "delete_volumes": False,
            "confirm_deletion": False
        })
        
        assert result.type == "text"
        assert "❌" in result.text
        assert "not confirmed" in result.text.lower()

    @pytest.mark.asyncio
    async def test_validate_compose_valid(self, tools_handler):
        """Test validating valid Docker Compose."""
        compose_yaml = """
version: '3'
services:
  web:
    image: nginx:latest
    ports:
      - "8080:80"
"""
        
        result = await tools_handler.call_tool("validate_compose", {
            "compose_yaml": compose_yaml,
            "check_security": True
        })
        
        assert result.type == "text"
        assert "✅" in result.text
        assert "valid" in result.text.lower()

    @pytest.mark.asyncio
    async def test_get_app_logs(self, tools_handler):
        """Test getting Custom App logs."""
        result = await tools_handler.call_tool("get_app_logs", {
            "app_name": "nginx-demo",
            "lines": 50
        })
        
        assert result.type == "text"
        assert "Logs for" in result.text
        assert "nginx-demo" in result.text

    @pytest.mark.asyncio
    async def test_invalid_tool_name(self, tools_handler):
        """Test calling invalid tool name returns error."""
        result = await tools_handler.call_tool("invalid_tool", {})
        
        assert result.type == "text"
        assert "❌" in result.text
        assert "Unknown tool" in result.text

    @pytest.mark.asyncio
    async def test_tool_execution_error_handling(self, tools_handler):
        """Test error handling in tool execution."""
        # Mock the client to raise an exception
        tools_handler.client.get_app_status = AsyncMock(side_effect=Exception("Mock error"))
        
        result = await tools_handler.call_tool("get_custom_app_status", {"app_name": "test"})
        
        assert result.type == "text"
        assert "❌" in result.text
        assert "Error executing" in result.text


class TestToolSchemas:
    """Test MCP tool schema validation."""

    @pytest.fixture
    async def tools_handler(self):
        """Create tools handler."""
        mock_client = MockTrueNASClient()
        await mock_client.connect()
        return MCPToolsHandler(mock_client)

    @pytest.mark.asyncio
    async def test_all_tools_have_valid_schemas(self, tools_handler):
        """Test all tools have valid JSON schemas."""
        tools = await tools_handler.list_tools()
        
        for tool in tools:
            assert hasattr(tool, 'name')
            assert hasattr(tool, 'description')
            assert hasattr(tool, 'inputSchema')
            
            schema = tool.inputSchema
            assert isinstance(schema, dict)
            assert schema.get("type") == "object"
            assert "properties" in schema
            assert "additionalProperties" in schema
            assert schema["additionalProperties"] is False

    @pytest.mark.asyncio
    async def test_app_name_pattern_validation(self, tools_handler):
        """Test app name pattern in tool schemas."""
        tools = await tools_handler.list_tools()
        
        app_name_tools = [
            "get_custom_app_status",
            "start_custom_app", 
            "stop_custom_app",
            "deploy_custom_app",
            "update_custom_app",
            "delete_custom_app",
            "get_app_logs"
        ]
        
        for tool in tools:
            if tool.name in app_name_tools:
                app_name_prop = tool.inputSchema["properties"]["app_name"]
                assert app_name_prop["type"] == "string"
                assert "pattern" in app_name_prop
                assert app_name_prop["pattern"] == "^[a-z0-9][a-z0-9-]*[a-z0-9]$"