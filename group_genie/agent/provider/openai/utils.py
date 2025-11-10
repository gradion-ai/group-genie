from contextvars import ContextVar
from typing import Any

from agents.mcp import MCPServer
from mcp.types import CallToolResult, TextContent

from group_genie.agent.approval import ApprovalCallback


class MCPApprovalInterceptor(MCPServer):
    """MCP server wrapper that intercepts tool calls for approval.

    Wraps an OpenAI Agents SDK MCPServer to add approval workflow for all tool
    calls. When the LLM attempts to call an MCP tool, the interceptor:

    1. Retrieves the approval callback from the context variable
    2. Calls the callback with the tool name and arguments
    3. If approved, executes the original MCP tool
    4. If denied, returns a denial message without executing the tool

    This enables consistent approval workflows across all MCP tools used by
    an agent.

    Attributes:
        _wrapped: The underlying MCP server being wrapped.
        _callback: Context variable containing the approval callback for the
            current agent run.

    Example:
        ```python
        from agents.mcp import MCPServer
        from contextvars import ContextVar

        mcp_server = MCPServer(...)
        callback_var = ContextVar("callback")
        interceptor = MCPApprovalInterceptor(
            wrapped=mcp_server,
            callback=callback_var
        )
        ```
    """

    def __init__(self, wrapped: MCPServer, callback: ContextVar[ApprovalCallback]):
        super().__init__(use_structured_content=wrapped.use_structured_content)
        self._wrapped = wrapped
        self._callback = callback

    @property
    def name(self) -> str:
        return self._wrapped.name

    async def connect(self):
        await self._wrapped.connect()

    async def cleanup(self):
        await self._wrapped.cleanup()

    async def list_tools(self, run_context: Any | None = None, agent: Any | None = None) -> list[Any]:
        return await self._wrapped.list_tools(run_context, agent)

    async def call_tool(self, tool_name: str, arguments: dict[str, Any] | None) -> CallToolResult:
        """Intercept MCP tool call and request approval.

        Calls the approval callback to check if the tool execution should proceed.
        If approved, delegates to the wrapped MCP server's call_tool method.
        If denied, returns a text result indicating the action was denied.

        Args:
            tool_name: Name of the MCP tool being called.
            arguments: Arguments for the tool call, or None if no arguments.

        Returns:
            CallToolResult containing either the tool's output (if approved) or
                a denial message (if denied).
        """
        callback = self._callback.get()
        if await callback(tool_name=tool_name, tool_args=arguments):  # type: ignore
            return await self._wrapped.call_tool(tool_name, arguments)
        else:
            text = f"Action denied: {tool_name}({arguments})"
            return CallToolResult(content=[TextContent(type="text", text=text)], isError=False)

    async def list_prompts(self) -> Any:
        return await self._wrapped.list_prompts()

    async def get_prompt(self, name: str, arguments: dict[str, Any] | None = None) -> Any:
        return await self._wrapped.get_prompt(name, arguments)
