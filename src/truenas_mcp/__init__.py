"""TrueNAS Scale MCP Server.

A Model Context Protocol server for managing TrueNAS Scale Custom Apps
through Docker-based deployments.
"""

__version__ = "0.1.0"
__author__ = "TrueNAS MCP Project"

from .mcp_server import TrueNASMCPServer

__all__ = ["TrueNASMCPServer"]