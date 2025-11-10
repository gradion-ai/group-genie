import base64
import json
from collections.abc import AsyncIterator
from contextlib import AsyncExitStack, asynccontextmanager
from contextvars import ContextVar
from dataclasses import replace
from typing import Any

from agents import Agent as AgentImpl
from agents import FunctionTool, Model, ModelSettings, Runner, Tool, TResponseInputItem
from agents.mcp import MCPServer
from pydantic_core import to_jsonable_python

from group_genie.agent.approval import ApprovalCallback
from group_genie.agent.base import Agent, AgentInput
from group_genie.agent.provider.openai.utils import MCPApprovalInterceptor
from group_genie.agent.provider.pydantic_ai.agent.prompt import user_prompt


class DefaultAgent(Agent):
    """Default [`Agent`][group_genie.agent.base.Agent] implementation using the
    [OpenAI Agents SDK](https://openai.github.io/openai-agents-python/).

    DefaultAgent is a ready-to-use Agent implementation built on the OpenAI Agents SDK.
    It supports conversation state management, tool calling with approval workflows,
    and MCP server lifecycle management.

    The agent can be configured with:

    - Custom system prompts (instructions)
    - Any OpenAI Agents SDK compatible model
    - Individual tools (function tools)
    - MCP servers for external integrations

    For model and tool configuration details, consult the
    [OpenAI Agents SDK documentation](https://openai.github.io/openai-agents-python/).

    Example:
        ```python
        from agents import Model, ModelSettings, function_tool

        @function_tool
        def get_weather(city: str) -> str:
            return f"Weather in {city}: sunny"

        agent = DefaultAgent(
            system_prompt="You are a helpful weather assistant",
            model="gpt-4o",
            model_settings=ModelSettings(temperature=0.7),
            tools=[get_weather],
        )
        ```
    """

    def __init__(
        self,
        system_prompt: str,
        model: str | Model,
        model_settings: ModelSettings,
        tools: list[Tool] = [],
        mcp_servers: list[Any] = [],
        **kwargs: Any,
    ):
        """Initialize an OpenAI Agents SDK based agent.

        Args:
            system_prompt: System prompt (instructions) that defines the agent's
                behavior and personality.
            model: Model identifier or OpenAI Agents SDK Model instance. Can be any
                model supported by the OpenAI Agents SDK.
            model_settings: Model-specific settings from the OpenAI Agents SDK. See
                the SDK documentation for available settings per model provider.
            tools: List of individual tools (typically function tools created with
                `@function_tool` decorator from the OpenAI Agents SDK).
            mcp_servers: List of MCP server instances from the OpenAI Agents SDK.
                These will be wrapped with approval interceptors.
            **kwargs: Additional arguments passed to the underlying OpenAI Agent
                constructor.
        """
        super().__init__()
        self.system_prompt = system_prompt
        self.model = model
        self.model_settings = model_settings
        self.kwargs = kwargs

        self._tools_wrapped = [self._wrap_tool(tool) for tool in tools]
        self._mcp_servers: list[MCPServer] = mcp_servers
        self._mcp_servers_wrapped: list[MCPServer] = []

        self._callback: ContextVar[ApprovalCallback] = ContextVar[ApprovalCallback]("callback")
        self._agent: AgentImpl[Any] | None = None
        self._history: list[TResponseInputItem] = []

    def get_serialized(self) -> Any:
        """Serialize agent conversation history for persistence.

        Returns:
            Serialized conversation history as JSON-compatible data structure
                (list of message dictionaries).
        """
        return to_jsonable_python(self._history, bytes_mode="base64")

    def set_serialized(self, state: Any):
        """Restore agent conversation history from serialized data.

        Args:
            state: Previously serialized state from
                [`get_serialized()`][group_genie.agent.provider.openai.DefaultAgent.get_serialized].
        """
        self._history = state

    @asynccontextmanager
    async def mcp(self) -> AsyncIterator["DefaultAgent"]:
        """Manage MCP server lifecycle for this agent.

        Connects to all configured MCP servers and wraps them with approval interceptors.
        Creates the underlying OpenAI Agents SDK agent instance with all tools and
        MCP servers. On exit, disconnects from MCP servers and cleans up the agent.

        Yields:
            This agent instance.
        """
        async with AsyncExitStack() as stack:
            for mcp_server in self._mcp_servers:
                _mcp_server = await stack.enter_async_context(mcp_server)
                self._mcp_servers_wrapped.append(MCPApprovalInterceptor(wrapped=_mcp_server, callback=self._callback))

            self._agent = AgentImpl[Any](
                name="openai-agent",
                instructions=self.system_prompt,
                model=self.model,
                model_settings=self.model_settings,
                mcp_servers=self._mcp_servers_wrapped,
                tools=self._tools_wrapped,
                **self.kwargs,
            )

            yield self

            self._agent = None
            self._mcp_servers_wrapped = []

    async def run(self, input: AgentInput, callback: ApprovalCallback) -> str:
        """Process a query and return a response.

        Runs the OpenAI Agents SDK agent with the provided query, attachments, and
        preferences. Tool call approvals are requested through the approval
        callback, allowing the application to approve or deny tool execution. Image
        attachments are converted to base64-encoded data URLs. User preferences are
        temporarily added to the conversation but removed from the persisted history
        after execution.

        Args:
            input: Query, attachments, and preferences to process. See
                [`AgentInput`][group_genie.agent.base.AgentInput] for details.
            callback: Approval callback for tool calls. Called for each tool execution
                to request approval. See
                [`ApprovalCallback`][group_genie.agent.approval.ApprovalCallback].

        Returns:
            The agent's response as a string.

        Raises:
            ValueError: If an attachment has a non-image media type.
        """
        prompt = []

        for attachment in input.attachments:
            if not attachment.media_type.startswith("image/"):
                raise ValueError(f"Unsupported attachment media type: {attachment.media_type}")

            prompt.append(
                {
                    "type": "input_text",
                    "text": f'Attachment name="{attachment.name}": ',
                }
            )
            prompt.append(
                {
                    "type": "input_image",
                    "image_url": f"data:{attachment.media_type};base64,{base64.b64encode(await attachment.bytes()).decode('utf-8')}",
                }
            )

        for part in user_prompt(input):
            prompt.append(
                {
                    "type": "input_text",
                    "text": part,
                }
            )

        self._callback.set(callback)
        result = await Runner.run(
            self._agent,
            input=self._history
            + [
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
        )

        user_message_idx = len(self._history)
        self._history = result.to_input_list()

        if input.preferences:
            # remove preferences from history
            self._history[user_message_idx]["content"].pop(-2)

        return str(result.final_output)

    def _wrap_tool(self, tool: Tool) -> Tool:
        if not isinstance(tool, FunctionTool):
            return tool

        original_invoke = tool.on_invoke_tool

        async def wrapped_invoke(ctx: Any, args_json: str) -> Any:
            callback = self._callback.get()
            args_dict = json.loads(args_json)
            if await callback(tool_name=tool.name, tool_args=args_dict):  # type: ignore
                return await original_invoke(ctx, args_json)
            else:
                return f"Action denied: {tool.name}({args_dict})"

        return replace(tool, on_invoke_tool=wrapped_invoke)
