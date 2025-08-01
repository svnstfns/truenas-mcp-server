"""Tests for main MCP server functionality."""

import os
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from truenas_mcp.mcp_server import TrueNASMCPServer
from truenas_mcp.mock_client import MockTrueNASClient


class TestTrueNASMCPServer:
    """Test MCP server functionality."""

    @pytest.fixture
    def mock_env(self):
        """Mock environment variables."""
        env_vars = {
            "TRUENAS_HOST": "test.example.com",
            "TRUENAS_API_KEY": "test-api-key",
            "TRUENAS_PORT": "443",
            "TRUENAS_PROTOCOL": "wss",
            "TRUENAS_SSL_VERIFY": "false",
            "DEBUG_MODE": "true",
            "MOCK_TRUENAS": "true",
        }
        
        with patch.dict(os.environ, env_vars, clear=False):
            yield env_vars

    @pytest.fixture
    def server(self, mock_env):
        """Create MCP server instance."""
        return TrueNASMCPServer()

    def test_server_initialization(self, server):
        """Test server initialization with environment variables."""
        assert server.config["truenas_host"] == "test.example.com"
        assert server.config["truenas_api_key"] == "test-api-key"
        assert server.config["truenas_port"] == 443
        assert server.config["truenas_protocol"] == "wss"
        assert server.config["ssl_verify"] is False
        assert server.config["debug_mode"] is True
        assert server.config["mock_mode"] is True

    def test_server_initialization_defaults(self):
        """Test server initialization with default values."""
        with patch.dict(os.environ, {}, clear=True):
            server = TrueNASMCPServer()
            
            assert server.config["truenas_host"] == "nas.pvnkn3t.lan"
            assert server.config["truenas_api_key"] is None
            assert server.config["truenas_port"] == 443
            assert server.config["truenas_protocol"] == "wss"
            assert server.config["ssl_verify"] is True
            assert server.config["debug_mode"] is False
            assert server.config["mock_mode"] is False

    @pytest.mark.asyncio
    async def test_initialize_clients_mock_mode(self, server):
        """Test client initialization in mock mode."""
        await server._initialize_clients()
        
        assert server.truenas_client is not None
        assert isinstance(server.truenas_client, MockTrueNASClient)
        assert server.tools_handler is not None

    @pytest.mark.asyncio
    async def test_initialize_clients_real_mode_no_api_key(self):
        """Test client initialization in real mode without API key."""
        with patch.dict(os.environ, {"MOCK_TRUENAS": "false"}, clear=False):
            server = TrueNASMCPServer()
            
            with pytest.raises(ValueError, match="TRUENAS_API_KEY environment variable required"):
                await server._initialize_clients()

    @pytest.mark.asyncio
    @patch('truenas_mcp.mcp_server.TrueNASClient')
    async def test_initialize_clients_real_mode_with_api_key(self, mock_client_class):
        """Test client initialization in real mode with API key."""
        mock_client = AsyncMock()
        mock_client_class.return_value = mock_client
        
        env_vars = {
            "TRUENAS_HOST": "test.example.com",
            "TRUENAS_API_KEY": "test-api-key",
            "MOCK_TRUENAS": "false",
        }
        
        with patch.dict(os.environ, env_vars, clear=False):
            server = TrueNASMCPServer()
            await server._initialize_clients()
            
            # Check client was created with correct parameters
            mock_client_class.assert_called_once_with(
                host="test.example.com",
                api_key="test-api-key",
                port=443,
                protocol="wss",
                ssl_verify=True,
            )
            
            # Check client connect was called
            mock_client.connect.assert_called_once()
            
            assert server.truenas_client == mock_client
            assert server.tools_handler is not None

    @pytest.mark.asyncio
    async def test_cleanup(self, server):
        """Test server cleanup."""
        # Initialize client
        await server._initialize_clients()
        
        mock_client = server.truenas_client
        mock_client.disconnect = AsyncMock()
        
        await server.cleanup()
        
        mock_client.disconnect.assert_called_once()

    @pytest.mark.asyncio
    async def test_cleanup_no_client(self, server):
        """Test server cleanup without initialized client."""
        # Should not raise exception
        await server.cleanup()

    @pytest.mark.asyncio
    @patch('truenas_mcp.mcp_server.stdio_server')
    async def test_run_method(self, mock_stdio_server, server):
        """Test server run method."""
        mock_streams = (AsyncMock(), AsyncMock())
        mock_stdio_server.return_value.__aenter__.return_value = mock_streams
        
        server.server.run = AsyncMock()
        
        await server.run(*mock_streams)
        
        server.server.run.assert_called_once_with(*mock_streams)

    @pytest.mark.asyncio
    async def test_mcp_handlers_integration(self, server):
        """Test MCP protocol handlers integration."""
        # Initialize the server
        await server._initialize_clients()
        
        # Test that handlers are registered
        assert hasattr(server.server, '_handlers')
        
        # The handlers should be able to list tools
        tools = await server.tools_handler.list_tools()
        assert len(tools) > 0
        
        # The handlers should be able to call tools
        result = await server.tools_handler.call_tool("test_connection", {})
        assert result.type == "text"


