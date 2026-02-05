from abc import ABC, abstractmethod
from contextlib import AbstractAsyncContextManager
from dataclasses import dataclass, field
from typing import Any

from group_genie.agent.approval import ApprovalCallback
from group_genie.message import Attachment


@dataclass
class AgentInfo:
    """Metadata about an agent.

    Provides descriptive information about an agent for configuration purposes.
    Used by [`AgentFactory`][group_genie.agent.factory.AgentFactory] coordinator
    agents to learn about available subagents.

    Attributes:
        name: Unique identifier for the agent (e.g., "search", "math", "system").
        description: Description of the agent's capabilities and purpose. Used by
            coordinator agents to select subagents.
        emoji: Optional emoji code for visual identification.
        idle_timeout: Optional timeout in seconds after which an idle agent is stopped
            to free resources. None means no timeout.

    Example:
        ```python
        info = AgentInfo(
            name="search",
            description="Searches the web for current information",
            emoji="mag",
            idle_timeout=300.0
        )
        ```
    """

    name: str
    description: str
    emoji: str | None = None
    idle_timeout: float | None = None


@dataclass
class AgentInput:
    """Input data for agent execution.

    Encapsulates all information needed for an agent to process a query, including
    the query text, any attached files, and user-specific preferences.

    Attributes:
        query: The query text for the agent to process. Should be self-contained
            with all necessary context.
        attachments: List of file attachments that accompany the query.
        preferences: Optional user-specific preferences that customize the agent's
            response style and format. Typically a free-form string with bullet points.

    Example:
        ```python
        input = AgentInput(
            query="Analyze this report and summarize key findings",
            attachments=[Attachment(
                path="/tmp/report.pdf",
                name="Q3 Report",
                media_type="application/pdf"
            )],
            preferences="Concise responses, no emojis"
        )
        ```
    """

    query: str
    attachments: list[Attachment] = field(default_factory=list)
    preferences: str | None = None


class Agent(ABC):
    """Abstract base class for creating custom agents.

    Agents are the core processing units that handle delegated queries from group
    reasoners. They can be standalone agents or coordinator agents that orchestrate
    subagents in a hierarchical architecture.

    Implementations must handle conversation state serialization (via
    [`get_new_messages`][group_genie.agent.base.Agent.get_new_messages] and
    [`set_serialized`][group_genie.agent.base.Agent.set_serialized]), MCP server
    lifecycle management (via [`mcp`][group_genie.agent.base.Agent.mcp] context
    manager), and query processing with tool approval callbacks.

    State persistence is managed automatically by the framework using JSONL format
    (one JSON object per line). Persisted state is never transferred between
    different owners (users).

    Example:
        ```python
        class MyAgent(Agent):
            def __init__(self, system_prompt: str):
                self._history = []
                self._new_messages = []
                self._system_prompt = system_prompt

            def get_new_messages(self):
                return self._new_messages

            def set_serialized(self, lines):
                self._history = lines
                self._new_messages = []

            @asynccontextmanager
            async def mcp(self):
                # Initialize MCP servers if needed
                yield self

            async def run(self, input: AgentInput, callback: ApprovalCallback) -> str:
                # Process query and return response
                return f"Processed: {input.query}"
        ```
    """

    @abstractmethod
    def get_new_messages(self) -> list[Any]:
        """Return messages from the last run() call for appending.

        Returns the new messages generated during the most recent
        [`run()`][group_genie.agent.base.Agent.run] call. Called automatically
        by the framework after each run to persist incremental state.

        Returns:
            List of JSON-serializable message objects to append to storage.
        """
        ...

    @abstractmethod
    def set_serialized(self, lines: list[Any]):
        """Reconstruct agent history from all JSONL lines.

        Rebuilds conversation history from all previously stored lines. Called
        automatically by the framework when loading from
        [`DataStore`][group_genie.datastore.DataStore].

        Args:
            lines: All previously stored lines from the JSONL file.
        """
        ...

    @abstractmethod
    def mcp(self) -> AbstractAsyncContextManager["Agent"]:
        """Context manager for MCP server lifecycle.

        Manages the lifecycle of any MCP (Model Context Protocol) servers used by
        this agent. Connects to the agent's MCP servers on entering the context,
        and disconnects on exit.

        Returns:
            Async context manager that yields self.
        """
        ...

    @abstractmethod
    async def run(self, input: AgentInput, callback: ApprovalCallback) -> str:
        """Process a query and return a response.

        Executes the agent's core logic to process the query. Must use the provided
        callback for any tool calls that require approval. Agent execution blocks
        until all approvals are granted or denied.

        Args:
            input: The query and associated data to process.
            callback: Async callback for requesting approval of tool calls. Must be
                called for any tool execution that requires user approval.

        Returns:
            The agent's response as a string.
        """
        ...
