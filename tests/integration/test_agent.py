import json
from asyncio import Queue, create_task

import pytest

from group_genie.agent import Agent, AgentFactory, AgentInput, ApprovalContext
from tests.integration.conftest import approve


@pytest.fixture
def agent(agent_factory: AgentFactory) -> Agent:
    return agent_factory.create_agent(name="test", owner="")


@pytest.mark.asyncio
async def test_agent_run_with_auto_approve_true(agent: Agent):
    context = ApprovalContext(queue=Queue(), auto_approve=True)

    async with agent.mcp():
        result = await agent.run(
            input=AgentInput(
                query="What is the weather in Paris?",
                attachments=[],
            ),
            callback=context.approval_callback(sender="test-agent"),
        )

    parsed = json.loads(result)

    assert "get_weather" in parsed
    assert "sunny" in parsed["get_weather"]
    assert "20°C" in parsed["get_weather"]

    assert "tool_1" in parsed
    assert "You passed to tool 1:" in parsed["tool_1"]

    assert "tool_2" in parsed
    assert "You passed to tool 2:" in parsed["tool_2"]


@pytest.mark.asyncio
async def test_agent_run_with_auto_approve_false(agent: Agent):
    context = ApprovalContext(queue=Queue(), auto_approve=False)

    async with agent.mcp():
        approval_task = create_task(approve(3, context.queue))
        result = await agent.run(
            input=AgentInput(
                query="What is the weather in Paris?",
                attachments=[],
            ),
            callback=context.approval_callback(sender="test-agent"),
        )
        approvals = await approval_task

    parsed = json.loads(result)

    assert "get_weather" in parsed
    assert "sunny" in parsed["get_weather"]

    assert "tool_1" in parsed
    assert "You passed to tool 1:" in parsed["tool_1"]

    assert "tool_2" in parsed
    assert "You passed to tool 2:" in parsed["tool_2"]

    for approval in approvals:
        assert approval.sender == "test-agent"
        assert approval.tool_name in {"get_weather", "tool_1", "tool_2"}
