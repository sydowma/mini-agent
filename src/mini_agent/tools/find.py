"""Find tool implementation."""

import asyncio
import shutil
from pathlib import Path
from typing import Optional

from .base import BaseTool
from .registry import register_tool
from .truncate import truncate_tail, format_truncation_notice


@register_tool
class FindTool(BaseTool):
    """Tool for finding files using fd or fallback."""

    @property
    def name(self) -> str:
        return "find"

    @property
    def description(self) -> str:
        return (
            "Find files by name pattern. Uses fd if available, falls back to Python. "
            "Respects .gitignore by default. Returns paths sorted by modification time."
        )

    @property
    def input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "pattern": {
                    "type": "string",
                    "description": "Glob pattern to match files (e.g., '*.py', '**/*.ts')",
                },
                "path": {
                    "type": "string",
                    "description": "Directory to search in (default: current directory)",
                },
                "type": {
                    "type": "string",
                    "enum": ["file", "directory", "any"],
                    "description": "Type of items to find",
                    "default": "file",
                },
                "max_depth": {
                    "type": "integer",
                    "description": "Maximum search depth",
                },
            },
            "required": ["pattern"],
        }

    async def execute(self, arguments: dict) -> str:
        """Execute the find tool."""
        pattern = arguments.get("pattern")
        path = arguments.get("path", ".")
        item_type = arguments.get("type", "file")
        max_depth = arguments.get("max_depth")

        if not pattern:
            return "Error: pattern is required"

        # Check if fd is available
        fd_path = shutil.which("fd")

        if fd_path:
            return await self._fd_search(fd_path, arguments)

        return self._python_fallback(arguments)

    async def _fd_search(self, fd_path: str, arguments: dict) -> str:
        """Use fd for searching."""
        pattern = arguments.get("pattern")
        path = arguments.get("path", ".")
        item_type = arguments.get("type", "file")
        max_depth = arguments.get("max_depth")

        cmd = [fd_path, pattern, path]

        if item_type == "file":
            cmd.extend(["-t", "f"])
        elif item_type == "directory":
            cmd.extend(["-t", "d"])

        if max_depth:
            cmd.extend(["-d", str(max_depth)])

        # Sort by modification time
        cmd.append("--changed-within=100y")  # Include all recent files
        cmd.append("--exec-batch")  # We'll sort manually

        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, stderr = await process.communicate()

            if process.returncode != 0:
                stderr_str = stderr.decode('utf-8', errors='replace')
                if stderr_str:
                    return f"Error: {stderr_str}"

            stdout_str = stdout.decode('utf-8', errors='replace')
            results = stdout_str.strip().split('\n') if stdout_str.strip() else []

            if not results or results == ['']:
                return "No files found"

            # Sort by modification time
            def get_mtime(filepath: str) -> float:
                try:
                    return Path(filepath).stat().st_mtime
                except Exception:
                    return 0

            results.sort(key=get_mtime, reverse=True)

            output = '\n'.join(results)

            # Truncate if needed
            trunc_result = truncate_tail(output, max_lines=1000)
            if trunc_result.was_truncated:
                return trunc_result.content + format_truncation_notice(trunc_result, "tail")

            return output

        except Exception as e:
            return f"Error executing find: {e}"

    def _python_fallback(self, arguments: dict) -> str:
        """Fallback using Python's pathlib."""
        from fnmatch import fnmatch

        pattern = arguments.get("pattern")
        path = Path(arguments.get("path", "."))
        item_type = arguments.get("type", "file")
        max_depth = arguments.get("max_depth", 10)

        results = []

        def should_include(item: Path) -> bool:
            if item_type == "file" and not item.is_file():
                return False
            if item_type == "directory" and not item.is_dir():
                return False
            # Check pattern match
            if '**' in pattern:
                return True  # Will be filtered later
            return fnmatch(item.name, pattern)

        def search(current: Path, depth: int = 0):
            if depth > max_depth:
                return

            try:
                for item in current.iterdir():
                    # Skip hidden files and common ignore patterns
                    if item.name.startswith('.'):
                        if item.name not in ['.gitignore', '.env.example']:
                            continue

                    if should_include(item):
                        results.append(str(item))

                    if item.is_dir():
                        search(item, depth + 1)
            except PermissionError:
                pass

        if '**' in pattern:
            # Use rglob for recursive patterns
            base_pattern = pattern.replace('**/', '').replace('/**', '')
            for item in path.rglob(base_pattern if base_pattern else '*'):
                if should_include(item):
                    results.append(str(item))
        else:
            search(path)

        if not results:
            return "No files found"

        # Sort by modification time
        def get_mtime(filepath: str) -> float:
            try:
                return Path(filepath).stat().st_mtime
            except Exception:
                return 0

        results.sort(key=get_mtime, reverse=True)

        output = '\n'.join(results[:500])  # Limit results
        return output
