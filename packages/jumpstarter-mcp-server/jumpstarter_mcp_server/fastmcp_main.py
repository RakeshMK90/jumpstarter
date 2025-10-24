#!/usr/bin/env python3
"""
Jumpstarter MCP Server using FastMCP
"""

import asyncio
import json
import logging
import os
import sys
from typing import Any, Dict, List, Optional

from fastmcp import FastMCP

from jumpstarter.config.client import ClientConfigV1Alpha1
from jumpstarter.config.exporter import ExporterConfigV1Alpha1
from jumpstarter.config.user import UserConfigV1Alpha1


logger = logging.getLogger(__name__)


def _load_client_config() -> ClientConfigV1Alpha1:
    """Load client configuration following the same logic as CLI tools"""
    try:
        # Try to create a config directly (will succeed if env vars are set)
        return ClientConfigV1Alpha1()
    except Exception:
        # Fall back to user config
        user_config = UserConfigV1Alpha1.load_or_create()
        if user_config.config.current_client is None:
            raise RuntimeError("No client configuration available. Please run 'jmp login' or set environment variables.")
        return user_config.config.current_client


# Initialize FastMCP server
mcp = FastMCP("jumpstarter-mcp-server")


@mcp.tool
async def jumpstarter_get_config() -> str:
    """Get current Jumpstarter configuration information"""
    try:
        config = _load_client_config()
        config_type = type(config).__name__

        config_info = {
            "type": config_type,
            "is_client_config": isinstance(config, ClientConfigV1Alpha1),
            "is_exporter_config": isinstance(config, ExporterConfigV1Alpha1),
        }

        if isinstance(config, ClientConfigV1Alpha1):
            # Try different possible attribute names for the config structure
            endpoint = 'unknown'
            for attr in ['client', 'Client', 'endpoint', 'server']:
                if hasattr(config, attr):
                    client_obj = getattr(config, attr)
                    if hasattr(client_obj, 'endpoint'):
                        endpoint = client_obj.endpoint
                        break
                    elif isinstance(client_obj, str):
                        endpoint = client_obj
                        break

            driver_allow = []
            unsafe_drivers = False
            for attr in ['drivers', 'Drivers', 'driver_config']:
                if hasattr(config, attr):
                    drivers_obj = getattr(config, attr)
                    if hasattr(drivers_obj, 'allow'):
                        driver_allow = drivers_obj.allow
                    if hasattr(drivers_obj, 'unsafe'):
                        unsafe_drivers = drivers_obj.unsafe
                    break

            config_info.update({
                "endpoint": endpoint,
                "driver_allow_list": driver_allow,
                "unsafe_drivers": unsafe_drivers,
                "config_attributes": [attr for attr in dir(config) if not attr.startswith('_')]
            })

        return f"Jumpstarter Configuration:\n{json.dumps(config_info, indent=2)}"
    except Exception as e:
        raise RuntimeError(f"Failed to load configuration: {str(e)}")


@mcp.tool
async def jumpstarter_list_exporters(
    selector: Optional[str] = None,
    include_leases: bool = False,
    include_online: bool = True
) -> str:
    """List available hardware exporters and their status"""
    try:
        config = await asyncio.to_thread(_load_client_config)

        if not isinstance(config, ClientConfigV1Alpha1):
            raise RuntimeError("Client configuration required for listing exporters")

        exporters = await asyncio.to_thread(
            config.list_exporters,
            filter=selector,
            include_leases=include_leases,
            include_online=include_online
        )

        # Debug: Let's see what we actually get
        logger.info(f"Exporters type: {type(exporters)}")
        logger.info(f"Exporters dir: {dir(exporters)}")

        # Handle ExporterList object
        try:
            if hasattr(exporters, 'exporters'):
                exporter_list = list(exporters.exporters)
            elif hasattr(exporters, 'items'):
                exporter_list = list(exporters.items)
            else:
                # Try to iterate directly
                exporter_list = list(exporters)
        except Exception as list_error:
            logger.error(f"Failed to convert exporters to list: {list_error}")
            exporter_list = []

        logger.info(f"Found {len(exporter_list)} exporters")
        if exporter_list:
            logger.info(f"First exporter type: {type(exporter_list[0])}")
            logger.info(f"First exporter dir: {dir(exporter_list[0])}")

        # Convert exporters to a more readable format
        exporter_data = []
        for exp in exporter_list:
            # Try different attribute names that might exist
            exporter_info = {}

            # Try common attribute patterns
            for name_attr in ['name', 'Name', 'id', 'identifier']:
                if hasattr(exp, name_attr):
                    exporter_info['name'] = getattr(exp, name_attr)
                    break
            else:
                exporter_info['name'] = 'unknown'

            for labels_attr in ['labels', 'Labels', 'metadata', 'tags']:
                if hasattr(exp, labels_attr):
                    labels = getattr(exp, labels_attr)
                    if isinstance(labels, dict):
                        exporter_info['labels'] = labels
                    else:
                        exporter_info['labels'] = {}
                    break
            else:
                exporter_info['labels'] = {}

            for status_attr in ['status', 'Status', 'state', 'State']:
                if hasattr(exp, status_attr):
                    exporter_info['status'] = getattr(exp, status_attr)
                    break
            else:
                exporter_info['status'] = 'unknown'

            for online_attr in ['online', 'Online', 'available', 'is_online']:
                if hasattr(exp, online_attr):
                    exporter_info['online'] = getattr(exp, online_attr)
                    break
            else:
                exporter_info['online'] = False

            # If we still don't have a name, try to extract it from string representation
            if exporter_info['name'] == 'unknown':
                exp_str = str(exp)
                if exp_str and exp_str != str(type(exp)):
                    exporter_info['name'] = exp_str

            exporter_data.append(exporter_info)

        return f"Available Exporters:\n{json.dumps(exporter_data, indent=2)}"
    except Exception as e:
        logger.exception("Error listing exporters")
        raise RuntimeError(f"Failed to list exporters: {str(e)}")


