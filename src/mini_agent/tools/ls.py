"""List tool implementation."""

import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional

from .base import BaseTool
from .registry import register_tool


@register_tool
class ListTool(BaseTool):
    """Tool for listing directory contents."""

    @property
    def name(self) -> str:
        return "ls"

    @property
    def description(self) -> str:
        return (
            "List contents of a directory. Shows files and subdirectories "
            "sorted by name. Returns absolute paths."
        )

    @property
    def input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Directory path to list (default: current directory)",
                },
                "all": {
                    "type": "boolean",
                    "description": "Show hidden files (default: false)",
                    "default": False,
                },
                "long": {
                    "type": "boolean",
                    "description": "Show detailed information (default: false)",
                    "default": False,
                },
            },
            "required": [],
        }

    async def execute(self, arguments: dict) -> str:
        """Execute the ls tool."""
        path = arguments.get("path", ".")
        show_all = arguments.get("all", False)
        long_format = arguments.get("long", False)

        dir_path = Path(path)

        if not dir_path.is_absolute():
            return f"Error: path must be absolute, got: {path}"

        if not dir_path.exists():
            return f"Error: Directory not found: {path}"

        if not dir_path.is_dir():
            return f"Error: Not a directory: {path}"

        try:
            items = list(dir_path.iterdir())
        except PermissionError:
            return f"Error: Permission denied: {path}"
        except Exception as e:
            return f"Error listing directory: {e}"

        # Filter hidden files unless show_all
        if not show_all:
            items = [i for i in items if not i.name.startswith('.')]

        # Sort by name (case-insensitive)
        items.sort(key=lambda x: x.name.lower())

        # Format output
        if long_format:
            lines = [self._format_long(item) for item in items]
        else:
            lines = []
            for item in items:
                prefix = "d" if item.is_dir() else "-"
                lines.append(f"{prefix} {item.name}")

        if not lines:
            return f"Directory {path} is empty"

        return "\n".join(lines)

    def _format_long(self, item: Path) -> str:
        """Format item with detailed information."""
        try:
            stat = item.stat()
            size = stat.st_size
            mtime = datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M")
        except Exception:
            size = 0
            mtime = "?"

        is_dir = item.is_dir()
        prefix = "d" if is_dir else "-"

        # Format size
        if size >= 1024 * 1024:
            size_str = f"{size / (1024 * 1024):.1f}M"
        elif size >= 1024:
            size_str = f"{size / 1024:.1f}K"
        else:
            size_str = str(size)

        return f"{prefix} {size_str:>8} {mtime} {item.name}"
