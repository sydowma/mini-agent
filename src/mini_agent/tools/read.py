"""Read tool implementation."""

import base64
import os
from pathlib import Path
from typing import Optional

import mimetypes

from .base import BaseTool
from .registry import register_tool
from .truncate import truncate_tail, format_truncation_notice


@register_tool
class ReadTool(BaseTool):
    """Tool for reading file contents."""

    @property
    def name(self) -> str:
        return "read"

    @property
    def description(self) -> str:
        return (
            "Read the contents of a file. Supports text files and images. "
            "Returns file content with line numbers. For large files, "
            "content may be truncated."
        )

    @property
    def input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "The absolute path to the file to read",
                },
                "offset": {
                    "type": "integer",
                    "description": "Line number to start reading from (1-based). Default: 1",
                    "default": 1,
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of lines to read. Default: 2000",
                    "default": 2000,
                },
            },
            "required": ["file_path"],
        }

    async def execute(self, arguments: dict) -> str:
        """Execute the read tool."""
        file_path = arguments.get("file_path")
        offset = arguments.get("offset", 1)
        limit = arguments.get("limit", 2000)

        if not file_path:
            return "Error: file_path is required"

        path = Path(file_path)

        if not path.is_absolute():
            return f"Error: file_path must be absolute, got: {file_path}"

        if not path.exists():
            return f"Error: File not found: {file_path}"

        if not path.is_file():
            return f"Error: Not a file: {file_path}"

        # Check if it's an image
        mime_type, _ = mimetypes.guess_type(str(path))
        if mime_type and mime_type.startswith("image/"):
            return await self._read_image(path, mime_type)

        # Read text file
        try:
            with open(path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
        except UnicodeDecodeError:
            # Try with a different encoding or return binary info
            try:
                with open(path, 'r', encoding='latin-1') as f:
                    lines = f.readlines()
            except Exception as e:
                return f"Error: Could not read file as text: {e}"
        except Exception as e:
            return f"Error reading file: {e}"

        total_lines = len(lines)

        # Apply offset (1-based to 0-based)
        start = max(0, offset - 1)
        end = min(total_lines, start + limit)
        selected_lines = lines[start:end]

        # Format with line numbers
        formatted_lines = []
        for i, line in enumerate(selected_lines, start=start + 1):
            # Remove trailing newline for display, we'll add it back
            line_content = line.rstrip('\n')
            formatted_lines.append(f"{i:6}\t{line_content}")

        content = '\n'.join(formatted_lines)

        # Apply truncation if needed
        result = truncate_tail(content, max_lines=2000, max_bytes=256000)
        output = result.content

        # Add metadata
        if result.was_truncated:
            output += format_truncation_notice(result, "tail")

        # Add continuation hint if there are more lines
        if end < total_lines:
            output += f"\n\n[File has {total_lines} total lines. Use offset={end + 1} to read more.]"

        return output

    async def _read_image(self, path: Path, mime_type: str) -> str:
        """Read an image file and return base64 encoded data."""
        try:
            with open(path, 'rb') as f:
                data = f.read()

            encoded = base64.standard_b64encode(data).decode('utf-8')

            return (
                f"[Image: {path.name}]\n"
                f"Type: {mime_type}\n"
                f"Size: {len(data)} bytes\n"
                f"Base64 data: {encoded[:100]}...\n"
                f"(Full base64 data available but truncated for display)"
            )
        except Exception as e:
            return f"Error reading image: {e}"
