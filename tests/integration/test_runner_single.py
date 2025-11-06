import json
from asyncio import Queue, create_task
from collections.abc import AsyncIterator

import pytest
import pytest_asyncio

from group_genie.agent import AgentFactory, AgentInput, AgentRunner, ApprovalContext
from group_genie.datastore import DataStore
from tests.integration.conftest import approve


@pytest_asyncio.fixture
async def runner(agent_factory: AgentFactory) -> AsyncIterator[AgentRunner]:
    runner = AgentRunner(
        key="test-runner",
        name="test",
        owner="test-user",
        agent_factory=agent_factory,
    )

    yield runner

    runner.stop()
    await runner.join()


@pytest_asyncio.fixture
async def runner_with_store(agent_factory: AgentFactory, data_store: DataStore) -> AsyncIterator[AgentRunner]:
    runner = AgentRunner(
        key="test-runner",
        name="test",
        owner="test-user",
        agent_factory=agent_factory,
        data_store=data_store,
    )

    yield runner

    runner.stop()
    await runner.join()


@pytest.mark.asyncio
async def test_runner_invoke_with_auto_approve_true(runner: AgentRunner):
    context = ApprovalContext(queue=Queue(), auto_approve=True)

    future = runner.invoke(input=AgentInput(query="What is the weather in Paris?"), context=context)
    result = await future

    parsed = json.loads(result)

    assert "get_weather" in parsed
    assert "sunny" in parsed["get_weather"]
    assert "20°C" in parsed["get_weather"]

    assert "tool_1" in parsed
    assert "You passed to tool 1:" in parsed["tool_1"]

    assert "tool_2" in parsed
    assert "You passed to tool 2:" in parsed["tool_2"]


@pytest.mark.asyncio
async def test_runner_invoke_with_auto_approve_false(runner: AgentRunner):
    context = ApprovalContext(queue=Queue(), auto_approve=False)

    approval_task = create_task(approve(3, context.queue))
    future = runner.invoke(input=AgentInput(query="What is the weather in Paris?"), context=context)

    result = await future
    approvals = await approval_task

    parsed = json.loads(result)

    assert "get_weather" in parsed
    assert "sunny" in parsed["get_weather"]
    assert "20°C" in parsed["get_weather"]

    assert "tool_1" in parsed
    assert "You passed to tool 1:" in parsed["tool_1"]

    assert "tool_2" in parsed
    assert "You passed to tool 2:" in parsed["tool_2"]

    for approval in approvals:
        assert approval.sender == "test-runner"
        assert approval.tool_name in {"get_weather", "tool_1", "tool_2"}


@pytest.mark.asyncio
async def test_runner_persistence(agent_factory: AgentFactory, data_store: DataStore):
    context = ApprovalContext(queue=Queue(), auto_approve=True)

    # Create first runner and invoke it
    runner1 = AgentRunner(
        key="test-runner",
        name="test",
        owner="test-user",
        agent_factory=agent_factory,
        data_store=data_store,
    )
    future = runner1.invoke(input=AgentInput(query="What is the weather in Paris?"), context=context)
    await future

    # Get the history from the first runner before stopping
    history1 = runner1._agent._history  # type: ignore

    # Stop the runner to ensure it saves
    runner1.stop()
    await runner1.join()

    # Create a new runner with the same store and key and verify it loads the history
    runner2 = AgentRunner(
        key="test-runner",
        name="test",
        owner="test-user",
        agent_factory=agent_factory,
        data_store=data_store,
    )

    # Stop and join to ensure the history is loaded
    runner2.stop()
    await runner2.join()

    # The new runner should have the same history as the previous one
    history2 = runner2._agent._history  # type: ignore

    assert len(history1) > 0
    assert len(history2) == len(history1)
    assert history2 == history1
