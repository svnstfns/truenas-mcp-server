#!/usr/bin/env node

/**
 * TrueNAS Scale MCP Server
 * 
 * A Model Context Protocol server for TrueNAS Scale integration
 */

import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import { 
  CallToolRequestSchema, 
  ListToolsRequestSchema,
  Tool 
} from '@modelcontextprotocol/sdk/types.js';

import { TrueNASClient } from './truenas/client.js';
import { setupContainerHandlers } from './handlers/containers.js';
import { setupDatasetHandlers } from './handlers/datasets.js';
import { setupSystemHandlers } from './handlers/system.js';

class TrueNASMCPServer {
  private server: Server;
  private trueNASClient: TrueNASClient;
  private tools: Map<string, Tool> = new Map();

  constructor() {
    this.server = new Server(
      {
        name: 'truenas-scale-mcp',
        version: '1.0.0',
      },
      {
        capabilities: {
          tools: {},
        },
      }
    );

    this.trueNASClient = new TrueNASClient({
      host: process.env.TRUENAS_HOST || 'localhost',
      port: parseInt(process.env.TRUENAS_PORT || '80'),
      apiKey: process.env.TRUENAS_API_KEY || '',
      https: process.env.TRUENAS_HTTPS === 'true',
    });

    this.setupHandlers();
  }

  private setupHandlers(): void {
    // Setup tool handlers
    setupContainerHandlers(this.server, this.trueNASClient, this.tools);
    setupDatasetHandlers(this.server, this.trueNASClient, this.tools);
    setupSystemHandlers(this.server, this.trueNASClient, this.tools);

    // List tools handler
    this.server.setRequestHandler(ListToolsRequestSchema, async () => {
      return {
        tools: Array.from(this.tools.values()),
      };
    });

    // Call tool handler
    this.server.setRequestHandler(CallToolRequestSchema, async (request) => {
      const { name, arguments: args } = request.params;
      
      // Handle tool calls based on name
      // This will be implemented by the specific handlers
      throw new Error(`Unknown tool: ${name}`);
    });
  }

  async start(): Promise<void> {
    const transport = new StdioServerTransport();
    await this.server.connect(transport);
    
    console.error('TrueNAS Scale MCP Server running on stdio');
  }
}

// Start the server
const server = new TrueNASMCPServer();
server.start().catch((error) => {
  console.error('Failed to start TrueNAS MCP Server:', error);
  process.exit(1);
});