"""Output truncation utilities."""

from dataclasses import dataclass
from typing import Literal, Optional


@dataclass
class TruncationResult:
    """Result of truncation operation."""
    content: str
    was_truncated: bool
    original_lines: int
    original_bytes: int
    truncated_lines: int = 0
    truncated_bytes: int = 0
    truncated_by: Optional[Literal['lines', 'bytes']] = None  # Which limit triggered truncation
    last_line_partial: bool = False  # Whether the last line is partially truncated
    first_line_exceeds_limit: bool = False  # Whether the first line exceeds the byte limit

    @property
    def lines_removed(self) -> int:
        return self.original_lines - self.truncated_lines


def truncate_head(
    content: str,
    max_lines: int = 2000,
    max_bytes: int = 256000,
) -> TruncationResult:
    """
    Truncate content from the head (keeping the tail).

    Args:
        content: The content to truncate
        max_lines: Maximum number of lines
        max_bytes: Maximum number of bytes

    Returns:
        TruncationResult with truncated content
    """
    original_lines = content.count('\n') + 1 if content else 0
    original_bytes = len(content.encode('utf-8'))

    if original_lines <= max_lines and original_bytes <= max_bytes:
        return TruncationResult(
            content=content,
            was_truncated=False,
            original_lines=original_lines,
            original_bytes=original_bytes,
            truncated_lines=original_lines,
            truncated_bytes=original_bytes,
        )

    lines = content.split('\n')
    truncated_by = None
    last_line_partial = False
    first_line_exceeds_limit = False

    # Truncate by lines first
    if len(lines) > max_lines:
        truncated_by = 'lines'
        removed_count = len(lines) - max_lines
        lines = lines[removed_count:]
        content = '\n'.join(lines)

    # Check bytes after line truncation
    current_bytes = len(content.encode('utf-8'))
    if current_bytes > max_bytes:
        truncated_by = 'bytes'
        # Use UTF-8 safe truncation
        truncated_content = truncate_string_to_bytes_from_end(content, max_bytes)
        # Find first newline to start at a clean line boundary
        newline_idx = truncated_content.find('\n')
        if newline_idx != -1:
            truncated_content = truncated_content[newline_idx + 1:]
            last_line_partial = False
        else:
            # No newline found, we're starting mid-line
            first_line_exceeds_limit = True
            last_line_partial = True
        content = truncated_content

    final_lines = content.count('\n') + 1 if content else 0
    final_bytes = len(content.encode('utf-8'))

    return TruncationResult(
        content=content,
        was_truncated=True,
        original_lines=original_lines,
        original_bytes=original_bytes,
        truncated_lines=final_lines,
        truncated_bytes=final_bytes,
        truncated_by=truncated_by,
        last_line_partial=last_line_partial,
        first_line_exceeds_limit=first_line_exceeds_limit,
    )


def truncate_tail(
    content: str,
    max_lines: int = 2000,
    max_bytes: int = 256000,
) -> TruncationResult:
    """
    Truncate content from the tail (keeping the head).

    Args:
        content: The content to truncate
        max_lines: Maximum number of lines
        max_bytes: Maximum number of bytes

    Returns:
        TruncationResult with truncated content
    """
    original_lines = content.count('\n') + 1 if content else 0
    original_bytes = len(content.encode('utf-8'))

    if original_lines <= max_lines and original_bytes <= max_bytes:
        return TruncationResult(
            content=content,
            was_truncated=False,
            original_lines=original_lines,
            original_bytes=original_bytes,
            truncated_lines=original_lines,
            truncated_bytes=original_bytes,
        )

    lines = content.split('\n')
    truncated_by = None
    last_line_partial = False
    first_line_exceeds_limit = False

    # Truncate by lines first
    if len(lines) > max_lines:
        truncated_by = 'lines'
        lines = lines[:max_lines]
        content = '\n'.join(lines)

    # Check bytes after line truncation
    current_bytes = len(content.encode('utf-8'))
    if current_bytes > max_bytes:
        truncated_by = 'bytes'
        # Use UTF-8 safe truncation
        truncated_content = truncate_string_to_bytes_from_start(content, max_bytes)
        # Find last newline to end at a clean line boundary
        newline_idx = truncated_content.rfind('\n')
        if newline_idx != -1:
            truncated_content = truncated_content[:newline_idx]
            last_line_partial = False
        else:
            # No newline found, entire content is on one line that exceeds limit
            first_line_exceeds_limit = True
            last_line_partial = True
        content = truncated_content

    final_lines = content.count('\n') + 1 if content else 0
    final_bytes = len(content.encode('utf-8'))

    return TruncationResult(
        content=content,
        was_truncated=True,
        original_lines=original_lines,
        original_bytes=original_bytes,
        truncated_lines=final_lines,
        truncated_bytes=final_bytes,
        truncated_by=truncated_by,
        last_line_partial=last_line_partial,
        first_line_exceeds_limit=first_line_exceeds_limit,
    )


def format_truncation_notice(result: TruncationResult, direction: str = "head") -> str:
    """Format a notice about truncation."""
    if not result.was_truncated:
        return ""

    notice = f"\n[Output truncated: removed {result.lines_removed} lines from {direction}]"
    notice += f"\n[Original: {result.original_lines} lines, {result.original_bytes} bytes]"
    notice += f"\n[Showing: {result.truncated_lines} lines, {result.truncated_bytes} bytes]"
    return notice


def truncate_string_to_bytes_from_end(text: str, max_bytes: int) -> str:
    """
    UTF-8 safe truncation from the end of a string.

    Finds a valid UTF-8 character boundary when truncating, avoiding
    splitting multi-byte characters.

    Args:
        text: The text to truncate
        max_bytes: Maximum number of bytes to keep

    Returns:
        Truncated text that fits within max_bytes, starting from a valid
        UTF-8 character boundary
    """
    if not text:
        return text

    encoded = text.encode('utf-8')

    if len(encoded) <= max_bytes:
        return text

    # Calculate starting position
    start = len(encoded) - max_bytes

    # Skip continuation bytes (0x80-0xBF) to find a valid character boundary
    # Continuation bytes have the pattern 10xxxxxx (0x80-0xBF)
    while start < len(encoded) and (encoded[start] & 0xC0) == 0x80:
        start += 1

    # Decode from the valid starting position
    return encoded[start:].decode('utf-8')


def truncate_string_to_bytes_from_start(text: str, max_bytes: int) -> str:
    """
    UTF-8 safe truncation from the start of a string.

    Finds a valid UTF-8 character boundary when truncating, avoiding
    splitting multi-byte characters.

    Args:
        text: The text to truncate
        max_bytes: Maximum number of bytes to keep

    Returns:
        Truncated text that fits within max_bytes, ending at a valid
        UTF-8 character boundary
    """
    if not text:
        return text

    encoded = text.encode('utf-8')

    if len(encoded) <= max_bytes:
        return text

    # Truncate to max_bytes
    truncated = encoded[:max_bytes]

    # Work backwards to find a valid UTF-8 boundary
    # Try decoding and back off until we find a valid boundary
    while truncated:
        try:
            return truncated.decode('utf-8')
        except UnicodeDecodeError:
            truncated = truncated[:-1]

    return ''
