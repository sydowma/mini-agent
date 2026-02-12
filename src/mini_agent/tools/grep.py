"""Grep tool implementation."""

import asyncio
import json
import shutil
import subprocess
from pathlib import Path
from typing import Optional

from .base import BaseTool
from .registry import register_tool
from .truncate import truncate_tail, format_truncation_notice


@register_tool
class GrepTool(BaseTool):
    """Tool for searching file contents using ripgrep."""

    @property
    def name(self) -> str:
        return "grep"

    @property
    def description(self) -> str:
        return (
            "Search for patterns in file contents using ripgrep. "
            "Supports regex patterns and various output formats. "
            "Optimized for code search with context lines."
        )

    @property
    def input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "pattern": {
                    "type": "string",
                    "description": "The regex pattern to search for",
                },
                "path": {
                    "type": "string",
                    "description": "Directory or file to search in (default: current directory)",
                },
                "glob": {
                    "type": "string",
                    "description": "Glob pattern to filter files (e.g., '*.py', '**/*.ts')",
                },
                "output_mode": {
                    "type": "string",
                    "enum": ["content", "files_with_matches", "count"],
                    "description": "Output format (default: content)",
                    "default": "content",
                },
                "context": {
                    "type": "integer",
                    "description": "Number of context lines to show",
                    "default": 0,
                },
                "case_insensitive": {
                    "type": "boolean",
                    "description": "Case insensitive search",
                    "default": False,
                },
                "head_limit": {
                    "type": "integer",
                    "description": "Maximum number of results",
                },
            },
            "required": ["pattern"],
        }

    async def execute(self, arguments: dict) -> str:
        """Execute the grep tool."""
        pattern = arguments.get("pattern")
        path = arguments.get("path", ".")
        glob_pattern = arguments.get("glob")
        output_mode = arguments.get("output_mode", "content")
        context = arguments.get("context", 0)
        case_insensitive = arguments.get("case_insensitive", False)
        head_limit = arguments.get("head_limit")

        if not pattern:
            return "Error: pattern is required"

        # Check if rg (ripgrep) is available
        rg_path = shutil.which("rg")
        if not rg_path:
            return self._fallback_grep(arguments)

        # Build command
        cmd = [rg_path, "--json"]  # JSON output for easy parsing

        if case_insensitive:
            cmd.append("-i")

        if output_mode == "files_with_matches":
            cmd.append("-l")
        elif output_mode == "count":
            cmd.append("-c")

        if context > 0:
            cmd.extend(["-C", str(context)])

        if glob_pattern:
            cmd.extend(["-g", glob_pattern])

        if head_limit:
            cmd.extend(["-m", str(head_limit)])

        cmd.append(pattern)
        cmd.append(path)

        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, stderr = await process.communicate()

            if process.returncode not in (0, 1):  # 1 = no matches
                stderr_str = stderr.decode('utf-8', errors='replace')
                return f"Error: {stderr_str}"

            stdout_str = stdout.decode('utf-8', errors='replace')

            if output_mode == "content" and stdout_str:
                return self._format_json_output(stdout_str)

            return stdout_str if stdout_str else "No matches found"

        except Exception as e:
            return f"Error executing grep: {e}"

    def _format_json_output(self, json_output: str) -> str:
        """Format ripgrep JSON output for display."""
        results = []

        for line in json_output.strip().split('\n'):
            if not line:
                continue

            try:
                data = json.loads(line)
                if data.get("type") == "match":
                    match_data = data.get("data", {})
                    path = match_data.get("path", {}).get("text", "")
                    line_number = match_data.get("line_number", 0)
                    lines = match_data.get("lines", {}).get("text", "")
                    results.append(f"{path}:{line_number}:\t{lines.rstrip()}")
            except json.JSONDecodeError:
                # Fallback to raw line
                results.append(line)

        output = '\n'.join(results)

        # Truncate if needed
        trunc_result = truncate_tail(output, max_lines=2000)
        if trunc_result.was_truncated:
            return trunc_result.content + format_truncation_notice(trunc_result, "tail")

        return output

    async def _fallback_grep(self, arguments: dict) -> str:
        """Fallback using Python's grep when ripgrep is not available."""
        import re
        from pathlib import Path

        pattern = arguments.get("pattern")
        path = Path(arguments.get("path", "."))
        case_insensitive = arguments.get("case_insensitive", False)

        flags = re.MULTILINE
        if case_insensitive:
            flags |= re.IGNORECASE

        try:
            regex = re.compile(pattern, flags)
        except re.error as e:
            return f"Error: Invalid regex pattern: {e}"

        results = []

        def search_file(file_path: Path):
            try:
                with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                    for i, line in enumerate(f, 1):
                        if regex.search(line):
                            results.append(f"{file_path}:{i}:\t{line.rstrip()}")
            except Exception:
                pass

        if path.is_file():
            search_file(path)
        else:
            for file_path in path.rglob("*"):
                if file_path.is_file() and not file_path.name.startswith('.'):
                    search_file(file_path)

        if not results:
            return "No matches found"

        output = '\n'.join(results[:100])  # Limit results
        return output