class TestMCPHandlers:
    """Test MCP protocol handlers."""

    @pytest.fixture
    async def initialized_server(self):
        """Create and initialize MCP server."""
        with patch.dict(os.environ, {"MOCK_TRUENAS": "true"}, clear=False):
            server = TrueNASMCPServer()
            await server._initialize_clients()
            return server

    @pytest.mark.asyncio
    async def test_list_tools_handler(self, initialized_server):
        """Test list_tools MCP handler."""
        # Get the registered handler
        list_tools_handler = None
        for handler_info in initialized_server.server._handlers.get('list_tools', []):
            list_tools_handler = handler_info.func
            break
        
        assert list_tools_handler is not None
        
        # Call the handler
        tools = await list_tools_handler()
        
        assert isinstance(tools, list)
        assert len(tools) > 0
        
        # Check tool structure
        for tool in tools:
            assert hasattr(tool, 'name')
            assert hasattr(tool, 'description')
            assert hasattr(tool, 'inputSchema')

    @pytest.mark.asyncio
    async def test_call_tool_handler(self, initialized_server):
        """Test call_tool MCP handler."""
        # Get the registered handler
        call_tool_handler = None
        for handler_info in initialized_server.server._handlers.get('call_tool', []):
            call_tool_handler = handler_info.func
            break
        
        assert call_tool_handler is not None
        
        # Call the handler with test_connection tool
        result = await call_tool_handler("test_connection", {})
        
        assert hasattr(result, 'type')
        assert hasattr(result, 'text')
        assert result.type == "text"
        assert "✅" in result.text

    @pytest.mark.asyncio
    async def test_call_tool_handler_with_args(self, initialized_server):
        """Test call_tool handler with arguments."""
        call_tool_handler = None
        for handler_info in initialized_server.server._handlers.get('call_tool', []):
            call_tool_handler = handler_info.func
            break
        
        # Call with list_custom_apps tool and arguments
        result = await call_tool_handler("list_custom_apps", {"status_filter": "running"})
        
        assert result.type == "text"
        assert "Custom Apps:" in result.text

    @pytest.mark.asyncio
    async def test_handler_initialization_lazy_loading(self):
        """Test that handlers initialize clients lazily."""
        with patch.dict(os.environ, {"MOCK_TRUENAS": "true"}, clear=False):
            server = TrueNASMCPServer()
            
            # Clients should not be initialized yet
            assert server.truenas_client is None
            assert server.tools_handler is None
            
            # Get the list_tools handler
            list_tools_handler = None
            for handler_info in server.server._handlers.get('list_tools', []):
                list_tools_handler = handler_info.func
                break
            
            # Call the handler - should trigger initialization
            tools = await list_tools_handler()
            
            # Now clients should be initialized
            assert server.truenas_client is not None
            assert server.tools_handler is not None
            assert len(tools) > 0


class TestMainFunction:
    """Test main entry point function."""

    @pytest.mark.asyncio
    @patch('truenas_mcp.mcp_server.stdio_server')
    @patch('truenas_mcp.mcp_server.TrueNASMCPServer')
    async def test_main_normal_execution(self, mock_server_class, mock_stdio_server):
        """Test normal main function execution."""
        from truenas_mcp.mcp_server import main
        
        # Mock server instance
        mock_server = AsyncMock()
        mock_server_class.return_value = mock_server
        
        # Mock stdio streams
        mock_streams = (AsyncMock(), AsyncMock())
        mock_stdio_server.return_value.__aenter__.return_value = mock_streams
        
        # Run main
        await main()
        
        # Verify server was created and run
        mock_server_class.assert_called_once()
        mock_server.run.assert_called_once_with(*mock_streams)
        mock_server.cleanup.assert_called_once()

    @pytest.mark.asyncio
    @patch('truenas_mcp.mcp_server.stdio_server')
    @patch('truenas_mcp.mcp_server.TrueNASMCPServer')
    async def test_main_keyboard_interrupt(self, mock_server_class, mock_stdio_server):
        """Test main function with keyboard interrupt."""
        from truenas_mcp.mcp_server import main
        
        # Mock server instance
        mock_server = AsyncMock()
        mock_server.run.side_effect = KeyboardInterrupt("Test interrupt")
        mock_server_class.return_value = mock_server
        
        # Mock stdio streams
        mock_streams = (AsyncMock(), AsyncMock())
        mock_stdio_server.return_value.__aenter__.return_value = mock_streams
        
        # Run main - should handle KeyboardInterrupt gracefully
        await main()
        
        # Verify cleanup was still called
        mock_server.cleanup.assert_called_once()

    @pytest.mark.asyncio
    @patch('truenas_mcp.mcp_server.stdio_server')
    @patch('truenas_mcp.mcp_server.TrueNASMCPServer')
    @patch('sys.exit')
    async def test_main_exception_handling(self, mock_exit, mock_server_class, mock_stdio_server):
        """Test main function exception handling."""
        from truenas_mcp.mcp_server import main
        
        # Mock server instance
        mock_server = AsyncMock()
        mock_server.run.side_effect = Exception("Test error")
        mock_server_class.return_value = mock_server
        
        # Mock stdio streams
        mock_streams = (AsyncMock(), AsyncMock())
        mock_stdio_server.return_value.__aenter__.return_value = mock_streams
        
        # Run main - should handle exception and exit
        await main()
        
        # Verify cleanup was called and sys.exit was called with error code
        mock_server.cleanup.assert_called_once()
        mock_exit.assert_called_once_with(1)