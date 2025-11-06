from asyncio import Future, Queue
from dataclasses import dataclass
from functools import partial
from typing import Any, Awaitable, Callable

ApprovalCallback = Callable[[str, dict[str, Any]], Awaitable[bool]]
"""Callback function type for requesting approval of tool calls.

When called, approval is requested and blocks until the application approves or
denies the request. This callback is typically provided by
[`ApprovalContext.approval_callback()`][group_genie.agent.approval.ApprovalContext.approval_callback]
and passed to [`Agent.run()`][group_genie.agent.base.Agent.run] to enable approval
workflows.

Args:
    tool_name: Name of the tool being called.
    tool_args: Keyword arguments for the tool call.

Returns:
    True if the tool call is approved, False if denied.
"""


@dataclass
class Approval:
    """Represents a tool call awaiting user approval.

    [`Approval`][group_genie.agent.approval.Approval] objects are emitted by
    [`Execution.stream()`][group_genie.session.Execution.stream] when an agent
    attempts to call a tool that requires approval. Applications must approve or
    deny the request by calling [`approve()`][group_genie.agent.approval.Approval.approve]
    or [`deny()`][group_genie.agent.approval.Approval.deny], which unblocks the
    agent execution.

    Attributes:
        sender: Identifier of the agent or subagent requesting approval (e.g.,
            "system", "search:a1b2c3d4").
        tool_name: Name of the tool being called.
        tool_args: Positional arguments for the tool call.
        tool_kwargs: Keyword arguments for the tool call.
        ftr: Internal future for communicating the approval decision.

    Example:
        ```python
        async for elem in execution.stream():
            match elem:
                case Approval() as approval:
                    print(f"Tool call: {approval.call_repr()}")
                    if is_safe(approval.tool_name):
                        approval.approve()
                    else:
                        approval.deny()
        ```
    """

    sender: str

    tool_name: str
    tool_args: tuple
    tool_kwargs: dict[str, Any]
    ftr: Future[bool]

    async def approved(self) -> bool:
        """Wait for and return the approval decision.

        Blocks until approve() or deny() is called, then returns the decision.

        Returns:
            True if approved, False if denied.
        """
        return await self.ftr

    def approve(self):
        """Approve the tool call and unblock agent execution.

        Allows the agent to proceed with the tool execution. The agent will receive
        the tool's result.
        """
        self.ftr.set_result(True)

    def deny(self):
        """Deny the tool call and unblock agent execution.

        Prevents the tool from executing. The agent will receive a denial message
        (implementation-specific behavior).
        """
        self.ftr.set_result(False)

    def __str__(self) -> str:
        actor_str = f'sender="{self.sender}"'
        return f"[{actor_str}] {self.call_repr()}"

    def call_repr(self) -> str:
        """Get a string representation of the tool call."""
        args_str = ", ".join([repr(arg) for arg in self.tool_args])
        kwargs_str = ", ".join([f"{k}={repr(v)}" for k, v in self.tool_kwargs.items()])
        all_args = ", ".join(filter(None, [args_str, kwargs_str]))
        return f"{self.tool_name}({all_args})"


@dataclass
class ApprovalContext:
    """Context for managing the approval workflow.

    [`ApprovalContext`][group_genie.agent.approval.ApprovalContext] coordinates
    approval requests between agents and the application. It manages a queue of
    [`Approval`][group_genie.agent.approval.Approval] objects that are emitted
    through [`Execution.stream()`][group_genie.session.Execution.stream] and
    provides callbacks for agents to request approval.

    When auto_approve is enabled, all tool calls are automatically approved and
    [`Approval`][group_genie.agent.approval.Approval] objects are not emitted
    through the stream.

    Attributes:
        queue: Queue for Approval objects that need user attention.
        auto_approve: If True, automatically approve all tool calls without emitting
            Approvals. Defaults to False.

    Example:
        ```python
        # Auto-approve mode (used by Execution.result())
        context = ApprovalContext(queue=queue, auto_approve=True)

        # Manual approval mode (used by Execution.stream())
        context = ApprovalContext(queue=queue, auto_approve=False)
        ```
    """

    queue: Queue[Approval]
    auto_approve: bool = False

    def approval_callback(self, sender: str) -> ApprovalCallback:
        """Create an approval callback for a specific sender.

        Args:
            sender: Identifier of the agent requesting approval.

        Returns:
            Callback function that can be passed to
                [`Agent.run()`][group_genie.agent.base.Agent.run].
        """
        return partial(self.approval, sender=sender)

    async def approval(self, sender: str, tool_name: str, tool_args: dict[str, Any]) -> bool:
        """Request approval for a tool call.

        If auto_approve is enabled, immediately returns True. Otherwise, creates
        an [`Approval`][group_genie.agent.approval.Approval] object, adds it to
        the queue for the application to handle, and blocks until
        [`approve()`][group_genie.agent.approval.Approval.approve] or
        [`deny()`][group_genie.agent.approval.Approval.deny] is called.

        Args:
            sender: Identifier of the agent requesting approval.
            tool_name: Name of the tool being called.
            tool_args: Arguments for the tool call.

        Returns:
            True if approved, False if denied.
        """
        if self.auto_approve:
            return True

        approval = Approval(
            sender=sender,
            tool_name=tool_name,
            tool_args=(),
            tool_kwargs=tool_args,
            ftr=Future[bool](),
        )
        self.queue.put_nowait(approval)
        return await approval.approved()