@mcp.tool
async def jumpstarter_list_leases(selector: Optional[str] = None) -> str:
    """List active hardware leases"""
    try:
        config = await asyncio.to_thread(_load_client_config)

        if not isinstance(config, ClientConfigV1Alpha1):
            raise RuntimeError("Client configuration required for listing leases")

        leases = await asyncio.to_thread(config.list_leases, filter=selector)

        # Debug: Let's see what we actually get for leases
        logger.info(f"Leases type: {type(leases)}")
        logger.info(f"Leases dir: {dir(leases)}")

        # Handle LeaseList object - similar to ExporterList
        try:
            if hasattr(leases, 'leases'):
                lease_list = list(leases.leases)
            elif hasattr(leases, 'items'):
                lease_list = list(leases.items)
            else:
                # Try to iterate directly
                lease_list = list(leases)
        except Exception as list_error:
            logger.error(f"Failed to convert leases to list: {list_error}")
            lease_list = []

        logger.info(f"Found {len(lease_list)} leases")
        if lease_list:
            logger.info(f"First lease type: {type(lease_list[0])}")
            logger.info(f"First lease dir: {dir(lease_list[0])}")

        # Convert leases to a more readable format
        lease_data = []
        for lease in lease_list:
            # Try different attribute names that might exist
            lease_info = {}

            # Try common attribute patterns for lease ID
            for id_attr in ['id', 'Id', 'ID', 'lease_id', 'identifier']:
                if hasattr(lease, id_attr):
                    lease_info['id'] = getattr(lease, id_attr)
                    break
            else:
                lease_info['id'] = 'unknown'

            # Try common attribute patterns for lease name
            for name_attr in ['name', 'Name', 'lease_name', 'title']:
                if hasattr(lease, name_attr):
                    lease_info['name'] = getattr(lease, name_attr)
                    break
            else:
                lease_info['name'] = 'unknown'

            # Try common attribute patterns for status
            for status_attr in ['status', 'Status', 'state', 'State']:
                if hasattr(lease, status_attr):
                    lease_info['status'] = getattr(lease, status_attr)
                    break
            else:
                lease_info['status'] = 'unknown'

            # Try common attribute patterns for expiration
            for expires_attr in ['expires_at', 'expiry', 'expiration', 'expires', 'end_time']:
                if hasattr(lease, expires_attr):
                    expires_val = getattr(lease, expires_attr)
                    lease_info['expires_at'] = str(expires_val) if expires_val else 'unknown'
                    break
            else:
                lease_info['expires_at'] = 'unknown'

            # If we still don't have an ID, try to extract it from string representation
            if lease_info['id'] == 'unknown':
                lease_str = str(lease)
                if lease_str and lease_str != str(type(lease)):
                    lease_info['id'] = lease_str

            lease_data.append(lease_info)

        return f"Active Leases:\n{json.dumps(lease_data, indent=2)}"
    except Exception as e:
        logger.exception("Error listing leases")
        raise RuntimeError(f"Failed to list leases: {str(e)}")


