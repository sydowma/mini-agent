"""CLI entry point for mini-agent."""

import asyncio
import os
import sys
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.live import Live
from rich.text import Text
from dotenv import load_dotenv

from .agent import Agent, AgentEvent, AgentEventType
from .session import SessionManager
from .tools import (
    ReadTool, WriteTool, EditTool, BashTool,
    GrepTool, FindTool, ListTool,
)
from .tui import MiniAgentApp


def load_env_files():
    """Load .env files from various locations."""
    # Load from current directory
    load_dotenv(Path.cwd() / ".env")
    # Load from home directory
    load_dotenv(Path.home() / ".mini-agent" / ".env")


# Load environment variables at module import
load_env_files()

app = typer.Typer(
    name="mini-agent",
    help="A Python coding AI agent with TUI interface",
)
console = Console()


# Model to provider mapping
MODEL_PROVIDERS = {
    # OpenAI models
    "gpt-4o": "openai",
    "gpt-4o-mini": "openai",
    "gpt-4-turbo": "openai",
    "gpt-4": "openai",
    "gpt-3.5-turbo": "openai",
    "o1": "openai",
    "o1-mini": "openai",
    "o1-preview": "openai",

    # Anthropic models
    "claude-sonnet-4-20250514": "anthropic",
    "claude-sonnet-4": "anthropic",
    "claude-3-5-sonnet-20241022": "anthropic",
    "claude-3-5-sonnet": "anthropic",
    "claude-3-5-haiku-20241022": "anthropic",
    "claude-3-5-haiku": "anthropic",
    "claude-3-opus-20240229": "anthropic",
    "claude-3-opus": "anthropic",
    "claude-3-sonnet-20240229": "anthropic",
    "claude-3-sonnet": "anthropic",
    "claude-3-haiku-20240307": "anthropic",
    "claude-3-haiku": "anthropic",

    # Zhipu AI models (Anthropic-compatible API)
    "glm-4-plus": "anthropic",
    "glm-4-air": "anthropic",
    "glm-4-airx": "anthropic",
    "glm-4-flash": "anthropic",
    "glm-4-long": "anthropic",
    "glm-4v-plus": "anthropic",
    "glm-4v-flash": "anthropic",
    "glm-z1-air": "anthropic",
    "glm-z1-airx": "anthropic",
    "glm-z1-flash": "anthropic",
}


def detect_provider(model: str) -> str:
    """Detect provider from model name."""
    # Check exact match first
    if model in MODEL_PROVIDERS:
        return MODEL_PROVIDERS[model]

    # Check prefix match
    model_lower = model.lower()
    if model_lower.startswith("gpt") or model_lower.startswith("o1"):
        return "openai"
    if model_lower.startswith("claude") or model_lower.startswith("glm"):
        return "anthropic"

    # Default to anthropic (supports more custom endpoints)
    return "anthropic"


def create_agent(
    model: str = "gpt-4o",
    provider: Optional[str] = None,
    working_directory: str = ".",
) -> Agent:
    """Create and configure an agent with all tools."""
    # Auto-detect provider if not specified
    if provider is None:
        provider = detect_provider(model)

    agent = Agent(
        model=model,
        provider_name=provider,
        working_directory=working_directory,
    )

    agent.add_tools([
        ReadTool(),
        WriteTool(),
        EditTool(),
        BashTool(),
        GrepTool(),
        FindTool(),
        ListTool(),
    ])

    return agent


@app.command()
def main(
    model: str = typer.Option(
        None,  # Will be set from env or default
        "--model", "-m",
        help="The model to use (e.g., gpt-4o, claude-sonnet-4, glm-4-plus)",
    ),
    provider: Optional[str] = typer.Option(
        None,
        "--provider", "-p",
        help="Provider to use (openai, anthropic). Auto-detected from model if not specified.",
    ),
    session: Optional[str] = typer.Option(
        None,
        "--session", "-s",
        help="Session ID to load",
    ),
    mode: str = typer.Option(
        "interactive",
        "--mode",
        help="Output mode: interactive (TUI), print (one-shot), json",
    ),
    working_dir: str = typer.Option(
        None,
        "--dir", "-d",
        help="Working directory",
    ),
    list_sessions: bool = typer.Option(
        False,
        "--list-sessions", "-l",
        help="List saved sessions",
    ),
    list_providers: bool = typer.Option(
        False,
        "--list-providers",
        help="List available providers",
    ),
):
    """
    Mini Agent - A Python coding AI agent.

    Run without arguments to start the interactive TUI.

    Configuration is loaded from .env file (current directory or ~/.mini-agent/.env).

    Examples:
        mini-agent                              # Start interactive TUI
        mini-agent -m gpt-4o                    # Use GPT-4o
        mini-agent -m glm-4-plus                # Use Zhipu GLM-4-Plus
        mini-agent -m claude-3-5-sonnet         # Use Claude 3.5 Sonnet
        mini-agent -p anthropic -m claude-3-opus  # Explicit provider
        mini-agent -s abc12345                  # Load a session
        mini-agent -l                           # List sessions
    """
    # Get defaults from environment
    env_model = os.getenv("DEFAULT_MODEL", "claude-sonnet-4-20250514")
    env_working_dir = os.getenv("WORKING_DIRECTORY", ".")

    # Apply defaults
    if model is None:
        model = env_model
    if working_dir is None:
        working_dir = env_working_dir
    # Handle list providers
    if list_providers:
        _list_providers()
        return

    # Handle list sessions
    if list_sessions:
        _list_sessions()
        return

    # Resolve working directory
    working_directory = os.path.abspath(working_dir)

    # Auto-detect provider if not specified
    actual_provider = provider or detect_provider(model)

    # Run in appropriate mode
    if mode == "interactive":
        _run_interactive(model, actual_provider, session, working_directory)
    elif mode == "print":
        _run_print_mode(model, actual_provider, working_directory)
    elif mode == "json":
        _run_json_mode(model, actual_provider, working_directory)
    else:
        console.print(f"[red]Unknown mode: {mode}[/]")
        sys.exit(1)


