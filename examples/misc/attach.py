import asyncio
import logging
from pathlib import Path

from examples.factory.agent_2 import get_agent_factory
from examples.factory.reasoner import get_group_reasoner_factory
from examples.utils import complete_execution
from group_genie.datastore import DataStore
from group_genie.logging import configure_logging
from group_genie.message import Attachment, Message
from group_genie.session import GroupSession
from group_genie.utils import identifier

logger = logging.getLogger(__name__)


async def main():
    session_id = identifier()
    session = GroupSession(
        id=session_id,
        group_reasoner_factory=get_group_reasoner_factory(),
        agent_factory=get_agent_factory(),
        data_store=DataStore(root_path=Path(".data", "attach", session_id)),
    )

    attachment_1 = Attachment(
        path="tests/data/unknown-1.png",
        name="unknown-1.png",
        media_type="image/png",
    )

    message_1 = Message(
        content="Look at this nice image!",
        sender="user2",
        attachments=[attachment_1],
    )

    message_2 = Message(
        content="What is the weather in the city mentioned in the attached image?",
        sender="user1",
    )

    execution_1 = session.handle(message_1)
    execution_2 = session.handle(message_2)

    await asyncio.gather(
        complete_execution(execution_1),
        complete_execution(execution_2),
    )

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
