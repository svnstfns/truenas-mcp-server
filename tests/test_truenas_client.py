"""Tests for TrueNAS client implementations."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from truenas_mcp.truenas_client import (
    TrueNASClient,
    TrueNASConnectionError,
    TrueNASAuthenticationError,
    TrueNASAPIError,
)
from truenas_mcp.mock_client import MockTrueNASClient


class TestMockTrueNASClient:
    """Test mock TrueNAS client functionality."""

    @pytest.fixture
    async def mock_client(self):
        """Create mock client."""
        client = MockTrueNASClient()
        await client.connect()
        return client

    @pytest.mark.asyncio
    async def test_connection_lifecycle(self):
        """Test connection/disconnection lifecycle."""
        client = MockTrueNASClient()
        
        # Initially not connected
        assert not client.connected
        assert not client.authenticated
        
        # Connect
        await client.connect()
        assert client.connected
        assert client.authenticated
        
        # Disconnect
        await client.disconnect()
        assert not client.connected
        assert not client.authenticated

    @pytest.mark.asyncio
    async def test_test_connection(self, mock_client):
        """Test connection testing."""
        result = await mock_client.test_connection()
        assert result is True

    @pytest.mark.asyncio
    async def test_list_custom_apps_all(self, mock_client):
        """Test listing all Custom Apps."""
        apps = await mock_client.list_custom_apps("all")
        
        assert len(apps) == 3
        app_names = [app["name"] for app in apps]
        assert "nginx-demo" in app_names
        assert "plex-server" in app_names
        assert "home-assistant" in app_names

    @pytest.mark.asyncio
    async def test_list_custom_apps_running_filter(self, mock_client):
        """Test listing only running apps."""
        apps = await mock_client.list_custom_apps("running")
        
        running_apps = [app for app in apps if app["status"] == "running"]
        assert len(running_apps) == len(apps)  # All returned should be running

    @pytest.mark.asyncio
    async def test_get_app_status_existing(self, mock_client):
        """Test getting status of existing app."""
        status = await mock_client.get_app_status("nginx-demo")
        assert status == "running"

    @pytest.mark.asyncio
    async def test_get_app_status_nonexistent(self, mock_client):
        """Test getting status of nonexistent app raises exception."""
        with pytest.raises(Exception, match="not found"):
            await mock_client.get_app_status("nonexistent-app")

    @pytest.mark.asyncio
    async def test_start_app_existing(self, mock_client):
        """Test starting existing app."""
        result = await mock_client.start_app("plex-server")
        assert result is True
        
        # Verify status changed
        status = await mock_client.get_app_status("plex-server")
        assert status == "running"

    @pytest.mark.asyncio
    async def test_start_app_nonexistent(self, mock_client):
        """Test starting nonexistent app."""
        result = await mock_client.start_app("nonexistent-app")
        assert result is False

    @pytest.mark.asyncio
    async def test_stop_app_existing(self, mock_client):
        """Test stopping existing app."""
        result = await mock_client.stop_app("nginx-demo")
        assert result is True
        
        # Verify status changed
        status = await mock_client.get_app_status("nginx-demo")
        assert status == "stopped"

    @pytest.mark.asyncio
    async def test_deploy_app_success(self, mock_client):
        """Test successful app deployment."""
        compose_yaml = """
version: '3'
services:
  web:
    image: nginx:latest
"""
        
        result = await mock_client.deploy_app("new-app", compose_yaml, auto_start=True)
        assert result is True
        
        # Verify app was added
        apps = await mock_client.list_custom_apps("all")
        app_names = [app["name"] for app in apps]
        assert "new-app" in app_names

    @pytest.mark.asyncio
    async def test_update_app_existing(self, mock_client):
        """Test updating existing app."""
        compose_yaml = """
version: '3'
services:
  web:
    image: nginx:1.25
