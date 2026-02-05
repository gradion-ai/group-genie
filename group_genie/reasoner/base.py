import logging
from abc import ABC, abstractmethod
from typing import Any

from group_sense import Response

from group_genie.message import Message

logger = logging.getLogger(__name__)


class GroupReasoner(ABC):
    """Abstract base class for group reasoning logic.

    Group reasoners analyze incoming group chat messages and decide whether to ignore
    them or generate a query for downstream agents. They maintain conversation
    history across update messages supplied via
    [`run()`][group_genie.reasoner.base.GroupReasoner.run] calls.

    State persistence is managed automatically by the framework using JSONL format
    (one JSON object per line). Persisted state is never transferred between
    different owners (users).

    Example:
        ```python
        class MyGroupReasoner(GroupReasoner):
            def __init__(self, system_prompt: str):
                self._history = []
                self._processed = 0
                self._new_messages = []
                self._system_prompt = system_prompt

            @property
            def processed(self) -> int:
                return self._processed

            def get_new_messages(self):
                return self._new_messages

            def set_serialized(self, lines):
                for line in lines:
                    self._history.extend(line["messages"])
                    self._processed = line["processed"]
                self._new_messages = []

            async def run(self, updates: list[Message]) -> Response:
                # Analyze messages and decide
                self._processed += len(updates)
                return Response(decision=Decision.DELEGATE, query="...")
        ```
    """

    @property
    @abstractmethod
    def processed(self) -> int:
        """Number of messages processed so far by this reasoner.

        Used for tracking conversation history and providing context to the reasoner.
        """
        ...

    @abstractmethod
    def get_new_messages(self) -> list[Any]:
        """Return new data since last save for appending.

        Returns the new data generated during the most recent
        [`run()`][group_genie.reasoner.base.GroupReasoner.run] call. Called
        automatically by the framework after each run to persist incremental state.

        Returns:
            List of JSON-serializable objects to append to storage.
        """
        ...

    @abstractmethod
    def set_serialized(self, lines: list[Any]):
        """Reconstruct reasoner state from all JSONL lines.

        Rebuilds conversation history and internal state from all previously stored
        lines. Called automatically by the framework when loading from
        [`DataStore`][group_genie.datastore.DataStore].

        Args:
            lines: All previously stored lines from the JSONL file.
        """
        ...

    @abstractmethod
    async def run(self, updates: list[Message]) -> Response:
        """Analyze message updates and decide whether to delegate.

        Processes new group messages in the context of the entire conversation history
        and decides whether to ignore them or generate a query for agent processing.

        Args:
            updates: List of new messages to process. Must not be empty. Represents
                messages that arrived since the last
                [`run()`][group_genie.reasoner.base.GroupReasoner.run] call.

        Returns:
            Response from group-sense containing the decision (IGNORE or DELEGATE)
                and optional delegation parameters (query and receiver).
        """
        ...
