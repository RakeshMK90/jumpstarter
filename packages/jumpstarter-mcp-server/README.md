# Jumpstarter MCP Server

A Model Context Protocol (MCP) server built with **FastMCP** that provides access to Jumpstarter's hardware automation and testing capabilities.

## Overview

This MCP server exposes Jumpstarter's core functionality as MCP tools, allowing AI assistants like Claude to interact with hardware testing infrastructure. Built on the **FastMCP framework** for enhanced reliability and performance.

### Key Features
- 🚀 **FastMCP Framework**: Production-ready MCP implementation with improved error handling
- 🔧 **Hardware Management**: Discover and lease hardware resources
- 📊 **Real-time Status**: Monitor exporter and lease status
- ⚡ **Live Integration**: Direct integration with Jumpstarter APIs
- 🐳 **Containerized**: Ready for deployment with Podman/Docker

## Current Status (PoC)

✅ **Working Tools** (Production Ready):
- `jumpstarter_get_config` - Get Jumpstarter configuration
- `jumpstarter_list_exporters` - List available hardware exporters
- `jumpstarter_list_leases` - List active hardware leases
- `jumpstarter_create_lease` - Create new hardware leases

🚧 **Additional Tools** (PoC Implementation):
- Power control, serial console, storage flashing, SSH forwarding, and arbitrary j commands

## Architecture

### FastMCP Framework

This server uses **FastMCP** instead of the standard MCP library for several advantages:

- **Simplified Decorators**: Tools defined with simple `@mcp.tool` decorators
- **Better Error Handling**: Automatic error serialization and validation
- **Production Ready**: Designed for reliability in production environments
- **Cleaner Code**: Reduced boilerplate compared to standard MCP

```python
@mcp.tool
async def jumpstarter_list_exporters(
    selector: Optional[str] = None,
    include_leases: bool = False,
    include_online: bool = True
) -> str:
    """List available hardware exporters and their status"""
    # Implementation here...
```

### Container Deployment

The server is packaged as a container for easy deployment:

```dockerfile
FROM python:3.11-slim
# FastMCP server entry point
ENTRYPOINT ["uv", "run", "--directory", "packages/jumpstarter-mcp-server", "jumpstarter-fastmcp"]
```

## Installation & Usage

### Method 1: Container (Recommended)

```bash
# Build the container
cd /path/to/jumpstarter
podman build -t jumpstarter-mcp-server -f packages/jumpstarter-mcp-server/Containerfile .

# Run with your Jumpstarter config
podman run -it \
  -v ~/.config/jumpstarter:/home/jumpstarter/.config/jumpstarter:ro \
  jumpstarter-mcp-server
```

### Method 2: Development Setup

```bash
# Install from the Jumpstarter workspace
uv sync --all-packages
cd packages/jumpstarter-mcp-server

# Run FastMCP server
uv run jumpstarter-fastmcp
```

### Method 3: Claude Desktop/Cursor Integration

Add to your MCP configuration:

```json
{
  "mcpServers": {
    "jumpstarter": {
      "command": "podman",
      "args": [
        "run", "-i", "--rm",
        "-v", "/home/user/.config/jumpstarter:/home/jumpstarter/.config/jumpstarter:ro",
        "jumpstarter-mcp-server"
      ]
    }
  }
}
```

## Working Tools

### 🔧 `jumpstarter_get_config`
Get current Jumpstarter configuration information including endpoint, driver settings, and connection status.

**Example Response:**
```json
{
  "type": "ClientConfigV1Alpha1",
  "is_client_config": true,
  "endpoint": "grpc://jumpstarter.example.com:1234",
  "driver_allow_list": ["power", "console"],
  "unsafe_drivers": false
}
```

### 📋 `jumpstarter_list_exporters`
List available hardware exporters and their current status.

**Parameters:**
- `selector` (optional): Label selector to filter exporters (e.g., "board-type=j784s4evm")
- `include_leases` (bool): Include lease information (default: false)
- `include_online` (bool): Include online status (default: true)

