"""Bash tool implementation."""

import asyncio
import os
import signal
import subprocess
from pathlib import Path
from typing import Optional

from .base import BaseTool
from .registry import register_tool
from .truncate import truncate_tail, format_truncation_notice


@register_tool
class BashTool(BaseTool):
    """Tool for executing bash commands."""

    DEFAULT_TIMEOUT = 120000  # 2 minutes in seconds

    @property
    def name(self) -> str:
        return "bash"

    @property
    def description(self) -> str:
        return (
            "Execute a bash command in the shell. Commands run in the working directory. "
            "Output is streamed and may be truncated for large outputs. "
            "Use timeout to limit execution time."
        )

    @property
    def input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "The command to execute",
                },
                "timeout": {
                    "type": "integer",
                    "description": f"Timeout in seconds (default: {self.DEFAULT_TIMEOUT})",
                    "default": self.DEFAULT_TIMEOUT,
                },
                "working_dir": {
                    "type": "string",
                    "description": "Working directory (default: current directory)",
                },
            },
            "required": ["command"],
        }

    async def execute(self, arguments: dict) -> str:
        """Execute the bash tool."""
        command = arguments.get("command")
        timeout = arguments.get("timeout", self.DEFAULT_TIMEOUT)
        working_dir = arguments.get("working_dir")

        if not command:
            return "Error: command is required"

        # Validate working directory
        if working_dir:
            work_path = Path(working_dir)
            if not work_path.exists():
                return f"Error: Working directory does not exist: {working_dir}"
            if not work_path.is_dir():
                return f"Error: Not a directory: {working_dir}"

        try:
            # Run the command
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=working_dir,
                # Use process group for proper termination
                start_new_session=True,
            )

            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=timeout
                )
            except asyncio.TimeoutError:
                # Kill the process group
                try:
                    os.killpg(os.getpgid(process.pid), signal.SIGTERM)
                    await asyncio.sleep(1)
                    # Force kill if still running
                    if process.returncode is None:
                        os.killpg(os.getpgid(process.pid), signal.SIGKILL)
                except ProcessLookupError:
                    pass

                return (
                    f"Error: Command timed out after {timeout} seconds\n"
                    f"Command: {command}"
                )

            # Decode output
            stdout_str = stdout.decode('utf-8', errors='replace') if stdout else ""
            stderr_str = stderr.decode('utf-8', errors='replace') if stderr else ""

            # Build result
            result_parts = []

            if stdout_str:
                result_parts.append(stdout_str)

            if stderr_str:
                result_parts.append(f"[stderr]\n{stderr_str}")

            if process.returncode != 0:
                result_parts.append(f"[exit code: {process.returncode}]")

            output = "\n".join(result_parts)

            # Truncate if needed
            trunc_result = truncate_tail(output, max_lines=2000, max_bytes=256000)

            if trunc_result.was_truncated:
                return trunc_result.content + format_truncation_notice(trunc_result, "tail")

            return output if output else "[Command completed with no output]"

        except Exception as e:
            return f"Error executing command: {e}"