"""
        
        result = await mock_client.update_app("nginx-demo", compose_yaml, force_recreate=True)
        assert result is True

    @pytest.mark.asyncio
    async def test_delete_app_existing(self, mock_client):
        """Test deleting existing app."""
        result = await mock_client.delete_app("nginx-demo", delete_volumes=False)
        assert result is True
        
        # Verify app was removed
        apps = await mock_client.list_custom_apps("all")
        app_names = [app["name"] for app in apps]
        assert "nginx-demo" not in app_names

    @pytest.mark.asyncio
    async def test_validate_compose_valid(self, mock_client):
        """Test validating valid Docker Compose."""
        compose_yaml = """
version: '3'
services:
  web:
    image: nginx:latest
    ports:
      - "8080:80"
"""
        
        is_valid, issues = await mock_client.validate_compose(compose_yaml, check_security=True)
        assert is_valid is True
        assert isinstance(issues, list)

    @pytest.mark.asyncio
    async def test_validate_compose_invalid(self, mock_client):
        """Test validating invalid Docker Compose."""
        compose_yaml = "invalid yaml content"
        
        is_valid, issues = await mock_client.validate_compose(compose_yaml, check_security=True)
        assert is_valid is False
        assert len(issues) > 0

    @pytest.mark.asyncio
    async def test_get_app_logs_existing(self, mock_client):
        """Test getting logs from existing app."""
        logs = await mock_client.get_app_logs("nginx-demo", lines=50)
        
        assert isinstance(logs, str)
        assert len(logs) > 0
        assert "INFO" in logs or "WARN" in logs or "ERROR" in logs  # Mock logs contain these

    @pytest.mark.asyncio
    async def test_get_app_logs_nonexistent(self, mock_client):
        """Test getting logs from nonexistent app."""
        logs = await mock_client.get_app_logs("nonexistent-app", lines=50)
        assert logs == "App not found"


class TestTrueNASClient:
    """Test real TrueNAS client functionality."""

    @pytest.fixture
    def client_config(self):
        """Client configuration for testing."""
        return {
            "host": "test.example.com",
            "api_key": "test-api-key", 
            "port": 443,
            "protocol": "wss",
            "ssl_verify": False,
        }

    @pytest.fixture
    def truenas_client(self, client_config):
        """Create TrueNAS client for testing."""
        return TrueNASClient(**client_config)

    def test_client_initialization(self, truenas_client):
        """Test client initialization."""
        assert truenas_client.host == "test.example.com"
        assert truenas_client.api_key == "test-api-key"
        assert truenas_client.port == 443
        assert truenas_client.protocol == "wss"
        assert truenas_client.ssl_verify is False
        assert truenas_client.websocket is None
        assert truenas_client.authenticated is False

    def test_url_property(self, truenas_client):
        """Test URL property construction."""
        expected_url = "wss://test.example.com:443/api/current"
        assert truenas_client.url == expected_url

    @pytest.mark.asyncio
    @patch('websockets.connect')
    async def test_connect_success(self, mock_connect, truenas_client):
        """Test successful connection."""
        # Mock WebSocket connection
        mock_websocket = AsyncMock()
        mock_connect.return_value = mock_websocket
        
        # Mock authentication response
        auth_response = {"id": 1, "jsonrpc": "2.0", "result": True}
        mock_websocket.send.return_value = None
        mock_websocket.recv.return_value = '{"id": 1, "jsonrpc": "2.0", "result": true}'
        
        await truenas_client.connect()
        
        assert truenas_client.websocket is not None
        assert truenas_client.authenticated is True
        
        # Verify authentication call was made
        mock_websocket.send.assert_called()

    @pytest.mark.asyncio
    @patch('websockets.connect')
    async def test_connect_auth_failure(self, mock_connect, truenas_client):
        """Test connection with authentication failure."""
        mock_websocket = AsyncMock()
        mock_connect.return_value = mock_websocket
        
        # Mock authentication error response
        mock_websocket.send.return_value = None
        mock_websocket.recv.return_value = '{"id": 1, "jsonrpc": "2.0", "error": {"code": -1, "message": "Invalid API key"}}'
        
        with pytest.raises(TrueNASAuthenticationError, match="Authentication failed"):
            await truenas_client.connect()

    @pytest.mark.asyncio
    @patch('websockets.connect')
    async def test_connect_connection_failure(self, mock_connect, truenas_client):
        """Test connection failure."""
        mock_connect.side_effect = Exception("Connection refused")
        
        with pytest.raises(TrueNASConnectionError, match="Connection failed"):
            await truenas_client.connect()

    @pytest.mark.asyncio
    async def test_disconnect(self, truenas_client):
        """Test disconnection."""
        # Set up connected state
        mock_websocket = AsyncMock()
        truenas_client.websocket = mock_websocket
        truenas_client.authenticated = True
        
        await truenas_client.disconnect()
        
        assert truenas_client.websocket is None
        assert truenas_client.authenticated is False
        mock_websocket.close.assert_called_once()

    def test_next_request_id(self, truenas_client):
        """Test request ID generation."""
        assert truenas_client.request_id == 0
        
        id1 = truenas_client._next_request_id()
        assert id1 == 1
        assert truenas_client.request_id == 1
        
        id2 = truenas_client._next_request_id()
        assert id2 == 2
        assert truenas_client.request_id == 2

    @pytest.mark.asyncio
    async def test_send_request_success(self, truenas_client):
        """Test successful request sending."""
        mock_websocket = AsyncMock()
        truenas_client.websocket = mock_websocket
        
        request = {"id": 1, "jsonrpc": "2.0", "method": "test", "params": []}
        response_json = '{"id": 1, "jsonrpc": "2.0", "result": "success"}'
        
        mock_websocket.send.return_value = None
        mock_websocket.recv.return_value = response_json
        
        response = await truenas_client._send_request(request)
        
        assert response["result"] == "success"
        mock_websocket.send.assert_called_once()
        mock_websocket.recv.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_request_no_connection(self, truenas_client):
        """Test request sending without connection."""
        request = {"id": 1, "jsonrpc": "2.0", "method": "test", "params": []}
        
        with pytest.raises(TrueNASConnectionError, match="Not connected"):
            await truenas_client._send_request(request)

    @pytest.mark.asyncio
    async def test_test_connection_success(self, truenas_client):
        """Test successful connection test."""
        truenas_client.authenticated = True
        truenas_client._send_request = AsyncMock(return_value={"id": 1, "result": "pong"})
        
        result = await truenas_client.test_connection()
        assert result is True

    @pytest.mark.asyncio
    async def test_test_connection_failure(self, truenas_client):
        """Test failed connection test."""
        truenas_client._send_request = AsyncMock(side_effect=Exception("Connection error"))
        
        result = await truenas_client.test_connection()
        assert result is False

    @pytest.mark.asyncio
    async def test_list_custom_apps_success(self, truenas_client):
        """Test successful app listing."""
        mock_response = {
            "id": 1,
            "result": [
                {"name": "app1", "status": "running"},
                {"name": "app2", "status": "stopped"},
            ]
        }
        
        truenas_client._send_request = AsyncMock(return_value=mock_response)
        
        apps = await truenas_client.list_custom_apps("all")
        
        assert len(apps) == 2
        assert apps[0]["name"] == "app1"
        assert apps[1]["name"] == "app2"

    @pytest.mark.asyncio
    async def test_list_custom_apps_api_error(self, truenas_client):
        """Test app listing with API error."""
        mock_response = {
            "id": 1,
            "error": {"code": -1, "message": "API error"}
        }
        
        truenas_client._send_request = AsyncMock(return_value=mock_response)
        
        with pytest.raises(TrueNASAPIError, match="Failed to list apps"):
            await truenas_client.list_custom_apps("all")