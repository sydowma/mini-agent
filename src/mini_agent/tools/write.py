"""Write tool implementation."""

import os
from pathlib import Path
from typing import Optional

from .base import BaseTool
from .registry import register_tool


@register_tool
class WriteTool(BaseTool):
    """Tool for writing file contents."""

    @property
    def name(self) -> str:
        return "write"

    @property
    def description(self) -> str:
        return (
            "Write content to a file. Creates the file if it doesn't exist, "
            "overwrites if it does. Automatically creates parent directories."
        )

    @property
    def input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "The absolute path to the file to write",
                },
                "content": {
                    "type": "string",
                    "description": "The content to write to the file",
                },
            },
            "required": ["file_path", "content"],
        }

    async def execute(self, arguments: dict) -> str:
        """Execute the write tool."""
        file_path = arguments.get("file_path")
        content = arguments.get("content", "")

        if not file_path:
            return "Error: file_path is required"

        path = Path(file_path)

        if not path.is_absolute():
            return f"Error: file_path must be absolute, got: {file_path}"

        # Create parent directories if needed
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            return f"Error creating directories: {e}"

        # Check if file exists
        existed = path.exists()

        # Write the content
        try:
            with open(path, 'w', encoding='utf-8') as f:
                f.write(content)
        except Exception as e:
            return f"Error writing file: {e}"

        # Return summary
        lines = content.count('\n') + 1 if content else 0
        bytes_written = len(content.encode('utf-8'))

        action = "Updated" if existed else "Created"
        return f"{action} file: {file_path}\nLines: {lines}\nBytes: {bytes_written}"
