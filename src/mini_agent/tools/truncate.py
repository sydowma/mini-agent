"""Output truncation utilities."""

from dataclasses import dataclass


@dataclass
class TruncationResult:
    """Result of truncation operation."""
    content: str
    was_truncated: bool
    original_lines: int
    original_bytes: int
    truncated_lines: int = 0
    truncated_bytes: int = 0

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

    # Truncate by lines first
    if len(lines) > max_lines:
        removed_count = len(lines) - max_lines
        lines = lines[removed_count:]
        content = '\n'.join(lines)

    # Check bytes after line truncation
    current_bytes = len(content.encode('utf-8'))
    if current_bytes > max_bytes:
        # Need to truncate by bytes
        truncated_content = content[-max_bytes:]
        # Find first newline to start at a clean line boundary
        newline_idx = truncated_content.find('\n')
        if newline_idx != -1:
            truncated_content = truncated_content[newline_idx + 1:]
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

    # Truncate by lines first
    if len(lines) > max_lines:
        lines = lines[:max_lines]
        content = '\n'.join(lines)

    # Check bytes after line truncation
    current_bytes = len(content.encode('utf-8'))
    if current_bytes > max_bytes:
        # Need to truncate by bytes
        truncated_content = content[:max_bytes]
        # Find last newline to end at a clean line boundary
        newline_idx = truncated_content.rfind('\n')
        if newline_idx != -1:
            truncated_content = truncated_content[:newline_idx]
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
    )


def format_truncation_notice(result: TruncationResult, direction: str = "head") -> str:
    """Format a notice about truncation."""
    if not result.was_truncated:
        return ""

    notice = f"\n[Output truncated: removed {result.lines_removed} lines from {direction}]"
    notice += f"\n[Original: {result.original_lines} lines, {result.original_bytes} bytes]"
    notice += f"\n[Showing: {result.truncated_lines} lines, {result.truncated_bytes} bytes]"
    return notice
