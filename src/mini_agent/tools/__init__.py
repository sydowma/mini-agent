"""Tools for mini-agent."""

from .base import BaseTool
from .registry import ToolRegistry, get_tool, register_tool, list_tools
from .truncate import (
    truncate_head,
    truncate_tail,
    truncate_string_to_bytes_from_end,
    truncate_string_to_bytes_from_start,
    TruncationResult,
)
from .text_utils import (
    strip_bom,
    detect_line_ending,
    normalize_to_lf,
    restore_line_endings,
    normalize_for_fuzzy_match,
    fuzzy_find_text,
    FuzzyMatchResult,
)
from .diff_utils import (
    generate_diff_string,
    format_diff_for_output,
    DiffResult,
)
from .read import ReadTool
from .write import WriteTool
from .edit import EditTool
from .bash import BashTool
from .grep import GrepTool
from .find import FindTool
from .ls import ListTool

__all__ = [
    "BaseTool",
    "ToolRegistry",
    "get_tool",
    "register_tool",
    "list_tools",
    "truncate_head",
    "truncate_tail",
    "truncate_string_to_bytes_from_end",
    "truncate_string_to_bytes_from_start",
    "TruncationResult",
    "strip_bom",
    "detect_line_ending",
    "normalize_to_lf",
    "restore_line_endings",
    "normalize_for_fuzzy_match",
    "fuzzy_find_text",
    "FuzzyMatchResult",
    "generate_diff_string",
    "format_diff_for_output",
    "DiffResult",
    "ReadTool",
    "WriteTool",
    "EditTool",
    "BashTool",
    "GrepTool",
    "FindTool",
    "ListTool",
]
