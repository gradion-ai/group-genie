from collections.abc import AsyncIterator
from pathlib import Path

import pytest
import pytest_asyncio

from group_genie.agent import AgentFactory, AgentInput, AgentRunner, Approval
from group_genie.datastore import DataStore


@pytest_asyncio.fixture
async def data_store(tmp_path: Path) -> AsyncIterator[DataStore]:
    async with DataStore(root_path=tmp_path) as ds:
        yield ds


@pytest_asyncio.fixture
async def runner(agent_factory: AgentFactory) -> AsyncIterator[AgentRunner]:
    runner = AgentRunner(
        key="test-runner",
        name="system",
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
        name="system",
        owner="test-user",
        agent_factory=agent_factory,
        data_store=data_store,
    )

    yield runner

    runner.stop()
    await runner.join()
    import asyncio

    await asyncio.sleep(1)


@pytest.mark.asyncio
async def test_runner_run(runner: AgentRunner):
    approvals: list[Approval] = []

    async for elem in runner.run(AgentInput(query="What is the weather in Paris?")):
        match elem:
            case Approval(tool_name=tool_name, tool_kwargs=tool_kwargs, sender=sender) as approval:
                approvals.append(approval)
                approval.approve()

                if tool_name == "get_weather":
                    assert tool_kwargs == {"city": "a"}
                    assert sender == "test-runner"
                elif tool_name == "run_subagent":
                    assert tool_kwargs == {
                        "query": "a",
                        "subagent_name": "a",
                        "subagent_instance": None,
                        "attachments": [],
                    }
                    assert sender == "test-runner"
                elif tool_name == "tool_1":
                    assert tool_kwargs == {"s": "a"}
                    assert sender.startswith("a:")
                elif tool_name == "tool_2":
                    assert tool_kwargs == {"s": "a"}
                    assert sender.startswith("a:")
                else:
                    pytest.fail("Unexpected tool_name: {}".format(tool_name))

            case str() as response:
                assert response == "Test output"
                break

    assert len(approvals) == 4


@pytest.mark.asyncio
async def test_runner_persistence(agent_factory: AgentFactory, data_store: DataStore):
    runner1 = AgentRunner(
        key="test-runner",
        name="system",
        owner="test-user",
        agent_factory=agent_factory,
        data_store=data_store,
    )

    async for elem in runner1.run(AgentInput(query="What is the weather in Paris?")):
        match elem:
            case Approval() as approval:
                approval.approve()
            case str() as content:
                assert content == "Test output"
                break

    # Get the history from the first runner before stopping
    history1 = runner1._agent._history  # type: ignore

    # Stop the runner to ensure it saves
    runner1.stop()
    await runner1.join()

    # Create a new runner with the same store and verify it loads the history
    runner2 = AgentRunner(
        key="test-runner",
        name="system",
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
