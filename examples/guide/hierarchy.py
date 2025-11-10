import asyncio
import logging
from pathlib import Path

from examples.factory.pydantic_ai.agent_factory_1 import get_agent_factory
from examples.factory.pydantic_ai.reasoner_factory import get_group_reasoner_factory
from examples.factory.secrets import EnvironmentSecretsProvider
from examples.utils import complete_execution
from group_genie.datastore import DataStore
from group_genie.logging import configure_logging
from group_genie.message import Message
from group_genie.session import GroupSession
from group_genie.utils import identifier

logger = logging.getLogger(__name__)


async def main():
    secrets_provider = EnvironmentSecretsProvider()
    session_id = identifier()
    session = GroupSession(
        id=session_id,
        group_reasoner_factory=get_group_reasoner_factory(
            secrets_provider=secrets_provider,
            template_name="general_assist",
        ),
        agent_factory=get_agent_factory(secrets_provider=secrets_provider),
        data_store=DataStore(root_path=Path(".data", "hierarchy")),
    )

    message = Message(
        content="what is the current population of Graz, Austria raised to the power of 0.13?",
        sender="user1",
    )

    # Uses the system agent as coordinator for subagents "search" and "math".
    execution = session.handle(message)
    await complete_execution(execution)
    # Output should be something like this:
    # 2025-11-10 07:16:25,116 DEBUG examples.utils: Decision.DELEGATE
    # 2025-11-10 07:16:26,959 DEBUG examples.utils: [sender="system"] run_subagent(query='current population of Graz Austria', subagent_name='search', subagent_instance=None, attachments=[])
    # Note: the search subagent uses the builtin web search tool provided by the Gemini API, hence no tool call is logged.
    # 2025-11-10 07:16:31,771 DEBUG examples.utils: [sender="system"] run_subagent(query='306068^0.13', subagent_name='math', subagent_instance=None, attachments=[])
    # 2025-11-10 07:16:32,587 DEBUG examples.utils: [sender="math:d330a02c"] execute_ipython_cell(code='print(306068**0.13)')
    # 2025-11-10 07:16:38,324 DEBUG examples.utils: Message(content='The current population of Graz, Austria (projected to be 306,068 as of January 1, 2025), raised to the power of 0.13 is approximately 5.166.', sender='system', receiver='user1', threads=[], attachments=[], request_id=None)

    session.stop()
    await session.join()


if __name__ == "__main__":
    with configure_logging(
        levels={
            "examples": logging.DEBUG,
            "group_sense": logging.INFO,
            "group_genie": logging.INFO,
        }
    ):
        asyncio.run(main())
