from collections.abc import AsyncIterator

import pytest
import pytest_asyncio

from group_genie.agent import AgentFactory, Approval
from group_genie.message import Message
from group_genie.reasoner import GroupReasonerFactory
from group_genie.session import GroupSession


@pytest_asyncio.fixture
async def session(
    agent_factory: AgentFactory,
    group_reasoner_factory: GroupReasonerFactory,
) -> AsyncIterator[GroupSession]:
    session = GroupSession(
        id="test-session",
        group_reasoner_factory=group_reasoner_factory,
        agent_factory=agent_factory,
    )

    yield session

    session.stop()
    await session.join()


@pytest.mark.asyncio
async def test_session_handle(session: GroupSession):
    message = Message(
        content="What is the weather in Paris?",
        sender="user",
        receiver="",
        request_id="123",
    )

    approvals: list[Approval] = []
    execution = session.handle(message)

    async for elem in execution.stream():
        match elem:
            case Approval(tool_name=tool_name, tool_kwargs=tool_kwargs, sender=sender) as approval:
                approvals.append(approval)
                approval.approve()

                if tool_name == "get_weather":
                    assert tool_kwargs == {"city": "a"}
                    assert sender == "system"
                elif tool_name == "run_subagent":
                    assert tool_kwargs["subagent_name"] == "a"
                    assert tool_kwargs["subagent_instance"] is None
                    assert tool_kwargs["attachments"] == []
                    assert sender == "system"
                elif tool_name == "tool_1":
                    assert tool_kwargs == {"s": "a"}
                    assert sender.startswith("a:")
                elif tool_name == "tool_2":
                    assert tool_kwargs == {"s": "a"}
                    assert sender.startswith("a:")
                else:
                    pytest.fail("Unexpected tool_name: {}".format(tool_name))

            case Message() as response:
                assert response.sender == "system"
                assert response.receiver == "dynamic"
                assert response.request_id == "123"
                assert response.content == "Test output"
                break

    assert len(approvals) == 4
