"""Tests for truncation utilities."""

import pytest
from mini_agent.tools.truncate import (
    truncate_head,
    truncate_tail,
    truncate_string_to_bytes_from_end,
    truncate_string_to_bytes_from_start,
    TruncationResult,
)


class TestTruncateStringToBytesFromEnd:
    """Tests for UTF-8 safe truncation from end."""

    def test_ascii_no_truncation(self):
        """ASCII text that fits should not be truncated."""
        text = "Hello"
        result = truncate_string_to_bytes_from_end(text, 100)
        assert result == text

    def test_ascii_truncation(self):
        """ASCII text should truncate correctly."""
        text = "Hello, world!"
        result = truncate_string_to_bytes_from_end(text, 5)
        assert result == "orld!"

    def test_chinese_truncation(self):
        """Chinese characters should not be split."""
        # Each Chinese character is 3 bytes in UTF-8
        text = "你好世界"
        result = truncate_string_to_bytes_from_end(text, 6)
        # 6 bytes = 2 Chinese characters
        assert result == "世界"
        assert len(result.encode('utf-8')) == 6

    def test_chinese_truncation_boundary(self):
        """Truncation at a multi-byte boundary should be handled correctly."""
        text = "你好世界"
        # 7 bytes would split a character, should start at 6
        result = truncate_string_to_bytes_from_end(text, 7)
        assert result == "世界"
        assert len(result.encode('utf-8')) == 6

    def test_emoji_truncation(self):
        """Emoji (4-byte characters) should not be split."""
        # Most emoji are 4 bytes in UTF-8
        # "Hello " = 6 bytes, "😀" = 4 bytes, "🎉" = 4 bytes = 14 bytes total
        text = "Hello 😀🎉"
        result = truncate_string_to_bytes_from_end(text, 8)
        # Last 8 bytes should be "😀🎉" (4 + 4 = 8 bytes)
        assert result == "😀🎉"
        assert len(result.encode('utf-8')) == 8

    def test_empty_string(self):
        """Empty string should return empty."""
        assert truncate_string_to_bytes_from_end("", 10) == ""

    def test_single_multibyte_char(self):
        """Single multi-byte character handling."""
        text = "你"
        result = truncate_string_to_bytes_from_end(text, 3)
        assert result == "你"
        result = truncate_string_to_bytes_from_end(text, 2)
        assert result == ""


class TestTruncateStringToBytesFromStart:
    """Tests for UTF-8 safe truncation from start."""

    def test_ascii_no_truncation(self):
        """ASCII text that fits should not be truncated."""
        text = "Hello"
        result = truncate_string_to_bytes_from_start(text, 100)
        assert result == text

    def test_ascii_truncation(self):
        """ASCII text should truncate correctly."""
        text = "Hello, world!"
        result = truncate_string_to_bytes_from_start(text, 5)
        assert result == "Hello"

    def test_chinese_truncation(self):
        """Chinese characters should not be split."""
        text = "你好世界"
        result = truncate_string_to_bytes_from_start(text, 6)
        # 6 bytes = 2 Chinese characters
        assert result == "你好"
        assert len(result.encode('utf-8')) == 6

    def test_chinese_truncation_boundary(self):
        """Truncation at a multi-byte boundary should be handled correctly."""
        text = "你好世界"
        # 7 bytes would split a character, should end at 6
        result = truncate_string_to_bytes_from_start(text, 7)
        assert result == "你好"
        assert len(result.encode('utf-8')) == 6

    def test_empty_string(self):
        """Empty string should return empty."""
        assert truncate_string_to_bytes_from_start("", 10) == ""


class TestTruncateHeadNewFields:
    """Tests for new TruncationResult fields in truncate_head."""

    def test_truncated_by_lines(self):
        """Should indicate truncation by lines."""
        lines = ["line " + str(i) for i in range(100)]
        content = "\n".join(lines)
        result = truncate_head(content, max_lines=10, max_bytes=1000000)
        assert result.was_truncated
        assert result.truncated_by == 'lines'

    def test_truncated_by_bytes(self):
        """Should indicate truncation by bytes."""
        content = "x" * 10000
        result = truncate_head(content, max_lines=10000, max_bytes=100)
        assert result.was_truncated
        assert result.truncated_by == 'bytes'

    def test_no_truncation_fields(self):
        """No truncation should have default field values."""
        content = "short content"
        result = truncate_head(content, max_lines=100, max_bytes=1000)
        assert not result.was_truncated
        assert result.truncated_by is None
        assert not result.last_line_partial
        assert not result.first_line_exceeds_limit


class TestTruncateTailNewFields:
    """Tests for new TruncationResult fields in truncate_tail."""

    def test_truncated_by_lines(self):
        """Should indicate truncation by lines."""
        lines = ["line " + str(i) for i in range(100)]
        content = "\n".join(lines)
        result = truncate_tail(content, max_lines=10, max_bytes=1000000)
        assert result.was_truncated
        assert result.truncated_by == 'lines'

    def test_truncated_by_bytes(self):
        """Should indicate truncation by bytes."""
        content = "x" * 10000
        result = truncate_tail(content, max_lines=10000, max_bytes=100)
        assert result.was_truncated
        assert result.truncated_by == 'bytes'

    def test_chinese_content(self):
        """Chinese content should be handled correctly."""
        lines = ["中文测试" + str(i) for i in range(100)]
        content = "\n".join(lines)
        result = truncate_tail(content, max_lines=10, max_bytes=1000000)
        assert result.was_truncated
        # Verify content is valid UTF-8
        result.content.encode('utf-8')  # Should not raise


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
