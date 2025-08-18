# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Overview

This is a **TrueNAS MCP Server** - a Python implementation of the Model Context Protocol (MCP) designed to enable AI assistants to interact with TrueNAS storage systems. The server provides tools and resources for managing TrueNAS operations through a standardized protocol.

## Core Architecture

### MCP Implementation
- **Protocol**: Model Context Protocol for AI assistant integration
- **Target System**: TrueNAS Scale and Core storage platforms
- **Communication**: Standard MCP server/client architecture
- **Tools**: TrueNAS-specific operations and management functions

### Python Project Structure
- **Package Manager**: Poetry for dependency management and packaging
- **Layout**: Modern src-layout (`src/truenas_mcp/`)
- **Entry Point**: Poetry script `truenas-mcp-server`
- **Python Version**: 3.x (check pyproject.toml for specific requirements)

## Essential Commands

### Development Setup
```bash
# Install dependencies
poetry install

# Install development dependencies
poetry install --with dev

# Activate virtual environment
poetry shell
```

### Development Workflow
```bash
# Run the MCP server
poetry run truenas-mcp-server

# Alternative direct execution
poetry run python -m truenas_mcp
```

### Code Quality & Testing
```bash
# Format code
poetry run black src/ tests/

# Lint code
poetry run ruff check src/ tests/

# Type checking
poetry run mypy src/

# Run tests
poetry run pytest

# Run tests with coverage
poetry run pytest --cov=src/truenas_mcp --cov-report=term-missing

# All quality checks (recommended before commits)
poetry run black src/ tests/ && poetry run ruff check src/ tests/ && poetry run mypy src/ && poetry run pytest
```

### Build & Distribution
```bash
# Build package
poetry build

# Install locally for testing
pip install dist/*.whl
```

## Project-Specific Patterns

### TrueNAS Integration
- **API Client**: Integration with TrueNAS REST API
- **Authentication**: Handle TrueNAS authentication and sessions
- **Operations**: Storage, dataset, and system management functions
- **Monitoring**: System status and health monitoring

### MCP Server Patterns
- **Tool Definitions**: Schema-validated tool descriptions
- **Resource Handlers**: Dynamic resource discovery and access
- **Streaming**: Support for real-time data streaming
- **Logging**: Comprehensive logging for debugging and monitoring

## Development Environment

### Tool Configuration
- **Black**: Code formatting with 88-character line length
- **Ruff**: Fast Python linter with extensive rule set
- **MyPy**: Static type checking with strict configuration
- **pytest**: Testing framework with coverage reporting

### Testing Strategy
```bash
# Run all tests
poetry run pytest

# Run specific test categories
poetry run pytest tests/unit/
poetry run pytest tests/integration/

# Test with verbose output
poetry run pytest -v

# Test specific modules
poetry run pytest tests/test_server.py
```

## Key Development Practices

### Code Quality
- Use type hints consistently (enforced by MyPy)
- Follow Black formatting standards
- Address all Ruff linting warnings
- Maintain test coverage above 80%

### MCP Development
- Follow MCP protocol specifications strictly
- Implement proper error handling and validation
- Use schema validation for all tool inputs
- Provide comprehensive tool descriptions

### Security Considerations
- **Credentials**: Never commit TrueNAS credentials to repository
- **API Keys**: Use environment variables for sensitive configuration
- **Input Validation**: Sanitize all user inputs through MCP tools

## Debugging & Troubleshooting

### Debug Commands
```bash
# Run with debug logging
poetry run truenas-mcp-server --debug

# Validate configuration
poetry run python -c "import truenas_mcp; print('OK')"

# Check dependencies
poetry check
poetry show --tree
```

### Common Issues
- **Authentication**: Verify TrueNAS credentials and API access
- **Network**: Check TrueNAS system connectivity
- **Dependencies**: Ensure all Poetry dependencies are installed
- **MCP Protocol**: Validate tool and resource schemas