def _list_providers() -> None:
    """List available providers."""
    from .ai.providers import ProviderRegistry

    console.print("[bold]Available Providers:[/]\n")

    for name in ProviderRegistry.list_providers():
        provider = ProviderRegistry.get(name)
        if provider:
            console.print(f"  [cyan]{name}[/] - Default model: {provider.default_model}")

    console.print("\n[bold]Supported Models:[/]\n")
    console.print("  [green]OpenAI:[/] gpt-4o, gpt-4o-mini, gpt-4-turbo, o1, o1-mini")
    console.print("  [green]Anthropic:[/] claude-sonnet-4-20250514, claude-3-5-sonnet, claude-3-opus, claude-3-haiku")


def _list_sessions() -> None:
    """List saved sessions."""
    manager = SessionManager()
    sessions = manager.list_sessions()

    if not sessions:
        console.print("[yellow]No saved sessions found.[/]")
        return

    console.print("[bold]Saved Sessions:[/]\n")

    for session in sessions:
        console.print(f"  [cyan]{session.id}[/] - {session.name}")
        console.print(f"    Model: {session.model}, Messages: {len(session.messages)}")
        console.print(f"    Updated: {session.updated_at}")
        console.print()


def _run_interactive(
    model: str,
    provider: str,
    session_id: Optional[str],
    working_directory: str,
) -> None:
    """Run the interactive TUI."""
    tui_app = MiniAgentApp(
        model=model,
        provider_name=provider,
        session_id=session_id,
        working_directory=working_directory,
    )
    tui_app.run()


def _run_print_mode(model: str, provider: str, working_directory: str) -> None:
    """Run in print mode (one-shot from stdin)."""
    # Read input from stdin
    if sys.stdin.isatty():
        console.print("[red]Error: print mode requires input from stdin[/]")
        console.print("Usage: echo 'your prompt' | mini-agent --mode print")
        sys.exit(1)

    prompt = sys.stdin.read().strip()
    if not prompt:
        console.print("[red]Error: No input provided[/]")
        sys.exit(1)

    agent = create_agent(model, provider, working_directory)

    # Track streaming output
    current_text = ""

    def on_event(event: AgentEvent):
        nonlocal current_text
        if event.type == AgentEventType.STREAM_TEXT:
            delta = event.data.get("delta", "") if event.data else ""
            current_text += delta
            print(delta, end="", flush=True)

    agent.on_event(on_event)

    # Run the agent
    try:
        asyncio.run(agent.prompt(prompt))
        print()  # Final newline
    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted[/]")
    except Exception as e:
        console.print(f"\n[red]Error: {e}[/]")
        sys.exit(1)


def _run_json_mode(model: str, provider: str, working_directory: str) -> None:
    """Run in JSON mode (one-shot from stdin with JSON output)."""
    import json

    # Read input from stdin
    if sys.stdin.isatty():
        console.print(json.dumps({"error": "JSON mode requires input from stdin"}))
        sys.exit(1)

    prompt = sys.stdin.read().strip()
    if not prompt:
        console.print(json.dumps({"error": "No input provided"}))
        sys.exit(1)

    agent = create_agent(model, provider, working_directory)

    # Collect all content
    text_parts = []
    tool_calls = []

    def on_event(event: AgentEvent):
        if event.type == AgentEventType.STREAM_TEXT:
            delta = event.data.get("delta", "") if event.data else ""
            text_parts.append(delta)
        elif event.type == AgentEventType.TOOL_RESULT:
            tool_calls.append(event.data)

    agent.on_event(on_event)

    # Run the agent
    try:
        response = asyncio.run(agent.prompt(prompt))

        result = {
            "text": "".join(text_parts),
            "tool_calls": tool_calls,
            "model": model,
            "provider": provider,
        }
        print(json.dumps(result, indent=2))

    except Exception as e:
        print(json.dumps({"error": str(e)}))
        sys.exit(1)


if __name__ == "__main__":
    app()
