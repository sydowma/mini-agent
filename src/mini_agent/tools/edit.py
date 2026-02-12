"""Edit tool implementation."""

from pathlib import Path

from .base import BaseTool
from .registry import register_tool
from .text_utils import (
    strip_bom,
    detect_line_ending,
    normalize_to_lf,
    restore_line_endings,
    fuzzy_find_text,
)
from .diff_utils import generate_diff_string, format_diff_for_output


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

        # Read the file in binary mode to preserve BOM and detect line endings
        try:
            with open(path, 'rb') as f:
                raw_bytes = f.read()
            raw_content = raw_bytes.decode('utf-8')
        except UnicodeDecodeError as e:
            return f"Error: File is not valid UTF-8: {e}"
        except Exception as e:
            return f"Error reading file: {e}"

        # Store original content for diff
        original_content = raw_content

        # Preprocess: handle BOM and line endings
        bom, content = strip_bom(raw_content)
        line_ending = detect_line_ending(content)
        content = normalize_to_lf(content)
        old_string_normalized = normalize_to_lf(old_string)
        new_string_normalized = normalize_to_lf(new_string)

        # Count occurrences using fuzzy matching
        count, fuzzy_matches = self._count_occurrences(content, old_string_normalized)

        if count == 0:
            return self._format_not_found_error(content, old_string)

        if not replace_all and count > 1:
            return (
                f"Error: old_string appears {count} times in the file. "
                f"Provide a more specific string or set replace_all=true."
            )

        # Perform the replacement
        if replace_all:
            new_content = self._replace_all_occurrences(
                content, old_string_normalized, new_string_normalized
            )
            replacement_count = count
        else:
            new_content = self._replace_first_occurrence(
                content, old_string_normalized, new_string_normalized
            )
            replacement_count = 1

        # Restore line endings
        new_content = restore_line_endings(new_content, line_ending)

        # Write back with BOM preserved
        try:
            with open(path, 'w', encoding='utf-8', newline='') as f:
                f.write(bom + new_content)
        except Exception as e:
            return f"Error writing file: {e}"

        # Generate diff
        diff_result = generate_diff_string(
            original_content,
            bom + new_content,
            filename=path.name
        )

        output = f"Edited {file_path}"
        output += f"\nReplaced {replacement_count} occurrence(s)"

        if fuzzy_matches:
            output += " (using fuzzy matching)"

        if diff_result.diff:
            output += f"\n\n{format_diff_for_output(diff_result)}"

        return output

    def _count_occurrences(self, content: str, old_string: str) -> tuple[int, bool]:
        """
        Count occurrences of old_string in content using fuzzy matching.

        Returns:
            Tuple of (count, used_fuzzy_match)
        """
        # Try exact match first
        count = content.count(old_string)
        if count > 0:
            return count, False

        # Fall back to fuzzy matching - count fuzzy occurrences
        # This is a simplified approach; for accurate counting we'd need
        # to track already-matched positions
        normalized_content = self._normalize_for_count(content)
        normalized_old = self._normalize_for_count(old_string)

        if normalized_old in normalized_content:
            # At least one fuzzy match exists
            return 1, True

        return 0, False

    def _normalize_for_count(self, text: str) -> str:
        """Quick normalization for counting purposes."""
        from .text_utils import normalize_for_fuzzy_match
        return normalize_for_fuzzy_match(text)

    def _replace_all_occurrences(
        self, content: str, old_string: str, new_string: str
    ) -> str:
        """Replace all occurrences using fuzzy matching if needed."""
        # Try exact replacement first
        if old_string in content:
            return content.replace(old_string, new_string)

        # Fall back to fuzzy replacement
        return self._fuzzy_replace_all(content, old_string, new_string)

    def _replace_first_occurrence(
        self, content: str, old_string: str, new_string: str
    ) -> str:
        """Replace first occurrence using fuzzy matching if needed."""
        match = fuzzy_find_text(content, old_string)

        if match.found:
            return (
                content[:match.index] +
                new_string +
                content[match.index + match.match_length:]
            )

        return content

    def _fuzzy_replace_all(self, content: str, old_string: str, new_string: str) -> str:
        """Replace all occurrences using fuzzy matching."""
        result = content
        while True:
            match = fuzzy_find_text(result, old_string)
            if not match.found:
                break
            result = (
                result[:match.index] +
                new_string +
                result[match.index + match.match_length:]
            )
        return result

    def _format_not_found_error(self, content: str, old_string: str) -> str:
        """Format a helpful error when old_string is not found."""
        issues = []

        # Check whitespace
        if old_string.strip() != old_string:
            if old_string.lstrip() in content or old_string.rstrip() in content:
                issues.append("whitespace mismatch (leading/trailing)")

        # Check line endings
        if '\r\n' in old_string and '\n' in content and '\r\n' not in content:
            issues.append("line ending mismatch (CRLF vs LF)")

        # Check for Unicode character differences
        from .text_utils import normalize_for_fuzzy_match
        normalized_old = normalize_for_fuzzy_match(old_string)
        normalized_content = normalize_for_fuzzy_match(content)
        if normalized_old in normalized_content:
            issues.append("Unicode character differences (smart quotes, dashes, etc.)")

        error = "Error: old_string not found in file."
        if issues:
            error += f" Possible issues: {', '.join(issues)}"
        error += f"\n\nSearched for:\n{old_string[:200]}{'...' if len(old_string) > 200 else ''}"
        return error
