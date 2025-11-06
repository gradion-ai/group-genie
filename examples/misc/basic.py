import asyncio
import logging
from pathlib import Path

from examples.factory.agent_1 import get_agent_factory
from examples.factory.reasoner import get_group_reasoner_factory
from examples.utils import complete_execution
from group_genie.datastore import DataStore
from group_genie.logging import configure_logging
from group_genie.message import Message
from group_genie.session import GroupSession
from group_genie.utils import identifier

logger = logging.getLogger(__name__)


async def main():
    session_id = identifier()
    session = GroupSession(
        id=session_id,
        group_reasoner_factory=get_group_reasoner_factory(),
        agent_factory=get_agent_factory(),
        data_store=DataStore(root_path=Path(".data", "basic", session_id)),
    )

    execution = session.handle(Message(content="what is the weather like in Vienna today?", sender="user1"))
    await complete_execution(execution)

    session.stop()
    await session.join()


if __name__ == "__main__":
    with configure_logging(
        levels={
            "examples": logging.DEBUG,
            "group_sense": logging.DEBUG,
            "group_genie": logging.DEBUG,
        }
    ):
        asyncio.run(main())
