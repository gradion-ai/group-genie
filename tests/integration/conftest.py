from asyncio import Queue
from pathlib import Path
from typing import Any, AsyncIterator

import pytest
import pytest_asyncio
from group_sense import Decision, Response
from pydantic_ai.mcp import MCPServerStdio
from pydantic_ai.models.test import TestModel

from group_genie.agent import AgentFactory, AgentInfo, Approval, AsyncTool
from group_genie.agent.provider.pydantic_ai import DefaultAgent
from group_genie.datastore import DataStore
from group_genie.message import Message
from group_genie.reasoner import GroupReasoner, GroupReasonerFactory
from tests.integration.mcp.server import STDIO_SERVER_PATH


async def approve(expected: int, queue: Queue) -> list[Approval]:
    approvals: list[Approval] = []
    while len(approvals) < expected:
        match await queue.get():
            case Approval() as approval:
                approvals.append(approval)
                approval.approve()
    return approvals


@pytest_asyncio.fixture
async def data_store(tmp_path: Path) -> AsyncIterator[DataStore]:
    async with DataStore(root_path=tmp_path) as ds:
        yield ds


@pytest.fixture
def group_reasoner_factory() -> GroupReasonerFactory:
    def create_group_reasoner(secrets: dict[str, str], owner: str):
        return MockGroupReasoner()

    return GroupReasonerFactory(
        group_reasoner_factory_fn=create_group_reasoner,
    )


@pytest.fixture
def agent_factory() -> AgentFactory:
    mcp_server = MCPServerStdio(
        command="python",
        args=[str(STDIO_SERVER_PATH)],
    )

    def create_system_agent(
        secrets: dict[str, str],
        extra_tools: dict[str, AsyncTool],
        subagent_infos: list[AgentInfo],
    ):
        return DefaultAgent(
            system_prompt="",
            model=TestModel(custom_output_text="Test output"),
            tools=[extra_tools["run_subagent"], get_weather],
        )

    def create_agent_1(secrets: dict[str, str]):
        return DefaultAgent(
            system_prompt="You are a helpful assistant.",
            model="test",
            toolsets=[mcp_server],
        )

    def create_agent_2(secrets: dict[str, str]):
        return DefaultAgent(
            system_prompt="You are a helpful assistant.",
            model="test",
            toolsets=[mcp_server],
            tools=[get_weather],
        )

    registry = AgentFactory(
        system_agent_factory=create_system_agent,
    )

    registry.add_agent_factory_fn(
        factory_fn=create_agent_1,
        info=AgentInfo(name="a", description="A test subagent"),
    )

    registry.add_agent_factory_fn(
        factory_fn=create_agent_2,
        info=AgentInfo(name="test", description="A test agent"),
    )

    return registry


class MockGroupReasoner(GroupReasoner):
    @property
    def processed(self) -> int:
        return 0

    def get_serialized(self) -> Any:
        return {}

    def set_serialized(self, state: Any):
        pass

    async def run(self, updates: list[Message]) -> Response:
        return Response(
            decision=Decision.DELEGATE,
            query="Test query",
            receiver="dynamic",
        )


async def get_weather(city: str) -> str:
    return f"The weather in {city} is sunny at 20°C."
