from contextlib import asynccontextmanager
from contextvars import ContextVar

from pydantic_ai import Agent as AgentImpl
from pydantic_ai.builtin_tools import AbstractBuiltinTool
from pydantic_ai.messages import BinaryContent
from pydantic_ai.models import Model
from pydantic_ai.settings import ModelSettings
from pydantic_ai.toolsets import AbstractToolset, CombinedToolset, FunctionToolset

from group_genie.agent.base import Agent, AgentInput, ApprovalCallback
from group_genie.agent.factory import AsyncTool
from group_genie.agent.provider.pydantic_ai.agent.prompt import user_prompt
from group_genie.agent.provider.pydantic_ai.base import Stateful
from group_genie.agent.provider.pydantic_ai.utils import ApprovalInterceptor


class DefaultAgent(Stateful, Agent):
    """Default `Agent` implementation using [pydantic-ai](https://ai.pydantic.dev/).

    DefaultAgent is a ready-to-use Agent implementation built on pydantic-ai. It
    supports conversation state management, tool calling with approval workflows,
    and MCP server lifecycle management.

    The agent can be configured with:

    - Custom system prompts
    - Any pydantic-ai compatible model
    - Toolsets (collections of tools, including MCP servers)
    - Individual tools (async functions)
    - Built-in tools (like `WebSearchTool`)

    For model and tool configuration details, consult the pydantic-ai documentation.

    Example:
        ```python
        from pydantic_ai.builtin_tools import WebSearchTool
        from pydantic_ai.models.google import GoogleModelSettings

        agent = DefaultAgent(
            system_prompt="You are a helpful assistant",
            model="google-gla:gemini-3-flash-preview",
            model_settings=GoogleModelSettings(
                google_thinking_config={
                    "thinking_level": "high",
                    "include_thoughts": True,
                }
            ),
            builtin_tools=[WebSearchTool()],
        )
        ```
    """

    def __init__(
        self,
        system_prompt: str,
        model: str | Model,
        model_settings: ModelSettings | None = None,
        toolsets: list[AbstractToolset] = [],
        tools: list[AsyncTool] = [],
        builtin_tools: list[AbstractBuiltinTool] = [],
    ):
        """Initialize a pydantic-ai based agent.

        Args:
            system_prompt: System prompt that defines the agent's behavior and personality.
            model: Model identifier or pydantic-ai Model instance. Can be any model
                supported by pydantic-ai.
            model_settings: Optional model-specific settings. See pydantic-ai documentation
                for available settings per model provider.
            toolsets: List of tool collections (including MCP servers). Use this for
                organized sets of related tools.
            tools: List of individual async functions to make available as tools.
            builtin_tools: List of pydantic-ai built-in tools (e.g., WebSearchTool).
        """
        super().__init__()

        function_toolset = FunctionToolset(tools=tools)
        combined_toolset = CombinedToolset(toolsets=[*toolsets, function_toolset])

        self._interceptor = ApprovalInterceptor(
            wrapped=combined_toolset,
            callback=ContextVar("callback"),
        )
        self._agent: AgentImpl[None, str] = AgentImpl(
            system_prompt=system_prompt,
            model=model,
            model_settings=model_settings,
            toolsets=[self._interceptor],
            builtin_tools=builtin_tools,
            output_type=str,
        )

    @asynccontextmanager
    async def mcp(self):
        """Manage MCP server lifecycle for this agent.

        Delegates MCP server management to the underlying pydantic-ai agent,
        which handles connection and cleanup of any MCP servers included in toolsets.

        Yields:
            This agent instance.
        """
        async with self._agent:
            yield self

    async def run(self, input: AgentInput, callback: ApprovalCallback) -> str:
        """Process a query and return a response.

        Runs the pydantic-ai agent with the provided query, attachments, and preferences.
        Tool calls are intercepted and routed through the approval callback, allowing
        the application to approve or deny tool execution.

        Args:
            input: Query, attachments, and preferences to process.
            callback: Approval callback for tool calls. Called for each tool execution
                to request approval.

        Returns:
            The agent's response as a string.
        """
        prompt = []

        for attachment in input.attachments:
            prompt.append(f'Attachment name="{attachment.name}": ')
            prompt.append(
                BinaryContent(
                    data=await attachment.bytes(),
                    media_type=attachment.media_type,
                )
            )

        prompt.extend(user_prompt(input))

        self._interceptor.callback.set(callback)
        result = await self._agent.run(prompt, message_history=self._history)

        if input.preferences:
            # remove user preferences from list returned by formatter
            # (places preferences prior to last position in prompt)
            new_messages = result.new_messages()
            new_messages[0].parts[-1].content.pop(-2)

        self._history = result.all_messages()
        return result.output
