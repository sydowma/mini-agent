"""Tests for truncation utilities."""

import pytest
from mini_agent.tools.truncate import (
    truncate_head,
    truncate_tail,
    TruncationResult,
)


class TestTruncateHead:
    def test_no_truncation_needed(self):
        content = "short content"
        result = truncate_head(content, max_lines=100, max_bytes=1000)
        assert not result.was_truncated
        assert result.content == content

    def test_truncate_by_lines(self):
        lines = ["line " + str(i) for i in range(100)]
        content = "\n".join(lines)
        result = truncate_head(content, max_lines=10)
        assert result.was_truncated
        assert result.lines_removed == 90
        # Should keep the last 10 lines
        assert "line 99" in result.content
        assert "line 0" not in result.content

    def test_truncate_by_bytes(self):
        content = "x" * 1000
        result = truncate_head(content, max_lines=1000, max_bytes=100)
        assert result.was_truncated
        assert len(result.content) <= 150  # Account for newline boundary adjustment


class TestTruncateTail:
    def test_no_truncation_needed(self):
        content = "short content"
        result = truncate_tail(content, max_lines=100, max_bytes=1000)
        assert not result.was_truncated
        assert result.content == content

    def test_truncate_by_lines(self):
        lines = ["line " + str(i) for i in range(100)]
        content = "\n".join(lines)
        result = truncate_tail(content, max_lines=10)
        assert result.was_truncated
        assert result.lines_removed == 90
        # Should keep the first 10 lines
        assert "line 0" in result.content
        assert "line 99" not in result.content

    def test_empty_content(self):
        result = truncate_tail("", max_lines=10)
        assert result.content == ""
        assert not result.was_truncated
