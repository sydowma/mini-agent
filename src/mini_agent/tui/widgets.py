"""TUI widgets for mini-agent."""

from textual.widget import Widget
from textual.app import ComposeResult
from textual.containers import ScrollableContainer, Horizontal, Vertical
from textual.widgets import Static, Input, Button, Label
from textual.reactive import reactive

from .theme import DEFAULT_THEME


class MessageWidget(Static):
    """Widget to display a single message."""

    role = reactive("user")
    content = reactive("")

    def __init__(self, role: str, content: str, **kwargs):
        super().__init__(**kwargs)
        self.role = role
        self.content = content

    def render(self) -> str:
        # Color based on role
        if self.role == "user":
            color = DEFAULT_THEME.user_color
            prefix = "👤 You"
        elif self.role == "assistant":
            color = DEFAULT_THEME.assistant_color
            prefix = "🤖 Assistant"
        else:
            color = DEFAULT_THEME.tool_color
            prefix = "⚙️ Tool"

        return f"[bold {color}]{prefix}[/]\n{self.content}"


class ToolExecutionWidget(Static):
    """Widget to display tool execution."""

    tool_name = reactive("")
    status = reactive("pending")
    result = reactive("")

    def __init__(self, tool_name: str, **kwargs):
        super().__init__(**kwargs)
        self.tool_name = tool_name

    def render(self) -> str:
        color = DEFAULT_THEME.tool_color
        status_icon = "⏳" if self.status == "running" else "✓"

        lines = [f"[bold {color}]{status_icon} Tool: {self.tool_name}[/]"]

        if self.result:
            # Truncate result if too long
            result_text = self.result
            if len(result_text) > 500:
                result_text = result_text[:500] + "..."
            lines.append(f"[dim]{result_text}[/]")

        return "\n".join(lines)


class StreamingTextWidget(Static):
    """Widget for streaming text output."""

    text = reactive("")
    is_streaming = reactive(False)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._buffer = ""

    def append(self, text: str) -> None:
        """Append text to the buffer."""
        self._buffer += text
        self.text = self._buffer

    def clear(self) -> None:
        """Clear the buffer."""
        self._buffer = ""
        self.text = ""

    def render(self) -> str:
        if not self.text:
            return ""

        color = DEFAULT_THEME.assistant_color
        prefix = "🤖 Assistant" if not self.is_streaming else "🤖 Assistant (streaming...)"

        return f"[bold {color}]{prefix}[/]\n{self.text}"


class InputWidget(Horizontal):
    """Widget for user input."""

    def __init__(self, placeholder: str = "Type your message...", **kwargs):
        super().__init__(**kwargs)
        self.placeholder = placeholder

    def compose(self) -> ComposeResult:
        yield Input(placeholder=self.placeholder, id="message-input")
        yield Button("Send", variant="primary", id="send-button")


class StatusBar(Static):
    """Status bar widget."""

    status = reactive("Ready")
    model = reactive("gpt-4o")
    session_id = reactive("")

    def render(self) -> str:
        parts = [f"Model: {self.model}"]

        if self.session_id:
            parts.append(f"Session: {self.session_id}")

        parts.append(f"Status: {self.status}")

        return " | ".join(parts)
