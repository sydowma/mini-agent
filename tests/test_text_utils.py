"""Tests for text processing utilities."""

import pytest
from mini_agent.tools.text_utils import (
    strip_bom,
    detect_line_ending,
    normalize_to_lf,
    restore_line_endings,
    normalize_for_fuzzy_match,
    fuzzy_find_text,
    FuzzyMatchResult,
)


class TestStripBom:
    """Tests for BOM handling."""

    def test_no_bom(self):
        """Content without BOM should be unchanged."""
        content = "Hello, world!"
        bom, text = strip_bom(content)
        assert bom == ""
        assert text == content

    def test_with_bom(self):
        """Content with BOM should have it stripped."""
        content = "\ufeffHello, world!"
        bom, text = strip_bom(content)
        assert bom == "\ufeff"
        assert text == "Hello, world!"

    def test_bom_only(self):
        """Content that is only BOM."""
        content = "\ufeff"
        bom, text = strip_bom(content)
        assert bom == "\ufeff"
        assert text == ""


class TestDetectLineEnding:
    """Tests for line ending detection."""

    def test_detect_lf(self):
        """Detect LF line endings."""
        content = "line1\nline2\nline3"
        assert detect_line_ending(content) == "\n"

    def test_detect_crlf(self):
        """Detect CRLF line endings."""
        content = "line1\r\nline2\r\nline3"
        assert detect_line_ending(content) == "\r\n"

    def test_mixed_with_more_crlf(self):
        """Mixed endings with more CRLF should return CRLF."""
        content = "line1\r\nline2\nline3\r\nline4\r\n"
        assert detect_line_ending(content) == "\r\n"

    def test_mixed_with_more_lf(self):
        """Mixed endings with more LF should return LF."""
        content = "line1\nline2\r\nline3\nline4\n"
        assert detect_line_ending(content) == "\n"

    def test_no_line_endings(self):
        """Content with no line endings defaults to LF."""
        content = "single line"
        assert detect_line_ending(content) == "\n"

    def test_empty_content(self):
        """Empty content defaults to LF."""
        assert detect_line_ending("") == "\n"


class TestNormalizeToLf:
    """Tests for line ending normalization."""

    def test_crlf_to_lf(self):
        """CRLF should be converted to LF."""
        content = "line1\r\nline2\r\n"
        assert normalize_to_lf(content) == "line1\nline2\n"

    def test_cr_to_lf(self):
        """CR should be converted to LF."""
        content = "line1\rline2\r"
        assert normalize_to_lf(content) == "line1\nline2\n"

    def test_mixed_to_lf(self):
        """Mixed line endings should all become LF."""
        content = "line1\r\nline2\rline3\n"
        assert normalize_to_lf(content) == "line1\nline2\nline3\n"

    def test_already_lf(self):
        """Content with LF should be unchanged."""
        content = "line1\nline2\n"
        assert normalize_to_lf(content) == content


class TestRestoreLineEndings:
    """Tests for line ending restoration."""

    def test_restore_to_crlf(self):
        """LF should be converted to CRLF."""
        content = "line1\nline2\n"
        assert restore_line_endings(content, "\r\n") == "line1\r\nline2\r\n"

    def test_restore_to_lf(self):
        """LF should remain LF."""
        content = "line1\nline2\n"
        assert restore_line_endings(content, "\n") == content

    def test_no_line_endings(self):
        """Content without line endings should be unchanged."""
        content = "single line"
        assert restore_line_endings(content, "\r\n") == content


class TestNormalizeForFuzzyMatch:
    """Tests for fuzzy match normalization."""

    def test_smart_single_quotes(self):
        """Smart single quotes should become regular quotes."""
        text = "It\u2019s a test"
        assert normalize_for_fuzzy_match(text) == "It's a test"

    def test_smart_double_quotes(self):
        """Smart double quotes should become regular quotes."""
        text = "\u201CHello\u201D"
        assert normalize_for_fuzzy_match(text) == '"Hello"'

    def test_various_dashes(self):
        """Various dashes should become regular hyphens."""
        text = "a\u2013b\u2014c\u2212d"
        assert normalize_for_fuzzy_match(text) == "a-b-c-d"

    def test_special_spaces(self):
        """Special spaces should become regular spaces."""
        text = "a\u00A0b\u2002c\u3000d"
        assert normalize_for_fuzzy_match(text) == "a b c d"

    def test_no_change_needed(self):
        """Regular ASCII text should be unchanged."""
        text = "Hello, world!"
        assert normalize_for_fuzzy_match(text) == text

    def test_combined_normalization(self):
        """Multiple Unicode variants should be normalized."""
        text = "\u201CHello\u201D\u2014it\u2019s\u00A0a\u2013test"
        assert normalize_for_fuzzy_match(text) == '"Hello"-it\'s a-test'


class TestFuzzyFindText:
    """Tests for fuzzy text finding."""

    def test_exact_match(self):
        """Exact match should be found."""
        content = "Hello, world!"
        match = fuzzy_find_text(content, "world")
        assert match.found
        assert match.index == 7
        assert match.match_length == 5
        assert not match.used_fuzzy_match

    def test_fuzzy_match_smart_quotes(self):
        """Fuzzy match should find text with smart quotes."""
        content = "It\u2019s a test"
        match = fuzzy_find_text(content, "It's")
        assert match.found
        assert match.used_fuzzy_match

    def test_fuzzy_match_smart_double_quotes(self):
        """Fuzzy match should find text with smart double quotes."""
        content = 'Say \u201CHello\u201D'
        match = fuzzy_find_text(content, '"Hello"')
        assert match.found
        assert match.used_fuzzy_match

    def test_fuzzy_match_dashes(self):
        """Fuzzy match should find text with dashes."""
        content = "test\u2013case"
        match = fuzzy_find_text(content, "test-case")
        assert match.found
        assert match.used_fuzzy_match

    def test_no_match(self):
        """No match should return found=False."""
        content = "Hello, world!"
        match = fuzzy_find_text(content, "goodbye")
        assert not match.found
        assert match.index == -1

    def test_match_at_start(self):
        """Match at the start of content."""
        content = "Hello, world!"
        match = fuzzy_find_text(content, "Hello")
        assert match.found
        assert match.index == 0

    def test_match_at_end(self):
        """Match at the end of content."""
        content = "Hello, world!"
        match = fuzzy_find_text(content, "world!")
        assert match.found
        assert match.index == 7

    def test_multiline_content(self):
        """Match across multiple lines."""
        content = "line1\nline2\nline3"
        match = fuzzy_find_text(content, "line2")
        assert match.found
        assert match.index == 6
