import logging
from pathlib import Path

from group_sense import Decision

from group_genie.agent import Approval
from group_genie.message import Message
from group_genie.session import Execution

logger = logging.getLogger(__name__)


def load_reasoner_template(name: str) -> str:
    path = Path(__file__).parent / "prompts" / "reasoner" / f"{name}.md"
    return path.read_text()


async def complete_execution(execution: Execution) -> None:
    async for elem in execution.stream():
        match elem:
            case Decision():
                logger.debug(elem)
            case Approval():
                logger.debug(elem)
                elem.approve()
            case Message():
                logger.debug(elem)
