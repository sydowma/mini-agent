"""Text processing utilities for fuzzy matching and encoding handling."""

import unicodedata
from dataclasses import dataclass
from typing import Tuple, Literal


# Unicode character mappings for fuzzy matching
SMART_QUOTE_MAPPING = {
    '\u2018': "'",  # LEFT SINGLE QUOTATION MARK
    '\u2019': "'",  # RIGHT SINGLE QUOTATION MARK
    '\u201A': "'",  # SINGLE LOW-9 QUOTATION MARK
    '\u201B': "'",  # SINGLE HIGH-REVERSED-9 QUOTATION MARK
    '\u201C': '"',  # LEFT DOUBLE QUOTATION MARK
    '\u201D': '"',  # RIGHT DOUBLE QUOTATION MARK
    '\u201E': '"',  # DOUBLE LOW-9 QUOTATION MARK
    '\u201F': '"',  # DOUBLE HIGH-REVERSED-9 QUOTATION MARK
}

DASH_MAPPING = {
    '\u2010': '-',  # HYPHEN
    '\u2011': '-',  # NON-BREAKING HYPHEN
    '\u2012': '-',  # FIGURE DASH
    '\u2013': '-',  # EN DASH
    '\u2014': '-',  # EM DASH
    '\u2015': '-',  # HORIZONTAL BAR
    '\u2212': '-',  # MINUS SIGN
}

SPACE_MAPPING = {
    '\u00A0': ' ',  # NO-BREAK SPACE
    '\u2002': ' ',  # EN SPACE
    '\u2003': ' ',  # EM SPACE
    '\u2004': ' ',  # THREE-PER-EM SPACE
    '\u2005': ' ',  # FOUR-PER-EM SPACE
    '\u2006': ' ',  # SIX-PER-EM SPACE
    '\u2007': ' ',  # FIGURE SPACE
    '\u2008': ' ',  # PUNCTUATION SPACE
    '\u2009': ' ',  # THIN SPACE
    '\u200A': ' ',  # HAIR SPACE
    '\u202F': ' ',  # NARROW NO-BREAK SPACE
    '\u205F': ' ',  # MEDIUM MATHEMATICAL SPACE
    '\u3000': ' ',  # IDEOGRAPHIC SPACE
}


def strip_bom(content: str) -> Tuple[str, str]:
    """
    Strip UTF-8 BOM from content if present.

    Args:
        content: The file content as a string

    Returns:
        Tuple of (bom, text_without_bom) where bom is '' or the BOM string
    """
    bom = ''
    if content.startswith('\ufeff'):
        bom = '\ufeff'
        content = content[1:]
    return bom, content


def detect_line_ending(content: str) -> Literal['\r\n', '\n']:
    """
    Detect the dominant line ending style in content.

    Args:
        content: The text content to analyze

    Returns:
        '\r\n' for CRLF, '\n' for LF (default)
    """
    crlf_count = content.count('\r\n')
    # Count standalone LF (not preceded by CR)
    lf_count = content.count('\n') - crlf_count

    if crlf_count > lf_count:
        return '\r\n'
    return '\n'


def normalize_to_lf(text: str) -> str:
    """
    Normalize all line endings to LF.

    Args:
        text: Text with potentially mixed line endings

    Returns:
        Text with all line endings converted to LF
    """
    return text.replace('\r\n', '\n').replace('\r', '\n')


def restore_line_endings(text: str, ending: str) -> str:
    """
    Restore line endings to the specified style.

    Args:
        text: Text with LF line endings
        ending: The line ending to use ('\r\n' or '\n')

    Returns:
        Text with the specified line endings
    """
    if ending == '\r\n':
        return text.replace('\n', '\r\n')
    return text


def normalize_for_fuzzy_match(text: str) -> str:
    """
    Normalize text for fuzzy matching by converting Unicode variants.

    This handles:
    - Smart quotes to regular quotes
    - Various dashes to regular hyphens
    - Various space characters to regular space
    - Unicode normalization (NFC)

    Args:
        text: The text to normalize

    Returns:
        Normalized text suitable for fuzzy comparison
    """
    # Apply Unicode normalization first
    text = unicodedata.normalize('NFC', text)

    # Create translation table
    result = []
    for char in text:
        if char in SMART_QUOTE_MAPPING:
            result.append(SMART_QUOTE_MAPPING[char])
        elif char in DASH_MAPPING:
            result.append(DASH_MAPPING[char])
        elif char in SPACE_MAPPING:
            result.append(SPACE_MAPPING[char])
        else:
            result.append(char)

    return ''.join(result)


@dataclass
class FuzzyMatchResult:
    """Result of a fuzzy text match operation."""
    found: bool
    index: int
    match_length: int
    used_fuzzy_match: bool
    content_for_replacement: str


def fuzzy_find_text(content: str, old_text: str) -> FuzzyMatchResult:
    """
    Find text in content using fuzzy matching.

    First tries exact match, then falls back to fuzzy matching with
    Unicode normalization.

    Args:
        content: The content to search in (should be LF-normalized)
        old_text: The text to find (should be LF-normalized)

    Returns:
        FuzzyMatchResult with match information
    """
    # Try exact match first
    index = content.find(old_text)
    if index != -1:
        return FuzzyMatchResult(
            found=True,
            index=index,
            match_length=len(old_text),
            used_fuzzy_match=False,
            content_for_replacement=content,
        )

    # Fall back to fuzzy matching
    normalized_content = normalize_for_fuzzy_match(content)
    normalized_old = normalize_for_fuzzy_match(old_text)

    fuzzy_index = normalized_content.find(normalized_old)
    if fuzzy_index != -1:
        # We need to find the corresponding position in the original content
        # This is complex because normalization may change character lengths
        # We'll use a character-by-character mapping approach

        # Find the corresponding original substring
        original_index = _find_original_index(content, normalized_content, fuzzy_index)
        original_end = _find_original_index(
            content, normalized_content, fuzzy_index + len(normalized_old)
        )

        if original_index is not None and original_end is not None:
            return FuzzyMatchResult(
                found=True,
                index=original_index,
                match_length=original_end - original_index,
                used_fuzzy_match=True,
                content_for_replacement=content,
            )

    return FuzzyMatchResult(
        found=False,
        index=-1,
        match_length=0,
        used_fuzzy_match=False,
        content_for_replacement=content,
    )


def _find_original_index(
    original: str,
    normalized: str,
    normalized_index: int
) -> int | None:
    """
    Find the index in original string corresponding to normalized index.

    This handles cases where normalization changes character counts.
    """
    orig_pos = 0
    norm_pos = 0

    while norm_pos < normalized_index and orig_pos < len(original):
        orig_char = original[orig_pos]
        norm_char = normalized[norm_pos]

        # Normalize the original character for comparison
        norm_orig = normalize_for_fuzzy_match(orig_char)

        if norm_orig == norm_char:
            norm_pos += 1
            orig_pos += 1
        elif norm_orig == '':
            # Character was removed by normalization (shouldn't happen with our normalization)
            orig_pos += 1
        elif len(norm_orig) == 1:
            norm_pos += 1
            orig_pos += 1
        else:
            # Multiple normalized chars from one original
            norm_pos += len(norm_orig)
            orig_pos += 1

    if norm_pos >= normalized_index:
        return orig_pos

    return None
