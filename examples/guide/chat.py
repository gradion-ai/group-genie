import argparse
import logging
import re
from asyncio import create_task, run
from pathlib import Path

from dotenv import load_dotenv
from group_terminal.server import ChatServer

from examples.factory.pydantic_ai.agent_factory_2 import get_agent_factory
from examples.factory.pydantic_ai.reasoner_factory import get_group_reasoner_factory
from examples.factory.secrets import EnvironmentSecretsProvider
from group_genie.agent import AgentFactory, Approval, Decision
from group_genie.datastore import DataStore
from group_genie.logging import configure_logging
from group_genie.message import Message
from group_genie.reasoner import GroupReasonerFactory
from group_genie.session import Execution, GroupSession
from group_genie.utils import identifier

logger = logging.getLogger(__name__)


class App:
    def __init__(
        self,
        group_reasoner_factory: GroupReasonerFactory,
        agent_factory: AgentFactory,
        session_id: str | None = None,
        host: str = "0.0.0.0",
        port: int = 8723,
    ):
        self._session_id = session_id or identifier()
        self._data_store = DataStore(root_path=Path(".data", "chat"))
        self._session = GroupSession(
            id=self._session_id,
            group_reasoner_factory=group_reasoner_factory,
            agent_factory=agent_factory,
            data_store=self._data_store,
        )

        self._server = ChatServer(host=host, port=port)
        self._server.add_handler(self._handle_message)

    @property
    def session(self):
        return self._session

    @property
    def server(self):
        return self._server

    async def _handle_message(self, content: str, sender: str):
        message = self._create_message(content, sender)
        # Add messages to session in message arrival order
        execution = self._session.handle(message)
        # Asynchronously complete execution
        create_task(self._complete_execution(execution))

    async def _complete_execution(self, execution: Execution):
        async for elem in execution.stream():
            match elem:
                case Decision() as decision:
                    logger.debug(f"Reasoner decision: {decision.value}")
                case Approval() as approval:
                    logger.debug(f"Auto-approve {approval}")
                    elem.approve()
                case Message() as message:
                    logger.debug(f"Agent response: {message.content}")
                    await self._server.send_message(message.content, sender=message.sender)

    def _create_message(self, content: str, sender: str) -> Message:
        if match := re.match(r"^@(\S+)\s*(.*)", content):
            # content started with an @mention, which is extracted and set as receiver
            return Message(content=match.group(2), sender=sender, receiver=match.group(1))
        return Message(content=content, sender=sender, receiver=None)


async def main(args):
    secrets_provider = EnvironmentSecretsProvider()
    app = App(
        group_reasoner_factory=get_group_reasoner_factory(
            secrets_provider=secrets_provider,
            template_name=args.template_name,
        ),
        agent_factory=get_agent_factory(secrets_provider=secrets_provider),
        session_id=args.session_id,
        host=args.host,
        port=args.port,
    )

    await app.server.start()
    await app.server.join()


if __name__ == "__main__":
    load_dotenv()

    parser = argparse.ArgumentParser()
    parser.add_argument("--session-id", type=str, default=None)
    parser.add_argument("--host", type=str, default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8723)
    parser.add_argument("--template-name", type=str, default="general_assist")

    with configure_logging(
        levels={
            __name__: logging.DEBUG,
            "group_genie": logging.DEBUG,
            "group_sense": logging.DEBUG,
        }
    ):
        run(main(args=parser.parse_args()))