@mcp.tool
async def jumpstarter_create_lease(
    selector: str = "",
    lease_name: Optional[str] = None,
    duration_minutes: int = 30
) -> str:
    """Create a hardware lease for testing"""
    try:
        # Load config synchronously since _load_client_config is not async
        config = _load_client_config()

        if not isinstance(config, ClientConfigV1Alpha1):
            raise RuntimeError("Client configuration required for creating leases")

        if not selector:
            raise ValueError("Selector is required for creating a lease (e.g., 'board-type=j784s4evm,enabled=true')")

        # Use the client to create a real lease
        from datetime import timedelta
        duration = timedelta(minutes=duration_minutes)

        logger.info(f"Creating lease with selector: {selector}, duration: {duration_minutes} minutes")

        # Create the lease using the client API
        try:
            # Try with selector and duration first
            lease_request = await config.create_lease(
                selector=selector,
                duration=duration
            )
        except TypeError as e:
            if "unexpected keyword argument" in str(e):
                # If duration or other parameters are not supported, try with just selector
                logger.warning(f"Parameter not supported, trying with selector only: {e}")
                try:
                    lease_request = await config.create_lease(selector=selector)
                except TypeError as e2:
                    if "unexpected keyword argument" in str(e2):
                        # If even selector is not supported as keyword, try positional
                        logger.warning(f"Selector as keyword not supported, trying positional: {e2}")
                        lease_request = await config.create_lease(selector)
                    else:
                        raise
            else:
                raise

        # Extract lease information
        lease_info = {
            "lease_id": getattr(lease_request, 'id', 'unknown'),
            "selector": selector,
            "lease_name": lease_name or getattr(lease_request, 'name', 'unknown'),
            "duration_minutes": duration_minutes,
            "status": getattr(lease_request, 'status', 'unknown'),
            "created_at": str(getattr(lease_request, 'created_at', 'unknown')),
            "expires_at": str(getattr(lease_request, 'expires_at', 'unknown'))
        }

        # Try to get more attributes if available
        if hasattr(lease_request, '__dict__'):
            for attr_name in ['lease_id', 'state', 'exporter_name']:
                if hasattr(lease_request, attr_name):
                    lease_info[attr_name] = getattr(lease_request, attr_name)

        return f"Lease Created Successfully!\n{json.dumps(lease_info, indent=2)}\n\nYou can now use this lease with other Jumpstarter tools by referencing the lease_id."

    except Exception as e:
        logger.exception("Error creating lease")
        raise RuntimeError(f"Failed to create lease: {str(e)}")


@mcp.tool
async def jumpstarter_execute_shell(
    command: List[str],
    selector: str = "",
    lease_name: Optional[str] = None
) -> str:
    """Execute shell commands on leased hardware"""
    try:
        # This is a PoC implementation - would need proper lease management
        # and shell execution integration
        command_info = {
            "command": command,
            "selector": selector,
            "lease_name": lease_name,
            "status": "Would execute command with these parameters"
        }

        return f"Shell Execution Request:\n{json.dumps(command_info, indent=2)}\n\nNote: This is a PoC - actual command execution would require lease management and proper shell integration."
    except Exception as e:
        raise RuntimeError(f"Failed to execute shell command: {str(e)}")


@mcp.tool
async def jumpstarter_power_control(action: str, lease_id: Optional[str] = None) -> str:
    """Control hardware power (on/off/cycle) using j power commands"""
    if action not in ["on", "off", "cycle"]:
        raise ValueError("Action must be one of: on, off, cycle")

    try:
        env_vars = {"JMP_LEASE": lease_id} if lease_id else {}

        # Execute j power command
        process = await asyncio.create_subprocess_exec(
            "j", "power", action,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env={**os.environ, **env_vars}
        )

        stdout, stderr = await process.communicate()

        if process.returncode == 0:
            result = f"Power {action} command executed successfully"
            if stdout:
                result += f"\nOutput: {stdout.decode()}"
        else:
            result = f"Power {action} command failed (exit code: {process.returncode})"
            if stderr:
                result += f"\nError: {stderr.decode()}"

        return result
    except Exception as e:
        raise RuntimeError(f"Failed to execute power {action}: {str(e)}")


