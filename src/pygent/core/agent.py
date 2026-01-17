from __future__ import annotations

from collections.abc import AsyncIterator

from pygent.core.cache import ToolCache
from pygent.core.loop import LoopEvent, conversation_loop
from pygent.core.permissions import PermissionManager
from pygent.core.providers import LLMProvider
from pygent.session.models import Message, Session
from pygent.tools.registry import ToolRegistry


class Agent:
    """Main agent orchestrator.

    Attributes:
        provider: The LLM provider for completions.
        tools: Registry of available tools.
        permissions: Permission manager for tool execution.
        session: The current conversation session.
        tool_cache: Cache for tool results.
        system_prompt: Optional system prompt to prepend to conversations.
    """

    def __init__(
        self,
        provider: LLMProvider,
        tools: ToolRegistry,
        permissions: PermissionManager,
        session: Session,
        tool_cache: ToolCache | None = None,
        system_prompt: str | None = None,
    ) -> None:
        self.provider = provider
        self.tools = tools
        self.permissions = permissions
        self.session = session
        self.tool_cache = tool_cache or ToolCache()
        self.system_prompt = system_prompt

    async def run(self, user_message: str) -> AsyncIterator[LoopEvent]:
        """Run the agent with a user message.

        Args:
            user_message: The user's input message.

        Yields:
            LoopEvent instances for each step of the conversation.
        """
        # Add user message to session
        msg = Message(role="user", content=user_message)
        self.session.messages.append(msg)

        # Call conversation_loop with system prompt
        async for event in conversation_loop(self, self.session.messages, self.system_prompt):
            yield event
