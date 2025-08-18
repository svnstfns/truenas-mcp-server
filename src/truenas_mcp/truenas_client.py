"""TrueNAS API client for WebSocket communication."""

import asyncio
import json
from typing import Any, Dict, List, Optional, Tuple

import structlog
import websockets
from websockets.exceptions import ConnectionClosed, WebSocketException

logger = structlog.get_logger(__name__)


class TrueNASConnectionError(Exception):
    """TrueNAS connection error."""


class TrueNASAuthenticationError(Exception):
    """TrueNAS authentication error."""


class TrueNASAPIError(Exception):
    """TrueNAS API error."""


class TrueNASClient:
    """WebSocket client for TrueNAS Electric Eel API."""

    def __init__(
        self,
        host: str,
        api_key: str,
        port: int = 443,
        protocol: str = "wss",
        ssl_verify: bool = True,
    ) -> None:
        """Initialize TrueNAS client."""
        self.host = host
        self.api_key = api_key
        self.port = port
        self.protocol = protocol
        self.ssl_verify = ssl_verify
        
        self.websocket: Optional[websockets.WebSocketServerProtocol] = None
        self.authenticated = False
        self.request_id = 0
        
    @property
    def url(self) -> str:
        """Get WebSocket URL."""
        return f"{self.protocol}://{self.host}:{self.port}/api/current"

    async def connect(self) -> None:
        """Connect to TrueNAS WebSocket API."""
        try:
            logger.info("Connecting to TrueNAS", url=self.url)
            
            # WebSocket connection with SSL context handling
            ssl_context = None
            if not self.ssl_verify and self.protocol == "wss":
                import ssl
                logger.warning(
                    "SSL certificate verification is DISABLED. This is insecure and should only be used in development.",
                    host=self.host
                )
                ssl_context = ssl.create_default_context()
                ssl_context.check_hostname = False
                ssl_context.verify_mode = ssl.CERT_NONE
            
            self.websocket = await websockets.connect(
                self.url,
                ssl=ssl_context,
                ping_interval=30,
                ping_timeout=10,
            )
            
            # Authenticate with API key
            await self._authenticate()
            
            logger.info("Connected to TrueNAS successfully")
            
        except Exception as e:
            logger.error("Failed to connect to TrueNAS", error=str(e))
            raise TrueNASConnectionError(f"Connection failed: {e}")

    async def disconnect(self) -> None:
        """Disconnect from TrueNAS."""
        if self.websocket:
            await self.websocket.close()
            self.websocket = None
            self.authenticated = False
            logger.info("Disconnected from TrueNAS")

    async def _authenticate(self) -> None:
        """Authenticate with TrueNAS using API key."""
        auth_request = {
            "id": self._next_request_id(),
            "jsonrpc": "2.0",
            "method": "auth.login_with_api_key",
            "params": [self.api_key],
        }
        
        response = await self._send_request(auth_request)
        
        if "error" in response:
            raise TrueNASAuthenticationError(f"Authentication failed: {response['error']}")
        
        self.authenticated = True
        logger.info("Authenticated with TrueNAS successfully")

    def _next_request_id(self) -> int:
        """Get next request ID."""
        self.request_id += 1
        return self.request_id

    async def _send_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Send JSON-RPC request and return response."""
        if not self.websocket:
            raise TrueNASConnectionError("Not connected to TrueNAS")
        
        try:
            # Send request
            await self.websocket.send(json.dumps(request))
            
            # Receive response
            response_str = await self.websocket.recv()
            response = json.loads(response_str)
            
            logger.debug("API request/response", request=request, response=response)
            
            return response
            
        except ConnectionClosed:
            logger.error("WebSocket connection closed")
            raise TrueNASConnectionError("Connection closed")
        except WebSocketException as e:
            logger.error("WebSocket error", error=str(e))
            raise TrueNASConnectionError(f"WebSocket error: {e}")
        except json.JSONDecodeError as e:
            logger.error("Invalid JSON response", error=str(e))
            raise TrueNASAPIError(f"Invalid JSON: {e}")

    async def test_connection(self) -> bool:
        """Test connection to TrueNAS."""
        try:
            if not self.authenticated:
                await self.connect()
            
            # Simple API call to test connectivity
            request = {
                "id": self._next_request_id(),
                "jsonrpc": "2.0",
                "method": "core.ping",
                "params": [],
            }
            
            response = await self._send_request(request)
            return "error" not in response
            
        except Exception as e:
            logger.error("Connection test failed", error=str(e))
            return False

    async def list_custom_apps(self, status_filter: str = "all") -> List[Dict[str, Any]]:
        """List Custom Apps."""
        request = {
            "id": self._next_request_id(),
            "jsonrpc": "2.0",
            "method": "app.query",
            "params": [{}],  # Empty filter for all apps
        }
        
        response = await self._send_request(request)
        
        if "error" in response:
            raise TrueNASAPIError(f"Failed to list apps: {response['error']}")
        
        apps = response.get("result", [])
        
        # Filter by status if specified
        if status_filter != "all":
            apps = [app for app in apps if app.get("status") == status_filter]
        
        return apps

    async def get_app_status(self, app_name: str) -> str:
        """Get Custom App status."""
        request = {
            "id": self._next_request_id(),
            "jsonrpc": "2.0",
            "method": "app.get_instance",
            "params": [app_name],
        }
        
        response = await self._send_request(request)
        
        if "error" in response:
            raise TrueNASAPIError(f"Failed to get app status: {response['error']}")
        
        app_data = response.get("result", {})
        return app_data.get("status", "unknown")

    async def start_app(self, app_name: str) -> bool:
        """Start Custom App."""
        request = {
            "id": self._next_request_id(),
            "jsonrpc": "2.0",
            "method": "app.start",
            "params": [app_name],
        }
        
        response = await self._send_request(request)
        return "error" not in response

    async def stop_app(self, app_name: str) -> bool:
        """Stop Custom App."""
        request = {
            "id": self._next_request_id(),
            "jsonrpc": "2.0",
            "method": "app.stop",
            "params": [app_name],
        }
        
        response = await self._send_request(request)
        return "error" not in response

    async def deploy_app(
        self,
        app_name: str,
        compose_yaml: str,
        auto_start: bool = True,
    ) -> bool:
        """Deploy Custom App from Docker Compose."""
        # Convert Docker Compose to TrueNAS format
        from .compose_converter import DockerComposeConverter
        
        converter = DockerComposeConverter()
        app_config = await converter.convert(compose_yaml, app_name)
        
        request = {
            "id": self._next_request_id(),
            "jsonrpc": "2.0",
            "method": "app.create",
            "params": [app_config],
        }
        
        response = await self._send_request(request)
        
        if "error" in response:
            logger.error("App deployment failed", error=response["error"])
            return False
        
        # Start app if requested
        if auto_start:
            await self.start_app(app_name)
        
        return True

    async def update_app(
        self,
        app_name: str,
        compose_yaml: str,
        force_recreate: bool = False,
    ) -> bool:
        """Update Custom App."""
        from .compose_converter import DockerComposeConverter
        
        converter = DockerComposeConverter()
        app_config = await converter.convert(compose_yaml, app_name)
        
        request = {
            "id": self._next_request_id(),
            "jsonrpc": "2.0",
            "method": "app.update",
            "params": [app_name, app_config],
        }
        
        response = await self._send_request(request)
        return "error" not in response

    async def delete_app(self, app_name: str, delete_volumes: bool = False) -> bool:
        """Delete Custom App."""
        request = {
            "id": self._next_request_id(),
            "jsonrpc": "2.0",
            "method": "app.delete",
            "params": [app_name, delete_volumes],
        }
        
        response = await self._send_request(request)
        return "error" not in response

    async def validate_compose(
        self,
        compose_yaml: str,
        check_security: bool = True,
    ) -> Tuple[bool, List[str]]:
        """Validate Docker Compose YAML."""
        from .validators import ComposeValidator
        
        validator = ComposeValidator()
        return await validator.validate(compose_yaml, check_security)

    async def get_app_logs(
        self,
        app_name: str,
        lines: int = 100,
        service_name: Optional[str] = None,
    ) -> str:
        """Get Custom App logs."""
        # Get container IDs for the app
        container_request = {
            "id": self._next_request_id(),
            "jsonrpc": "2.0",
            "method": "app.container_ids",
            "params": [app_name],
        }
        
        response = await self._send_request(container_request)
        
        if "error" in response:
            raise TrueNASAPIError(f"Failed to get container IDs: {response['error']}")
        
        container_ids = response.get("result", [])
        
        if not container_ids:
            return "No containers found for this app"
        
        # Get logs from first container (or specific service)
        container_id = container_ids[0]  # Simplified for now
        
        # Note: Actual log retrieval would need additional API methods
        # This is a placeholder implementation
        return f"Logs for {app_name} (container {container_id}):\\n[Log retrieval not fully implemented in TrueNAS API]"