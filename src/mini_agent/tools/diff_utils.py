"""Diff generation utilities."""

import difflib
from dataclasses import dataclass
from typing import Optional


@dataclass
class DiffResult:
    """Result of a diff generation operation."""
    diff: str  # Unified diff string
    first_changed_line: Optional[int]  # Line number of first change (1-indexed)


def generate_diff_string(
    old_content: str,
    new_content: str,
    context_lines: int = 4,
    filename: str = "file",
) -> DiffResult:
    """
    Generate a unified diff string between old and new content.

    Args:
        old_content: The original content
        new_content: The new content
        context_lines: Number of context lines around changes
        filename: Name to use in diff header

    Returns:
        DiffResult with the diff string and first changed line number
    """
    old_lines = old_content.splitlines(keepends=True)
    new_lines = new_content.splitlines(keepends=True)

    # Generate unified diff
    diff = difflib.unified_diff(
        old_lines,
        new_lines,
        fromfile=f"a/{filename}",
        tofile=f"b/{filename}",
        n=context_lines,
    )

    diff_text = ''.join(diff)

    # Find the first changed line number
    first_changed_line = _find_first_changed_line(old_content, new_content)

    return DiffResult(
        diff=diff_text,
        first_changed_line=first_changed_line,
    )


def _find_first_changed_line(old_content: str, new_content: str) -> Optional[int]:
    """
    Find the 1-indexed line number of the first change.

    Args:
        old_content: Original content
        new_content: New content

    Returns:
        1-indexed line number of first change, or None if no changes
    """
    old_lines = old_content.splitlines()
    new_lines = new_content.splitlines()

    # Use SequenceMatcher to find the first change
    matcher = difflib.SequenceMatcher(None, old_lines, new_lines)

    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag != 'equal':
            # Return the line number in the original file (1-indexed)
            # For 'replace' and 'delete', use old line position
            # For 'insert', use the position before which insertion happens
            if tag in ('replace', 'delete'):
                return i1 + 1
            elif tag == 'insert':
                return i1 + 1 if i1 > 0 else 1

    return None


def format_diff_for_output(diff_result: DiffResult, max_lines: int = 50) -> str:
    """
    Format diff result for display in tool output.

    Args:
        diff_result: The diff result to format
        max_lines: Maximum number of diff lines to show

    Returns:
        Formatted diff string for display
    """
    if not diff_result.diff:
        return "No changes"

    lines = diff_result.diff.splitlines(keepends=True)

    if len(lines) <= max_lines:
        output = diff_result.diff
    else:
        # Truncate to max_lines, keeping header and tail
        header_lines = min(2, len(lines))  # Keep diff header
        tail_lines = max_lines - header_lines

        output = ''.join(lines[:header_lines])
        output += f"... (truncated {len(lines) - max_lines} lines)\n"
        output += ''.join(lines[-tail_lines:])

    if diff_result.first_changed_line is not None:
        output += f"\nFirst change at line {diff_result.first_changed_line}"

    return output
