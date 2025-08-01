"""Main MCP Server implementation for TrueNAS Scale Custom Apps."""

import asyncio
import os
import sys
from typing import Any, Dict, List

import structlog
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool

from .mcp_tools import MCPToolsHandler
from .truenas_client import TrueNASClient

logger = structlog.get_logger(__name__)


class TrueNASMCPServer:
    """MCP Server for TrueNAS Scale Custom Apps management."""

    def __init__(self) -> None:
        """Initialize the MCP server."""
        self.server = Server("truenas-scale-mcp")
        self.truenas_client: TrueNASClient | None = None
        self.tools_handler: MCPToolsHandler | None = None
        
        # Configuration from environment
        self.config = {
            "truenas_host": os.getenv("TRUENAS_HOST", "nas.pvnkn3t.lan"),
            "truenas_api_key": os.getenv("TRUENAS_API_KEY"),
            "truenas_port": int(os.getenv("TRUENAS_PORT", "443")),
            "truenas_protocol": os.getenv("TRUENAS_PROTOCOL", "wss"),
            "ssl_verify": os.getenv("TRUENAS_SSL_VERIFY", "true").lower() == "true",
            "debug_mode": os.getenv("DEBUG_MODE", "false").lower() == "true",
            "mock_mode": os.getenv("MOCK_TRUENAS", "false").lower() == "true",
        }
        
        # Setup logging
        self._setup_logging()
        
        # Register MCP handlers
        self._register_handlers()

    def _setup_logging(self) -> None:
        """Configure structured logging."""
        log_level = "DEBUG" if self.config["debug_mode"] else "INFO"
        
        structlog.configure(
            processors=[
                structlog.stdlib.filter_by_level,
                structlog.stdlib.add_logger_name,
                structlog.stdlib.add_log_level,
                structlog.stdlib.PositionalArgumentsFormatter(),
                structlog.processors.TimeStamper(fmt="iso"),
                structlog.processors.StackInfoRenderer(),
                structlog.processors.format_exc_info,
                structlog.processors.UnicodeDecoder(),
                structlog.processors.JSONRenderer(),
            ],
            context_class=dict,
            logger_factory=structlog.stdlib.LoggerFactory(),
            wrapper_class=structlog.stdlib.BoundLogger,
            cache_logger_on_first_use=True,
        )
        
        logger.info(
            "TrueNAS MCP Server initializing",
            host=self.config["truenas_host"],
            mock_mode=self.config["mock_mode"],
            debug_mode=self.config["debug_mode"],
        )

    def _register_handlers(self) -> None:
        """Register MCP protocol handlers."""
        
        @self.server.list_tools()
        async def list_tools() -> List[Tool]:
            """List available MCP tools."""
            if not self.tools_handler:
                await self._initialize_clients()
            return await self.tools_handler.list_tools()

        @self.server.call_tool()
        async def call_tool(name: str, arguments: Dict[str, Any]) -> Any:
            """Execute an MCP tool."""
            if not self.tools_handler:
                await self._initialize_clients()
            return await self.tools_handler.call_tool(name, arguments)

    async def _initialize_clients(self) -> None:
        """Initialize TrueNAS client and tools handler."""
        if self.config["mock_mode"]:
            from .mock_client import MockTrueNASClient
            self.truenas_client = MockTrueNASClient()
            logger.info("Using mock TrueNAS client for development")
        else:
            if not self.config["truenas_api_key"]:
                raise ValueError("TRUENAS_API_KEY environment variable required")
            
            self.truenas_client = TrueNASClient(
                host=self.config["truenas_host"],
                api_key=self.config["truenas_api_key"],
                port=self.config["truenas_port"],
                protocol=self.config["truenas_protocol"],
                ssl_verify=self.config["ssl_verify"],
            )
            
            # Test connection
            await self.truenas_client.connect()
            logger.info("Connected to TrueNAS", host=self.config["truenas_host"])
        
        # Initialize tools handler
        self.tools_handler = MCPToolsHandler(self.truenas_client)

    async def run(self, read_stream, write_stream) -> None:
        """Run the MCP server."""
        logger.info("Starting TrueNAS MCP Server")
        await self.server.run(read_stream, write_stream)

    async def cleanup(self) -> None:
        """Cleanup resources."""
        if self.truenas_client:
            await self.truenas_client.disconnect()
        logger.info("TrueNAS MCP Server shutdown complete")


async def main() -> None:
    """Main entry point for the MCP server."""
    server = TrueNASMCPServer()
    
    try:
        async with stdio_server() as streams:
            await server.run(*streams)
    except KeyboardInterrupt:
        logger.info("Received shutdown signal")
    except Exception as e:
        logger.error("Server error", error=str(e), exc_info=True)
        sys.exit(1)
    finally:
        await server.cleanup()


if __name__ == "__main__":
    asyncio.run(main())