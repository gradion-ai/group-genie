from typing import Any

import group_sense as gs
from group_sense import Response
from pydantic_ai.models import Model
from pydantic_ai.settings import ModelSettings

from group_genie.message import Attachment, Message, Thread
from group_genie.reasoner import GroupReasoner


class DefaultGroupReasoner(GroupReasoner):
    """Default group reasoner implementation using
    [group-sense](https://gradion-ai.github.io/group-sense/).

    DefaultGroupReasoner wraps the group-sense library's DefaultGroupReasoner,
    adapting Group Genie's Message types to group-sense's message format.

    The reasoner analyzes group chat messages according to the system prompt's
    engagement criteria and decides whether to delegate queries to agents.

    For model and configuration details, consult the group-sense and pydantic-ai
    documentation. Tested with gemini-2.5-flash but compatible with any pydantic-ai
    supported model.

    Example:
        ```python
        reasoner = DefaultGroupReasoner(
            system_prompt='''
                You are monitoring a group chat for {owner}.
                Delegate when {owner} asks questions.
                Generate self-contained queries.
            '''.format(owner="alice"),
            model="gemini-2.5-flash",
        )

        # Process messages
        response = await reasoner.run([
            Message(content="What's the weather?", sender="alice")
        ])

        if response.decision == Decision.DELEGATE:
            print(f"Query: {response.query}")
        ```
    """

    def __init__(
        self,
        system_prompt: str,
        model: str | Model | None = None,
        model_settings: ModelSettings | None = None,
    ):
        """Initialize a group-sense based reasoner.

        Args:
            system_prompt: System prompt defining the engagement criteria. Should
                describe when to delegate messages and how to transform them into
                self-contained queries.
            model: Optional model identifier or pydantic-ai Model instance. Defaults
                to the model configured in group-sense. Can be any model supported
                by pydantic-ai.
            model_settings: Optional model-specific settings. See pydantic-ai
                documentation for available settings per model provider.
        """
        self._reasoner = gs.DefaultGroupReasoner(
            system_prompt=system_prompt,
            model=model,
            model_settings=model_settings,
        )

    @property
    def processed(self) -> int:
        return self._reasoner.processed

    def get_serialized(self) -> dict[str, Any]:
        return self._reasoner.get_serialized()

    def set_serialized(self, state: dict[str, Any]):
        self._reasoner.set_serialized(state)

    async def run(self, updates: list[Message]) -> Response:
        """Analyze message updates and decide whether to delegate.

        Converts Group Genie messages to group-sense format and delegates to the
        underlying group-sense reasoner for processing.

        Args:
            updates: List of new messages to analyze.

        Returns:
            Response from group-sense with decision and optional query/receiver.
        """
        return await self._reasoner.process(convert_messages(updates))


def convert_messages(messages: list[Message]) -> list[gs.Message]:
    return [convert_message(message) for message in messages]


def convert_message(message: Message) -> gs.Message:
    return gs.Message(
        content=message.content,
        sender=message.sender,
        receiver=message.receiver,
        threads=[convert_thread(thread) for thread in message.threads],
        attachments=[convert_attachment(attachment) for attachment in message.attachments],
    )


def convert_attachment(attachment: Attachment) -> gs.Attachment:
    return gs.Attachment(
        path=attachment.path,
        name=attachment.name,
        media_type=attachment.media_type,
    )


def convert_thread(thread: Thread) -> gs.Thread:
    return gs.Thread(
        id=thread.id,
        messages=convert_messages(thread.messages),
    )
