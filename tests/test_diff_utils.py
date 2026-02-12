"""Tests for diff generation utilities."""

import pytest
from mini_agent.tools.diff_utils import (
    generate_diff_string,
    format_diff_for_output,
    DiffResult,
)


class TestGenerateDiffString:
    """Tests for diff string generation."""

    def test_no_changes(self):
        """No changes should produce empty diff."""
        old = "line1\nline2\nline3"
        new = "line1\nline2\nline3"
        result = generate_diff_string(old, new)
        assert result.diff == ""
        assert result.first_changed_line is None

    def test_single_line_change(self):
        """Single line change should produce diff."""
        old = "line1\nline2\nline3"
        new = "line1\nmodified\nline3"
        result = generate_diff_string(old, new)
        assert result.diff != ""
        assert "-line2" in result.diff
        assert "+modified" in result.diff
        assert result.first_changed_line == 2

    def test_line_addition(self):
        """Adding a line should produce diff."""
        old = "line1\nline2"
        new = "line1\nline2\nline3"
        result = generate_diff_string(old, new)
        assert "+line3" in result.diff
        assert result.first_changed_line == 3

    def test_line_deletion(self):
        """Deleting a line should produce diff."""
        old = "line1\nline2\nline3"
        new = "line1\nline3"
        result = generate_diff_string(old, new)
        assert "-line2" in result.diff
        assert result.first_changed_line == 2

    def test_multiple_changes(self):
        """Multiple changes should produce diff with all changes."""
        old = "line1\nline2\nline3\nline4"
        new = "line1\nmodified\nline3\nchanged"
        result = generate_diff_string(old, new)
        assert "-line2" in result.diff
        assert "+modified" in result.diff
        assert "-line4" in result.diff
        assert "+changed" in result.diff
        assert result.first_changed_line == 2

    def test_empty_old_content(self):
        """Diff from empty content."""
        old = ""
        new = "new content"
        result = generate_diff_string(old, new)
        assert "+new content" in result.diff
        assert result.first_changed_line == 1

    def test_empty_new_content(self):
        """Diff to empty content."""
        old = "old content"
        new = ""
        result = generate_diff_string(old, new)
        assert "-old content" in result.diff
        assert result.first_changed_line == 1

    def test_context_lines(self):
        """Diff should include context lines."""
        old = "\n".join([f"line{i}" for i in range(10)])
        new = "\n".join([f"line{i}" for i in range(10)]).replace("line5", "modified")
        result = generate_diff_string(old, new, context_lines=2)
        # Should include lines 3-4 before and 6-7 after
        assert "line3" in result.diff
        assert "line4" in result.diff
        assert "line6" in result.diff
        assert "line7" in result.diff

    def test_custom_filename(self):
        """Custom filename should appear in diff header."""
        old = "line1"
        new = "line2"
        result = generate_diff_string(old, new, filename="myfile.txt")
        assert "a/myfile.txt" in result.diff
        assert "b/myfile.txt" in result.diff

    def test_first_changed_line_insert_at_start(self):
        """Insert at start should return line 1."""
        old = "line2"
        new = "line1\nline2"
        result = generate_diff_string(old, new)
        assert result.first_changed_line == 1


class TestFormatDiffForOutput:
    """Tests for diff formatting."""

    def test_no_changes(self):
        """No changes should return 'No changes'."""
        result = DiffResult(diff="", first_changed_line=None)
        output = format_diff_for_output(result)
        assert output == "No changes"

    def test_short_diff(self):
        """Short diff should be output completely."""
        diff = "--- a/file\n+++ b/file\n@@ -1 +1 @@\n-line1\n+line2\n"
        result = DiffResult(diff=diff, first_changed_line=1)
        output = format_diff_for_output(result)
        assert "-line1" in output
        assert "+line2" in output
        assert "First change at line 1" in output

    def test_truncated_diff(self):
        """Long diff should be truncated."""
        lines = ["--- a/file", "+++ b/file"]
        for i in range(100):
            lines.append(f"+line{i}")
        diff = "\n".join(lines) + "\n"
        result = DiffResult(diff=diff, first_changed_line=1)
        output = format_diff_for_output(result, max_lines=20)
        assert "truncated" in output

    def test_includes_line_number(self):
        """Output should include first changed line number."""
        result = DiffResult(diff="some diff", first_changed_line=42)
        output = format_diff_for_output(result)
        assert "line 42" in output

    def test_none_line_number(self):
        """None line number should not cause error."""
        result = DiffResult(diff="some diff", first_changed_line=None)
        output = format_diff_for_output(result)
        # Should just include the diff without line number info
        assert "some diff" in output
