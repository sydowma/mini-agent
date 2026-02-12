"""Main TUI application for mini-agent."""

import asyncio
from typing import Optional

from textual.app import App, ComposeResult
from textual.containers import ScrollableContainer, Vertical, Horizontal
from textual.widgets import Header, Footer, Static, Input, Button
from textual.reactive import reactive
from textual.binding import Binding

from ..agent import Agent, AgentEvent, AgentEventType
from ..session import SessionManager
from ..tools import ReadTool, WriteTool, EditTool, BashTool, GrepTool, FindTool, ListTool
from .widgets import MessageWidget, ToolExecutionWidget, StreamingTextWidget, StatusBar
from .theme import DEFAULT_THEME


class MiniAgentApp(App):
    """Main TUI application for Mini Agent."""

    CSS = f"""
    Screen {{
        background: {DEFAULT_THEME.bg_primary};
    }}

    .message-container {{
        height: 1fr;
        background: {DEFAULT_THEME.bg_secondary};
        padding: 1;
    }}

    .input-container {{
        height: auto;
        background: {DEFAULT_THEME.bg_primary};
        padding: 1;
        border-top: solid {DEFAULT_THEME.bg_tertiary};
    }}

    Input {{
        background: {DEFAULT_THEME.bg_secondary};
        color: {DEFAULT_THEME.text_primary};
        border: solid {DEFAULT_THEME.bg_tertiary};
    }}

    Input:focus {{
        border: solid {DEFAULT_THEME.accent_primary};
    }}

    Button {{
        background: {DEFAULT_THEME.accent_primary};
        color: {DEFAULT_THEME.bg_primary};
    }}

    .status-bar {{
        background: {DEFAULT_THEME.bg_tertiary};
        color: {DEFAULT_THEME.text_primary};
        padding: 0 1;
    }}

    MessageWidget {{
        margin: 1 0;
        padding: 1;
        background: {DEFAULT_THEME.bg_secondary};
    }}

    StreamingTextWidget {{
        margin: 1 0;
        padding: 1;
        background: {DEFAULT_THEME.bg_secondary};
    }}

    ToolExecutionWidget {{
        margin: 1 0;
        padding: 1;
        background: {DEFAULT_THEME.bg_tertiary};
    }}
    """

    BINDINGS = [
        Binding("ctrl+c", "quit", "Quit"),
        Binding("ctrl+n", "new_session", "New Session"),
        Binding("ctrl+s", "save_session", "Save Session"),
        Binding("ctrl+l", "clear", "Clear"),
    ]

    status = reactive("Ready")
    is_processing = reactive(False)

    def __init__(
        self,
        model: str = "claude-sonnet-4-20250514",
        provider_name: str = "anthropic",
        session_id: Optional[str] = None,
        working_directory: str = ".",
    ):
        super().__init__()
        self.model = model
        self.provider_name = provider_name
        self.session_id = session_id
        self.working_directory = working_directory

        # Initialize agent
        self.agent = Agent(
            model=model,
            provider_name=provider_name,
            working_directory=working_directory,
        )

        # Add tools
        self.agent.add_tools([
            ReadTool(),
            WriteTool(),
            EditTool(),
            BashTool(),
            GrepTool(),
            FindTool(),
            ListTool(),
        ])

        # Initialize session manager
        self.session_manager = SessionManager()

        # Streaming widget reference
        self._streaming_widget: Optional[StreamingTextWidget] = None

    def compose(self) -> ComposeResult:
        yield Header()
        yield ScrollableContainer(
            Static("Welcome to Mini Agent! Type your message below.", id="welcome"),
            id="message-container",
        )
        yield Horizontal(
            Input(placeholder="Type your message...", id="message-input"),
            Button("Send", variant="primary", id="send-button"),
            classes="input-container",
        )
        yield StatusBar(classes="status-bar")

    def on_mount(self) -> None:
        """Called when app is mounted."""
        # Focus the input
        self.query_one("#message-input", Input).focus()

        # Load or create session
        if self.session_id:
            self.session_manager.load_session(self.session_id)
        else:
            self.session_manager.create_session(model=self.model)

        # Update status bar
        self._update_status_bar()

        # Register event handler
        self.agent.on_event(self._on_agent_event)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle input submission."""
        if event.input.id == "message-input":
            self._send_message(event.value)
            event.input.value = ""

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press."""
        if event.button.id == "send-button":
            input_widget = self.query_one("#message-input", Input)
            self._send_message(input_widget.value)
            input_widget.value = ""

    def action_new_session(self) -> None:
        """Create a new session."""
        self.session_manager.create_session(model=self.model)
        self.agent.clear_messages()
        self._clear_messages()
        self._update_status_bar()

    def action_save_session(self) -> None:
        """Save the current session."""
        self.session_manager.update_session_messages(
            [m.to_dict() for m in self.agent.get_messages()]
        )
        self.status = "Session saved"
        self._update_status_bar()

    def action_clear(self) -> None:
        """Clear the message display."""
        self._clear_messages()

    def _send_message(self, text: str) -> None:
        """Send a message to the agent."""
        if not text.strip() or self.is_processing:
            return

        # Add user message to display
        self._add_message("user", text)

        # Start processing
        self.is_processing = True
        self.status = "Processing..."
        self._update_status_bar()

        # Create streaming widget
        self._streaming_widget = StreamingTextWidget()
        self._streaming_widget.is_streaming = True
        container = self.query_one("#message-container", ScrollableContainer)
        container.mount(self._streaming_widget)
        container.scroll_end()

        # Run agent in background
        asyncio.create_task(self._run_agent(text))

    async def _run_agent(self, text: str) -> None:
        """Run the agent with the given text."""
        try:
            response = await self.agent.prompt(text)

            # Finalize streaming widget
            if self._streaming_widget:
                # Fallback: if provider didn't emit stream deltas, show final text.
                if not self._streaming_widget.text and response.text:
                    self._streaming_widget.text = response.text
                self._streaming_widget.is_streaming = False
                final_text = self._streaming_widget.text
                self._streaming_widget.remove()
                self._streaming_widget = None

                # Convert streaming output into a static assistant message.
                if final_text:
                    self._add_message("assistant", final_text)

            self.status = "Ready"

        except Exception as e:
            self._add_message("system", f"Error: {e}")
            self.status = f"Error: {e}"

        finally:
            self.is_processing = False
            self._update_status_bar()

    def _on_agent_event(self, event: AgentEvent) -> None:
        """Handle agent events."""
        # Log to file for debugging
        with open("/tmp/mini-agent-events.log", "a") as f:
            f.write(f"[DEBUG TUI] Event received: {event.type}, data: {str(event.data)[:100]}\n")

        if event.type == AgentEventType.STREAM_TEXT:
            if self._streaming_widget and event.data:
                delta = event.data.get("delta", "")
                self._streaming_widget.append(delta)
                container = self.query_one("#message-container", ScrollableContainer)
                container.scroll_end()

        elif event.type == AgentEventType.TOOL_CALL:
            if event.data:
                status = event.data.get("status", "")
                tool_name = event.data.get("tool_name", "unknown")
                if status == "started":
                    self._add_tool_widget(tool_name)

        elif event.type == AgentEventType.TOOL_RESULT:
            if event.data:
                tool_name = event.data.get("tool_name", "unknown")
                result = event.data.get("result", "")
                self._update_tool_result(tool_name, result)

    def _add_message(self, role: str, content: str) -> None:
        """Add a message widget to the display."""
        container = self.query_one("#message-container", ScrollableContainer)
        widget = MessageWidget(role=role, content=content)
        container.mount(widget)
        container.scroll_end()

    def _add_tool_widget(self, tool_name: str) -> None:
        """Add a tool execution widget."""
        container = self.query_one("#message-container", ScrollableContainer)
        widget = ToolExecutionWidget(tool_name=tool_name)
        widget.status = "running"
        container.mount(widget)
        container.scroll_end()

    def _update_tool_result(self, tool_name: str, result: str) -> None:
        """Update tool execution result."""
        # Find the last tool widget with this name
        container = self.query_one("#message-container", ScrollableContainer)
        for widget in reversed(container.children):
            if isinstance(widget, ToolExecutionWidget) and widget.tool_name == tool_name:
                widget.status = "completed"
                widget.result = result
                break

    def _clear_messages(self) -> None:
        """Clear all messages."""
        container = self.query_one("#message-container", ScrollableContainer)
        container.remove_children()
        self._streaming_widget = None

    def _update_status_bar(self) -> None:
        """Update the status bar."""
        info = self.session_manager.get_session_info()
        session_id = info.get("id", "") if info else ""

        status_bar = self.query_one(".status-bar", StatusBar)
        status_bar.status = self.status
        status_bar.model = self.model
        status_bar.session_id = session_id[:8] if session_id else ""

    async def run_async(self, **kwargs) -> None:
        """Run the app asynchronously."""
        await super().run_async(**kwargs)
