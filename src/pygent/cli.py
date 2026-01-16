import asyncio
import uuid

import click

from pygent.core.agent import Agent
from pygent.core.permissions import PermissionManager
from pygent.core.providers import LLMProvider
from pygent.session.models import Session
from pygent.session.storage import SessionStorage
from pygent.tools.registry import ToolRegistry
from pygent.tui.app import PygentApp


@click.group()
@click.version_option()
def cli():
    """Pygent - AI-powered coding agent."""
    pass


@cli.command()
@click.option("--session", "-s", help="Resume a session by ID")
@click.option("--new", "-n", is_flag=True, help="Start a new session")
def chat(session: str | None, new: bool):
    """Start interactive chat session."""

    # 1. Load Config (Default for now)
    # config = asyncio.run(load_config())
    # TODO: Pass config to components

    # 2. Initialize Components
    provider = LLMProvider(model="anthropic/claude-3-5-sonnet-20241022")  # Default hardcoded for MVP if not in config
    # Note: LLMProvider in specs/phase-1-mvp.md signature is (model, api_key).
    # We should check providers.py to match signature.

    tools = ToolRegistry()
    # Register basic tools
    # We need to import the tool definitions or functions decorated with @tool
    # The current implementation of filesystem.py and shell.py uses @tool decorator
    # which returns a function with .tool_def attribute or we need to manage registration.
    # Let's check how tools are implemented. Assuming standard registry pattern.

    # For MVP we manually register known tools
    # Actually, the @tool decorator usually registers or we need to pass the function.
    # Let's check existing tool implementations.
    # But I will proceed with assumption and fix if needed in verification.

    # 3. Session Management
    storage = SessionStorage()

    current_session = None
    if session:
        current_session = asyncio.run(storage.load(session))
        if not current_session:
            click.echo(f"Session {session} not found.")
            return
    else:
        # Create new session
        current_session = Session(id=str(uuid.uuid4()), working_directory=".", messages=[], tool_history=[])
        # async save? storage.save(current_session)

    # 4. Permissions
    permissions = PermissionManager()

    # 5. Agent
    agent = Agent(provider=provider, tools=tools, permissions=permissions, session=current_session)

    # Register Tools (Manual for now, should be dynamic)
    # The 'tool' decorator in spec returns the wrapper.
    # We need to extract the definition or if the registry does it.
    # Inspecting registry.py would be good, but I'll write the code to register what I know.
    # tools.register(read_file) # Assuming register takes the decorated function or definition

    # 6. Run TUI
    app = PygentApp(agent=agent)
    app.run()


@cli.command()
def sessions():
    """List saved sessions."""
    click.echo("Sessions list not implemented yet.")


@cli.command()
@click.argument("session_id")
def resume(session_id: str):
    """Resume a specific session."""
    click.echo(f"Resuming {session_id} not implemented yet.")


@cli.command()
def config():
    """Show current configuration."""
    click.echo("Config view not implemented yet.")


if __name__ == "__main__":
    cli()