**Example Response:**
```json
[
  {
    "name": "exporter-1",
    "labels": {"board-type": "j784s4evm", "enabled": "true"},
    "status": "online",
    "online": true
  }
]
```

### 📊 `jumpstarter_list_leases`
List active hardware leases with status and expiration information.

**Parameters:**
- `selector` (optional): Label selector to filter leases

**Example Response:**
```json
[
  {
    "id": "lease-abc123",
    "name": "test-lease",
    "status": "active",
    "expires_at": "2024-10-24T10:30:00Z"
  }
]
```

### ⚡ `jumpstarter_create_lease`
Create a new hardware lease for testing with automatic error handling for API compatibility.

**Parameters:**
- `selector`: Label selector for target hardware (required)
- `lease_name` (optional): Name for the lease
- `duration_minutes`: Lease duration in minutes (default: 30)

**Example Usage:**
```json
{
  "selector": "board-type=j784s4evm,enabled=true",
  "lease_name": "my-test-lease",
  "duration_minutes": 60
}
```

**Features:**
- ✅ Real API integration with Jumpstarter client
- ✅ Automatic parameter compatibility handling
- ✅ Robust error handling for different API versions
- ✅ Detailed lease information in response

## Configuration Requirements

The MCP server requires Jumpstarter client configuration. Ensure you have:

1. **Authentication**: Valid Jumpstarter credentials
2. **Client Config**: Either environment variables or user config file
3. **Network Access**: Connectivity to Jumpstarter endpoint

### Environment Variables
```bash
# Option 1: Environment variables
export JUMPSTARTER_ENDPOINT="grpc://your-jumpstarter-server:1234"
export JUMPSTARTER_TOKEN="your-auth-token"

# Option 2: Use existing user config (~/.config/jumpstarter/)
# No environment variables needed
```

## Troubleshooting

### Common Issues

**"No client configuration available"**
- Run `jmp login` to set up authentication
- Or set `JUMPSTARTER_ENDPOINT` and `JUMPSTARTER_TOKEN` environment variables

**"Failed to list exporters"**
- Check network connectivity to Jumpstarter endpoint
- Verify authentication token is valid and not expired

**Container build issues**
- Ensure you're building from the root jumpstarter directory
- Check that all git metadata is available for version detection

### Debug Mode

Run with debug logging:
```bash
# Container
podman run -e LOG_LEVEL=DEBUG jumpstarter-mcp-server

# Development
LOG_LEVEL=DEBUG uv run jumpstarter-fastmcp
```

## Development

### FastMCP Benefits

Compared to standard MCP, FastMCP provides:

- **Simpler Tool Definition**: Just decorators, no complex handler registration
- **Automatic Serialization**: No manual CallToolResult construction
- **Better Error Messages**: Automatic error formatting and logging
- **Type Safety**: Full Pydantic integration for request/response validation

### Adding New Tools

```python
@mcp.tool
async def new_jumpstarter_tool(param1: str, param2: Optional[int] = None) -> str:
    """Tool description for AI assistant"""
    try:
        # Your implementation
        result = do_something(param1, param2)
        return f"Success: {result}"
    except Exception as e:
        raise RuntimeError(f"Tool failed: {str(e)}")
```

### Testing

```bash
# Run tests
uv run pytest

# Build and test container
podman build -t jumpstarter-mcp-server -f packages/jumpstarter-mcp-server/Containerfile .
echo '{"jsonrpc": "2.0", "id": 1, "method": "tools/list"}' | podman run -i jumpstarter-mcp-server
```

## Roadmap

### Next Phase
- 🔄 **Lease Management**: Release and extend lease functionality
- 📡 **Real Command Execution**: Live shell and j command execution
- 🔌 **Driver Integration**: Hardware-specific tool implementations
- 📊 **Streaming Responses**: Real-time output for long-running operations

### Future Enhancements
- **Advanced Monitoring**: Resource usage and performance metrics
- **Test Orchestration**: Multi-device test execution workflows
- **Hardware Discovery**: Automatic device detection and labeling
- **Integration APIs**: Webhooks and event notifications

---

**Built with FastMCP** - Production-ready Model Context Protocol server for hardware automation.