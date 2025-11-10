# --8<-- [start:imports]
import asyncio
import logging
from pathlib import Path
from uuid import uuid4

from examples.factory.pydantic_ai.agent_factory_1 import get_agent_factory
from examples.factory.pydantic_ai.reasoner_factory import get_group_reasoner_factory
from examples.factory.secrets import EnvironmentSecretsProvider
from group_genie.agent import Approval, Decision
from group_genie.datastore import DataStore
from group_genie.message import Message
from group_genie.session import Execution, GroupSession

# --8<-- [end:imports]

logger = logging.getLogger(__name__)


async def main():
    # --8<-- [start:main]
    secrets_provider = EnvironmentSecretsProvider()
    session_id = uuid4().hex[:8]
    session = GroupSession(
        id=session_id,
        group_reasoner_factory=get_group_reasoner_factory(
            secrets_provider=secrets_provider,
            template_name="fact_check",
        ),
        agent_factory=get_agent_factory(secrets_provider=secrets_provider),
        data_store=DataStore(root_path=Path(".data", "tutorial")),
    )

    chat = [  # example group chat messages
        # no factual inconsistency, group reasoner will ignore the message.
        Message(content="I'm going to Vienna tomorrow", sender="user1"),
        # no factual inconsistency, group reasoner will ignore the message.
        Message(content="Enjoy your time there!", sender="user2"),
        # factual inconsistency in response to user1's message.
        # Group reasoner will delegate to system agent for fact checking.
        Message(content="Cool, plan a visit to the Hofbräuhaus!", sender="user3"),
    ]

    # Add chat messages to session and create execution objects
    executions = [session.handle(msg) for msg in chat]

    # Concurrently process group chat messages. The complete_execution()
    # helper logs reasoner decisions and agent responses to the console.
    coros = [complete_execution(exec) for exec in executions]
    await asyncio.gather(*coros)
    # --8<-- [end:main]

    session.stop()
    await session.join()


# --8<-- [start:complete-execution]
async def complete_execution(execution: Execution) -> None:
    async for elem in execution.stream():
        match elem:
            case Decision():
                # log group reasoner decision
                logger.debug(elem)
            case Approval():
                # log tool call approval request
                logger.debug(elem)
                # approve tool call
                elem.approve()
            case Message():
                # log agent response
                logger.debug(elem)


# --8<-- [end:complete-execution]

if __name__ == "__main__":
    from group_genie.logging import configure_logging

    with configure_logging(
        levels={
            "__main__": logging.DEBUG,
            "group_sense": logging.INFO,
            "group_genie": logging.INFO,
        }
    ):
        asyncio.run(main())
