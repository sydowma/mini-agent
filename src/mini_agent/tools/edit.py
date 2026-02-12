"""Edit tool implementation."""

import os
from pathlib import Path
from typing import Optional

from .base import BaseTool
from .registry import register_tool


@register_tool
class EditTool(BaseTool):
    """Tool for editing file contents."""

    @property
    def name(self) -> str:
        return "edit"

    @property
    def description(self) -> str:
        return (
            "Edit a file by replacing specific text. The old_string must appear "
            "exactly once in the file. Use this for targeted edits rather than "
            "rewriting entire files."
        )

    @property
    def input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "The absolute path to the file to edit",
                },
                "old_string": {
                    "type": "string",
                    "description": "The text to find and replace (must be unique in the file)",
                },
                "new_string": {
                    "type": "string",
                    "description": "The text to replace old_string with",
                },
                "replace_all": {
                    "type": "boolean",
                    "description": "Replace all occurrences (default: false)",
                    "default": False,
                },
            },
            "required": ["file_path", "old_string", "new_string"],
        }

    async def execute(self, arguments: dict) -> str:
        """Execute the edit tool."""
        file_path = arguments.get("file_path")
        old_string = arguments.get("old_string")
        new_string = arguments.get("new_string")
        replace_all = arguments.get("replace_all", False)

        if not file_path:
            return "Error: file_path is required"
        if old_string is None:
            return "Error: old_string is required"
        if new_string is None:
            return "Error: new_string is required"

        path = Path(file_path)

        if not path.is_absolute():
            return f"Error: file_path must be absolute, got: {file_path}"

        if not path.exists():
            return f"Error: File not found: {file_path}"

        if not path.is_file():
            return f"Error: Not a file: {file_path}"

        # Read the file
        try:
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            return f"Error reading file: {e}"

        # Count occurrences
        count = content.count(old_string)

        if count == 0:
            # Try to provide helpful error message
            return self._format_not_found_error(content, old_string)

        if not replace_all and count > 1:
            return (
                f"Error: old_string appears {count} times in the file. "
                f"Provide a more specific string or set replace_all=true."
            )

        # Perform the replacement
        if replace_all:
            new_content = content.replace(old_string, new_string)
            replacement_count = count
        else:
            new_content = content.replace(old_string, new_string, 1)
            replacement_count = 1

        # Write back
        try:
            with open(path, 'w', encoding='utf-8') as f:
                f.write(new_content)
        except Exception as e:
            return f"Error writing file: {e}"

        return f"Edited {file_path}\nReplaced {replacement_count} occurrence(s)"

    def _format_not_found_error(self, content: str, old_string: str) -> str:
        """Format a helpful error when old_string is not found."""
        # Check for common issues
        issues = []

        # Check whitespace
        if old_string.strip() != old_string:
            if old_string.lstrip() in content or old_string.rstrip() in content:
                issues.append("whitespace mismatch (leading/trailing)")

        # Check line endings
        if '\r\n' in old_string and '\n' in content and '\r\n' not in content:
            issues.append("line ending mismatch (CRLF vs LF)")

        error = f"Error: old_string not found in file."
        if issues:
            error += f" Possible issues: {', '.join(issues)}"
        error += f"\n\nSearched for:\n{old_string[:200]}{'...' if len(old_string) > 200 else ''}"
        return error
