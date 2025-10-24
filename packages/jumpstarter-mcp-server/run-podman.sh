#!/bin/bash
set -e

# Change to the root of the jumpstarter repository
cd "$(dirname "$0")/../../"

# Build the container with Podman from the repository root
echo "Building Jumpstarter MCP Server container from repository root..."
podman build -t jumpstarter-mcp-server -f packages/jumpstarter-mcp-server/Containerfile .

# Check for existing Jumpstarter configuration
if [ -d "${HOME}/.config/jumpstarter" ]; then
    echo "Found Jumpstarter configuration directory"
    if [ -f "${HOME}/.config/jumpstarter/clients/${USER}.yaml" ]; then
        echo "Found client configuration for user: ${USER}"
    else
        echo "Warning: No client configuration found for user: ${USER}"
        echo "Available clients:"
        ls -la "${HOME}/.config/jumpstarter/clients/" 2>/dev/null || echo "No clients directory found"
    fi
else
    echo "Creating Jumpstarter configuration directory..."
    mkdir -p "${HOME}/.config/jumpstarter"
fi

# Create local share directory if it doesn't exist
mkdir -p "${HOME}/.local/share/jumpstarter"

# Run the container interactively for testing
echo "Running Jumpstarter MCP Server..."
podman run -it --rm \
    --name jumpstarter-mcp-server \
    -v "${HOME}/.config/jumpstarter:/home/jumpstarter/.config/jumpstarter:ro" \
    -v "${HOME}/.local/share/jumpstarter:/home/jumpstarter/.local/share/jumpstarter:ro" \
    -e JUMPSTARTER_CLIENT_ENDPOINT="${JUMPSTARTER_CLIENT_ENDPOINT:-}" \
    -e JUMPSTARTER_AUTH_TOKEN="${JUMPSTARTER_AUTH_TOKEN:-}" \
    jumpstarter-mcp-server