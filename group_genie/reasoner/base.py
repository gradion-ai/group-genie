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

    State persistence is managed automatically by the framework and stored in JSON
    format. Persisted state is never transferred between different owners (users).

    Example:
        ```python
        class MyGroupReasoner(GroupReasoner):
            def __init__(self, system_prompt: str):
                self._history = []
                self._processed = 0
                self._system_prompt = system_prompt

            @property
            def processed(self) -> int:
                return self._processed

            def get_serialized(self):
                return {"history": self._history, "processed": self._processed}

            def set_serialized(self, state):
                self._history = state["history"]
                self._processed = state["processed"]

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
    def get_serialized(self) -> Any:
        """Serialize reasoner state for persistence.

        Returns conversation history and any other state needed to resume the reasoner
        after a restart. Called automatically by the framework before saving to
        [`DataStore`][group_genie.datastore.DataStore].

        Returns:
            Serializable state (must be JSON-compatible). Implementation-specific format.
        """
        ...

    @abstractmethod
    def set_serialized(self, serialized: Any):
        """Restore reasoner state from serialized data.

        Reconstructs conversation history and internal state from previously serialized
        data. Called automatically by the framework after loading from
        [`DataStore`][group_genie.datastore.DataStore].

        Args:
            serialized: Previously serialized state from
                [`get_serialized()`][group_genie.reasoner.base.GroupReasoner.get_serialized].
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
