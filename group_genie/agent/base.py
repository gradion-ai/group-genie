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
    [`get_serialized`][group_genie.agent.base.Agent.get_serialized] and
    [`set_serialized`][group_genie.agent.base.Agent.set_serialized]), MCP server
    lifecycle management (via [`mcp`][group_genie.agent.base.Agent.mcp] context
    manager), and query processing with tool approval callbacks.

    State persistence is managed automatically by the framework and stored in JSON
    format. Persisted state is never transferred between different owners (users).

    Example:
        ```python
        class MyAgent(Agent):
            def __init__(self, system_prompt: str):
                self._history = []
                self._system_prompt = system_prompt

            def get_serialized(self):
                return {"history": self._history}

            def set_serialized(self, state):
                self._history = state["history"]

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
    def get_serialized(self) -> Any:
        """Serialize agent state for persistence.

        Returns conversation history and any other state needed to resume the agent
        after a restart. Called automatically by the framework before saving to
        [`DataStore`][group_genie.datastore.DataStore].

        Returns:
            Serializable state (must be JSON-compatible). Implementation-specific format.
        """
        ...

    @abstractmethod
    def set_serialized(self, state: Any):
        """Restore agent state from serialized data.

        Reconstructs conversation history and internal state from previously serialized
        data. Called automatically by the framework after loading from
        [`DataStore`][group_genie.datastore.DataStore].

        Args:
            state: Previously serialized state from
                [`get_serialized()`][group_genie.agent.base.Agent.get_serialized].
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
