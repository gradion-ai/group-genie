import inspect
from typing import Any, Awaitable, Callable

from group_genie.agent.base import Agent, AgentInfo
from group_genie.secrets import SecretsProvider

AsyncTool = Callable[..., Awaitable[Any]]

SingleAgentFactoryFn = Callable[[dict[str, str]], Agent]
"""Factory function signature for creating standalone agents.

Creates agents that process queries independently without orchestrating subagents.
These are "leaf" agents in an agent hierarchy.

Args:
    secrets (dict[str, str]): User-specific credentials (e.g., API keys) retrieved from a
        [`SecretsProvider`][group_genie.secrets.SecretsProvider]. Common keys include
        "GOOGLE_API_KEY", "BRAVE_API_KEY", etc.

Returns:
    A configured [`Agent`][group_genie.agent.base.Agent] instance ready to process
        queries.

Example:
    ```python
    def create_search_agent(secrets: dict[str, str]) -> Agent:
        model = GoogleModel(
            "gemini-3-flash-preview",
            provider=GoogleProvider(api_key=secrets.get("GOOGLE_API_KEY", "")),
        )
        return DefaultAgent(
            system_prompt="You are a web search specialist",
            model=model,
            builtin_tools=[WebSearchTool()],
        )
    ```
"""

MultiAgentFactoryFn = Callable[[dict[str, str], dict[str, AsyncTool], list[AgentInfo]], Agent]
"""Factory function signature for creating coordinator agents.

Creates agents that can orchestrate other agents as subagents. These coordinator
agents receive information about available subagents and framework-provided tools
like `run_subagent` to delegate work.

Args:
    secrets (dict[str, str]): User-specific credentials (e.g., API keys) retrieved from a
        [`SecretsProvider`][group_genie.secrets.SecretsProvider].
    extra_tools (dict[str, AsyncTool]): Framework-provided tools. Always includes `run_subagent`
        for delegating to subagents. May include `get_group_chat_messages` and other tools depending
        on the framework configuration.
    agent_infos (list[AgentInfo]): Metadata about all other registered agents (excluding the coordinator
        itself). Used to inform the coordinator what subagents are available. Each entry
        is an [`AgentInfo`][group_genie.agent.base.AgentInfo] instance.

Returns:
    A configured [`Agent`][group_genie.agent.base.Agent] instance capable of
        orchestrating subagents.

Example:
    ```python
    def create_coordinator(
        secrets: dict[str, str],
        extra_tools: dict[str, AsyncTool],
        agent_infos: list[AgentInfo],
    ) -> Agent:
        system_prompt = f"You can delegate to: {[a.name for a in agent_infos]}"
        return DefaultAgent(
            system_prompt=system_prompt,
            model="google-gla:gemini-3-flash-preview",
            tools=[extra_tools["run_subagent"]],
        )
    ```
"""


