from contextvars import ContextVar
from dataclasses import dataclass
from typing import Any

from pydantic_ai.tools import ToolDefinition
from pydantic_ai.toolsets import WrapperToolset

from group_genie.agent.base import ApprovalCallback


@dataclass
class ToolFilter:
    """Filter function for selectively exposing tools to agents based on whitelists and blacklists.

    This class is designed to be passed to pydantic-ai's `FilteredToolset` or the
    `filtered()` method on any toolset. It implements a callable filter that receives
    the run context and tool definition for each tool and returns whether the tool
    should be available.

    The filter operates as follows:
    - If `included` is specified, only tools in the whitelist are allowed
    - If `excluded` is specified, tools in the blacklist are rejected
    - If both are specified, a tool must be in `included` and not in `excluded`
    - If neither is specified, all tools are allowed

    Example:
       ```python
        filter = ToolFilter(included=["read_file", "write_file"])
        filtered_toolset = my_toolset.filtered(filter)
       ```

    Attributes:
        included: Optional whitelist of tool names. If provided, only tools with names
            in this list will be allowed through the filter.
        excluded: Optional blacklist of tool names. If provided, tools with names in
            this list will be rejected by the filter.
    """

    included: list[str] | None = None
    excluded: list[str] | None = None

    def __call__(self, ctx, tool_def: ToolDefinition) -> bool:
        if self.included is not None and tool_def.name not in self.included:
            return False

        if self.excluded is not None and tool_def.name in self.excluded:
            return False

        return True


@dataclass
class ApprovalInterceptor(WrapperToolset):
    callback: ContextVar[ApprovalCallback] = ContextVar("callback")

    async def call_tool(self, name: str, tool_args: dict[str, Any], ctx, tool) -> Any:
        callback = self.callback.get()
        if not await callback(tool_name=name, tool_args=tool_args):  # type: ignore
            return f"Action denied: {name}({tool_args})"
        return await self.wrapped.call_tool(name, tool_args, ctx, tool)