@mcp.tool
async def jumpstarter_serial_console(
    action: str,
    command: Optional[str] = None,
    lease_id: Optional[str] = None
) -> str:
    """Start or interact with serial console (like j serial start-console)"""
    if action not in ["start", "send_command", "info"]:
        raise ValueError("Action must be one of: start, send_command, info")

    try:
        env_vars = {"JMP_LEASE": lease_id} if lease_id else {}

        if action == "start":
            result = "To start serial console interactively, use: j serial start-console\n"
            result += "Note: MCP server cannot provide interactive console access.\n"
            result += "Use jumpstarter_serial_console with action='send_command' to send specific commands."

        elif action == "send_command":
            if not command:
                raise ValueError("command parameter required for send_command action")

            # This is a simplified implementation - real implementation would need
            # to maintain persistent serial connections
            result = f"Would send command to serial console: {command}\n"
            result += "Note: This is a PoC - actual implementation requires persistent connection management."

        elif action == "info":
            # Get serial port information
            process = await asyncio.create_subprocess_exec(
                "j", "serial", "--help",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env={**os.environ, **env_vars}
            )

            stdout, stderr = await process.communicate()
            result = f"Serial console information:\n{stdout.decode() if stdout else 'No output'}"

        return result
    except Exception as e:
        raise RuntimeError(f"Failed to execute serial console action: {str(e)}")


@mcp.tool
async def jumpstarter_storage_flash(
    image_url: str,
    target: Optional[str] = None,
    console_debug: bool = False,
    lease_id: Optional[str] = None
) -> str:
    """Flash an image to target storage (like j storage flash)"""
    try:
        env_vars = {"JMP_LEASE": lease_id} if lease_id else {}

        cmd = ["j", "storage", "flash"]
        if target:
            cmd.extend(["--target", target])
        if console_debug:
            cmd.append("--console-debug")
        cmd.append(image_url)

        result_info = {
            "command": " ".join(cmd),
            "image_url": image_url,
            "target": target,
            "console_debug": console_debug,
            "status": "Would execute flash command with these parameters"
        }

        return f"Storage Flash Request:\n{json.dumps(result_info, indent=2)}\n\nNote: This is a PoC - actual flashing would execute the j command and stream progress."
    except Exception as e:
        raise RuntimeError(f"Failed to execute storage flash: {str(e)}")


@mcp.tool
async def jumpstarter_ssh_forward(
    local_port: int = 2222,
    action: str = "start",
    lease_id: Optional[str] = None
) -> str:
    """Set up SSH port forwarding to DUT (like j ssh forward-tcp)"""
    if action not in ["start", "stop", "status"]:
        raise ValueError("Action must be one of: start, stop, status")

    try:
        env_vars = {"JMP_LEASE": lease_id} if lease_id else {}

        if action == "start":
            cmd = ["j", "ssh", "forward-tcp", str(local_port)]
            result_info = {
                "action": "start_forwarding",
                "local_port": local_port,
                "command": " ".join(cmd),
                "usage": f"ssh -p {local_port} -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null root@localhost",
                "status": "Would start port forwarding"
            }

        elif action == "status":
            result_info = {
                "action": "check_status",
                "local_port": local_port,
                "status": "Would check forwarding status"
            }

        elif action == "stop":
            result_info = {
                "action": "stop_forwarding",
                "local_port": local_port,
                "status": "Would stop port forwarding"
            }

        return f"SSH Port Forwarding:\n{json.dumps(result_info, indent=2)}\n\nNote: This is a PoC - actual implementation would manage background forwarding processes."
    except Exception as e:
        raise RuntimeError(f"Failed to execute SSH forwarding: {str(e)}")


@mcp.tool
async def jumpstarter_run_j_command(command: List[str], lease_id: Optional[str] = None) -> str:
    """Execute arbitrary j commands within a lease context"""
    try:
        env_vars = {"JMP_LEASE": lease_id} if lease_id else {}

        # Execute the j command
        process = await asyncio.create_subprocess_exec(
            "j", *command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env={**os.environ, **env_vars}
        )

        stdout, stderr = await process.communicate()

        result_info = {
            "command": ["j"] + command,
            "exit_code": process.returncode,
            "stdout": stdout.decode() if stdout else "",
            "stderr": stderr.decode() if stderr else ""
        }

        if process.returncode == 0:
            status = "Command executed successfully"
        else:
            status = f"Command failed with exit code {process.returncode}"

        return f"J Command Execution:\n{status}\n\nCommand: {' '.join(['j'] + command)}\n\nOutput:\n{result_info['stdout']}\n\nErrors:\n{result_info['stderr']}"
    except Exception as e:
        raise RuntimeError(f"Failed to execute j command: {str(e)}")


def main():
    """Main entry point"""
    logging.basicConfig(
        level=logging.INFO,
        stream=sys.stderr,  # Redirect logs to stderr to avoid interfering with MCP protocol
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    # FastMCP handles its own asyncio event loop
    mcp.run()


if __name__ == "__main__":
    main()