class AgentFactory:
    """Factory for creating agent instances.

    [`AgentFactory`][group_genie.agent.factory.AgentFactory] provides centralized
    agent creation and configuration. It supports two types of agents:

    1. Standalone agents (SingleAgentFactoryFn): Simple agents that process queries
       independently without subagent orchestration.

    2. Coordinator agents (MultiAgentFactoryFn): Complex agents that can run other
       agents as subagents, receiving information about available subagents and
       extra tools (like run_subagent).

    The factory automatically provides user-specific secrets to agents and maintains
    agent metadata for introspection.

    Example:
        ```python
        # Standalone agent factory
        def create_search_agent(secrets: dict[str, str]) -> Agent:
            return DefaultAgent(
                system_prompt="You are a search specialist",
                model="google-gla:google-gla:gemini-3-flash-preview",
                builtin_tools=[WebSearchTool()],
            )

        # Coordinator agent factory
        def create_coordinator(
            secrets: dict[str, str],
            extra_tools: dict[str, AsyncTool],
            agent_infos: list[AgentInfo]
        ) -> Agent:
            # Has access to run_subagent tool and info about subagents
            return DefaultAgent(
                system_prompt=f"Available subagents: {agent_infos}",
                tools=[extra_tools["run_subagent"]],
            )

        # Create factory
        factory = AgentFactory(
            system_agent_factory=create_coordinator,
            secrets_provider=my_secrets_provider,
        )

        # Register subagents
        factory.add_agent_factory_fn(
            factory_fn=create_search_agent,
            info=AgentInfo(name="search", description="Web search specialist")
        )
        ```
    """

    def __init__(
        self,
        system_agent_factory: SingleAgentFactoryFn | MultiAgentFactoryFn,
        system_agent_info: AgentInfo | None = None,
        secrets_provider: SecretsProvider | None = None,
    ):
        """Initialize the agent factory.

        Args:
            system_agent_factory: Factory function for creating the main system agent.
                Can be either SingleAgentFactoryFn (takes only secrets) or
                MultiAgentFactoryFn (takes secrets, extra_tools, and agent_infos).
            system_agent_info: Optional metadata for the system agent. Defaults to
                a basic AgentInfo with name="system" and 600s idle timeout.
            secrets_provider: Optional provider for user-specific secrets (e.g., API keys).
        """
        self._agent_factory_fns: dict[str, SingleAgentFactoryFn | MultiAgentFactoryFn] = {}
        self._agent_infos: dict[str, AgentInfo] = {}
        self._secrets_provider = secrets_provider

        self._agent_factory_fns["system"] = system_agent_factory
        self._agent_infos["system"] = system_agent_info or AgentInfo(
            name="system",
            description="System agent",
            idle_timeout=600,
        )

    def create_system_agent(self, owner: str, extra_tools: dict[str, AsyncTool]) -> Agent:
        """Create the main system agent for a specific owner.

        Args:
            owner: User ID of the agent owner.
            extra_tools: Additional tools provided by the framework (e.g., run_subagent,
                get_group_chat_messages).

        Returns:
            A new system Agent instance.
        """
        return self.create_agent(name="system", owner=owner, extra_tools=extra_tools)

    def create_agent(self, name: str, owner: str, extra_tools: dict[str, AsyncTool] | None = None) -> Agent:
        """Create an agent by name for a specific owner.

        Looks up the registered factory function for the given name and creates an
        agent instance.

        Args:
            name: Name of the agent to create (must be registered via add_agent_factory_fn
                or be "system").
            owner: User ID of the agent owner.
            extra_tools: Optional additional tools to provide to the agent. Only used
                for MultiAgentFactoryFn agents.

        Returns:
            A new Agent instance configured for the owner.
        """
        secrets = self._get_secrets(owner)
        factory = self._agent_factory_fns[name]
        signature = inspect.signature(factory)

        if len(signature.parameters) == 3:  # MultiAgentFactory
            return factory(secrets, extra_tools, self.agent_infos(exclude=name))  # type: ignore
        else:  # SingleAgentFactory
            return factory(secrets)  # type: ignore

    def add_agent_factory_fn(self, factory_fn: SingleAgentFactoryFn | MultiAgentFactoryFn, info: AgentInfo):
        """Register a new agent factory function.

        Adds a factory function that can create agents of a specific type. The agent
        can then be used as a subagent by coordinator agents.

        Args:
            factory_fn: Factory function for creating the agent. Can be either
                SingleAgentFactoryFn or MultiAgentFactoryFn.
            info: Metadata about the agent (name, description, idle timeout, etc.).
        """
        self._agent_factory_fns[info.name] = factory_fn
        self._agent_infos[info.name] = info

    def system_agent_info(self) -> AgentInfo:
        """Get metadata for the system agent.

        Returns:
            [`AgentInfo`][group_genie.agent.base.AgentInfo] for the system agent.
        """
        return self._agent_infos["system"]

    def agent_info(self, name: str) -> AgentInfo:
        """Get metadata for a specific agent by name.

        Args:
            name: Name of the agent.

        Returns:
            [`AgentInfo`][group_genie.agent.base.AgentInfo] for the specified agent.
        """
        return self._agent_infos[name]

    def agent_infos(self, exclude: str | None = None) -> list[AgentInfo]:
        """Get metadata for all registered agents.

        Args:
            exclude: Optional agent name to exclude from the results (e.g., exclude
                the coordinator agent itself when providing subagent info).

        Returns:
            List of [`AgentInfo`][group_genie.agent.base.AgentInfo] for all
                registered agents except the excluded one.
        """
        return [info for name, info in self._agent_infos.items() if name not in [exclude]]

    def _get_secrets(self, owner: str) -> dict[str, str]:
        if self._secrets_provider is None:
            return {}
        return self._secrets_provider.get_secrets(owner) or {}
