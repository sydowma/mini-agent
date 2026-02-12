"""Theme configuration for the TUI."""

from dataclasses import dataclass


@dataclass
class Theme:
    """Theme colors and styles."""
    # Background colors
    bg_primary: str = "#1a1b26"
    bg_secondary: str = "#24283b"
    bg_tertiary: str = "#414868"

    # Text colors
    text_primary: str = "#c0caf5"
    text_secondary: str = "#a9b1d6"
    text_muted: str = "#565f89"

    # Accent colors
    accent_primary: str = "#7aa2f7"
    accent_secondary: str = "#bb9af7"
    accent_success: str = "#9ece6a"
    accent_warning: str = "#e0af68"
    accent_error: str = "#f7768e"

    # Role colors
    user_color: str = "#7aa2f7"
    assistant_color: str = "#9ece6a"
    tool_color: str = "#e0af68"
    system_color: str = "#565f89"


# Default theme instance
DEFAULT_THEME = Theme()
