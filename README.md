# TrueNAS Scale MCP Server

A Model Context Protocol (MCP) server for managing TrueNAS Scale Custom Apps through Docker-based deployments.

## Overview

This MCP server enables AI assistants like Claude to manage TrueNAS Scale Custom Apps using natural language commands. It provides tools for deploying, managing, and monitoring Docker Compose applications on TrueNAS Scale systems.

## Features

- **11 MCP Tools** for comprehensive Custom App management
- **Docker Compose Conversion** to TrueNAS Custom App format
- **Security Validation** with input sanitization
- **Mock Development Mode** for testing without TrueNAS access
- **Comprehensive Test Suite** with >80% coverage
- **WebSocket API Integration** with TrueNAS Electric Eel

## Quick Start

### Prerequisites

- Python 3.10+
- Poetry for dependency management
- TrueNAS Scale 24.10+ (Electric Eel) with API access

### Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/truenas-mcp-server.git
cd truenas-mcp-server

# Install dependencies
poetry install

# Install pre-commit hooks (optional)
poetry run pre-commit install
```

### Configuration

Set up environment variables for your TrueNAS system:

```bash
export TRUENAS_HOST="nas.pvnkn3t.lan"
export TRUENAS_API_KEY="your-api-key-here"
export TRUENAS_PORT="443"
export TRUENAS_PROTOCOL="wss"
export TRUENAS_SSL_VERIFY="false"  # Use "true" for production
export DEBUG_MODE="false"
```

### Testing the Server

```bash
# Test with mock TrueNAS (no real TrueNAS required)
MOCK_TRUENAS=true poetry run python src/truenas_mcp/mcp_server.py

# Test with real TrueNAS
poetry run python src/truenas_mcp/mcp_server.py
```

## Claude Code Integration

Add this server to your Claude Code MCP configuration:

### Option 1: Direct Python Execution

Add to your `~/.claude/mcp-servers/production.json`:

```json
{
  "mcpServers": {
    "truenas-scale": {
      "type": "stdio",
      "command": "python",
      "args": ["/path/to/truenas-mcp-server/src/truenas_mcp/mcp_server.py"],
      "env": {
        "TRUENAS_HOST": "nas.pvnkn3t.lan",
        "TRUENAS_API_KEY": "your-api-key-here",
        "TRUENAS_PORT": "443",
        "TRUENAS_PROTOCOL": "wss",
        "TRUENAS_SSL_VERIFY": "false"
      }
    }
  }
}
```

### Option 2: Poetry Execution

```json
{
  "mcpServers": {
    "truenas-scale": {
      "type": "stdio",
      "command": "poetry",
      "args": ["run", "python", "src/truenas_mcp/mcp_server.py"],
      "cwd": "/path/to/truenas-mcp-server",
      "env": {
        "TRUENAS_HOST": "nas.pvnkn3t.lan",
        "TRUENAS_API_KEY": "your-api-key-here",
        "TRUENAS_PORT": "443",
        "TRUENAS_PROTOCOL": "wss",
        "TRUENAS_SSL_VERIFY": "false"
      }
    }
  }
}
```

## Usage Examples

Once configured, you can use these natural language commands with Claude:

```bash
# List all Custom Apps
claude "List all my TrueNAS Custom Apps and their status"

# Deploy a new app
claude "Deploy this docker-compose.yml as a Custom App named 'my-app'"

# Manage existing apps
claude "Stop the Custom App named 'plex'"
claude "Start the Custom App named 'nextcloud'"
claude "Show detailed status of Custom App 'jellyfin'"

# Get logs
claude "Show me the last 50 lines of logs from Custom App 'nginx'"

# Delete an app
claude "Delete the Custom App 'old-app' including its volumes"
```

## Available MCP Tools

### Connection Management
- `test_connection` - Test TrueNAS API connectivity

### Custom App Management
- `list_custom_apps` - List all Custom Apps with status
- `get_custom_app_status` - Get detailed app information
- `start_custom_app` - Start a stopped app
- `stop_custom_app` - Stop a running app

### Deployment Tools
- `deploy_custom_app` - Deploy new app from Docker Compose
- `update_custom_app` - Update existing app configuration
- `delete_custom_app` - Remove app and optionally its volumes

### Validation & Monitoring
- `validate_compose` - Validate Docker Compose for TrueNAS compatibility
- `get_app_logs` - Retrieve application logs

## Development

### Running Tests

```bash
# Run all tests
poetry run pytest

# Run with coverage
poetry run pytest --cov=src/truenas_mcp --cov-report=html

# Run specific test categories
poetry run pytest -m unit          # Unit tests only
poetry run pytest -m integration   # Integration tests only
```

### Code Quality

```bash
# Format code
poetry run black .

# Lint code
poetry run ruff check . --fix

# Type checking
poetry run mypy .

# Run all quality checks
poetry run pre-commit run --all-files
```

### Mock Development

For development without a TrueNAS system:

```bash
# Enable mock mode
export MOCK_TRUENAS=true

# Run the server
poetry run python src/truenas_mcp/mcp_server.py
```

## Docker Compose Conversion

The server automatically converts Docker Compose files to TrueNAS Custom App format:

### Supported Features
- Volume mounts (named volumes → IX volumes, bind mounts → host paths)
- Port forwarding (container ports → host ports)
- Environment variables
- Network configuration (bridge/host modes)
- Restart policies

### Security Validations
- Prevents privileged container mode
- Blocks dangerous system directory mounts
- Validates port conflicts
- Enforces resource limits

## Troubleshooting

### Connection Issues
```bash
# Test API connectivity
curl -k -H "Authorization: Bearer YOUR_API_KEY" https://nas.pvnkn3t.lan/api/v2.0/system/info

# Check WebSocket connection
export TRUENAS_HOST=nas.pvnkn3t.lan TRUENAS_API_KEY=your-key
poetry run python -c "
import asyncio
from src.truenas_mcp.truenas_client import TrueNASClient
asyncio.run(TrueNASClient().test_connection())
"
```

### Common Issues
- **"Connection refused"**: Check `TRUENAS_HOST` and `TRUENAS_PORT`
- **"Authentication failed"**: Verify `TRUENAS_API_KEY` is correct
- **"SSL verification failed"**: Set `TRUENAS_SSL_VERIFY=false` for self-signed certificates

## Architecture

```
┌─────────────────┐    MCP Protocol     ┌──────────────────┐    WebSocket API    ┌─────────────────┐
│   AI Assistant  │ ◄──────────────────► │ TrueNAS MCP      │ ◄──────────────────► │ TrueNAS Scale   │
│   (Claude.ai)   │    JSON-RPC 2.0     │ Server           │    auth + app.*     │ Electric Eel    │
└─────────────────┘                     └──────────────────┘                     └─────────────────┘
```

### Core Components
- **MCP Protocol Handler**: Manages client communication and capability exchange
- **TrueNAS API Client**: Handles WebSocket connection and authentication
- **Docker Compose Converter**: Transforms Docker Compose to TrueNAS Custom App format
- **Validation Engine**: Validates inputs and security constraints
- **Tool Registry**: Manages available tools and their schemas

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Make your changes
4. Run tests: `poetry run pytest`
5. Run quality checks: `poetry run pre-commit run --all-files`
6. Commit your changes: `git commit -m 'Add amazing feature'`
7. Push to the branch: `git push origin feature/amazing-feature`
8. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Requirements

This implementation fulfills the complete [TrueNAS MCP Requirements v2.0](docs/truenas_mcp_requirements.md) specification with:

- ✅ 11 MCP tools with JSON schema validation
- ✅ WebSocket API integration with TrueNAS Electric Eel
- ✅ Docker Compose to Custom App conversion
- ✅ Comprehensive security validation
- ✅ >80% test coverage
- ✅ Production-ready error handling and logging

## Support

For issues, questions, or contributions, please open an issue on GitHub.

---

**Status**: Production Ready ✅  
**MCP Protocol**: 2.0 Compatible  
**TrueNAS**: Electric Eel (24.10+) Compatible