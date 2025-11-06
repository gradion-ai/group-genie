from dataclasses import dataclass, field
from typing import Any

import aiofiles


@dataclass
class Attachment:
    """Metadata for files attached to group chat messages.

    Attachments represent files (images, documents, etc.) that accompany messages.
    They reference local filesystem paths and provide metadata for agents to
    understand and process the files.

    The file at the specified path must exist when
    [`bytes`][group_genie.message.Attachment.bytes] is called, otherwise an error
    is raised and the agent run fails.

    Attributes:
        path: Local filesystem path to the attachment file.
        name: Display name of the attachment.
        media_type: MIME type of the attachment (e.g., 'image/png', 'application/pdf').

    Example:
        ```python
        attachment = Attachment(
            path="/tmp/report.pdf",
            name="Monthly Report",
            media_type="application/pdf"
        )

        message = Message(
            content="Please review this report",
            sender="alice",
            attachments=[attachment]
        )
        ```
    """

    path: str
    """Local file path to the attachment."""

    name: str
    """Name of the attachment."""

    media_type: str
    """MIME type of the attachment."""

    async def bytes(self) -> bytes:
        """Read the attachment file contents.

        Returns:
            The raw bytes of the attachment file.

        Raises:
            FileNotFoundError: If the file at path does not exist.
        """
        async with aiofiles.open(self.path, "rb") as f:
            return await f.read()

    @staticmethod
    def deserialize(attachment_dict: dict[str, Any]) -> "Attachment":
        """Reconstruct an Attachment from a dictionary.

        Args:
            attachment_dict: Dictionary containing attachment data, typically obtained
                from calling asdict() on an Attachment instance.

        Returns:
            An Attachment instance.
        """
        return Attachment(**attachment_dict)


@dataclass
class Thread:
    """Reference to a conversation thread from another group chat.

    Threads allow messages to include context from other group conversations,
    enabling agents to access related discussions. Thread IDs are application-managed
    and typically correspond to [`GroupSession`][group_genie.session.GroupSession]
    IDs.

    Applications are responsible for loading thread messages from the referenced
    group session and including them in the [`Thread`][group_genie.message.Thread]
    object.

    Attributes:
        id: Unique identifier of the referenced thread (typically a GroupSession ID).
        messages: List of messages from the referenced thread.

    Example:
        ```python
        # Load messages from another session
        other_session_messages = await GroupSession.load_messages(other_datastore)

        # Include as thread reference
        thread = Thread(id="session123", messages=other_session_messages)
        message = Message(
            content="Following up on the previous discussion",
            sender="alice",
            threads=[thread]
        )
        ```
    """

    id: str
    messages: list["Message"]

    @staticmethod
    def deserialize(thread_dict: dict[str, Any]) -> "Thread":
        """Reconstruct a [`Thread`][group_genie.message.Thread] from a dictionary.

        Args:
            thread_dict: Dictionary containing thread data with 'id' and 'messages' keys,
                typically obtained from calling asdict() on a
                [`Thread`][group_genie.message.Thread] instance.

        Returns:
            A [`Thread`][group_genie.message.Thread] instance.
        """
        thread_id = thread_dict["id"]
        thread_messages = [Message.deserialize(message_dict) for message_dict in thread_dict["messages"]]
        return Thread(id=thread_id, messages=thread_messages)


@dataclass
class Message:
    """Represents a message in a group chat conversation.

    Messages are the primary unit of communication in Group Genie. Messages can
    include attachments, reference other threads, and optionally specify receivers
    and correlation IDs.

    Attributes:
        content: The text content of the message.
        sender: User ID of the message sender. Use "system" for agent-generated messages.
        receiver: Optional user ID of the intended recipient. When set by a reasoner,
            the agent's response will be directed to this user.
        threads: List of referenced threads from other group chats, providing cross-
            conversation context.
        attachments: List of files attached to this message.
        request_id: Optional correlation ID for matching request messages with their
            responses. Set on request messages passed to
            [`session.handle()`][group_genie.session.GroupSession.handle] to track
            which response corresponds to which request.

    Example:
        ```python
        # Simple message
        message = Message(content="Hello", sender="alice")

        # Message with attachment and receiver
        message = Message(
            content="Please review this document",
            sender="alice",
            receiver="bob",
            attachments=[Attachment(
                path="/tmp/doc.pdf",
                name="Document",
                media_type="application/pdf"
            )],
            request_id="req123"
        )

        # Process message
        execution = session.handle(message)
        response = await execution.result()

        # Response will have same request_id
        assert response.request_id == "req123"
        ```
    """

    content: str
    sender: str
    receiver: str | None = None
    threads: list[Thread] = field(default_factory=list)
    attachments: list[Attachment] = field(default_factory=list)
    request_id: str | None = None

    @staticmethod
    def deserialize(message_dict: dict[str, Any]) -> "Message":
        """Reconstruct a [`Message`][group_genie.message.Message] from a dictionary.

        Args:
            message_dict: Dictionary containing message data with nested
                [`Thread`][group_genie.message.Thread] and
                [`Attachment`][group_genie.message.Attachment] dictionaries, typically
                obtained from calling asdict() on a
                [`Message`][group_genie.message.Message] instance.

        Returns:
            A [`Message`][group_genie.message.Message] instance with all nested
                objects properly deserialized.
        """
        message_data = message_dict.copy()

        # replace thread dicts with Thread objects
        if "threads" in message_data and message_data["threads"]:
            threads = []
            for thread_data in message_data["threads"]:
                thread = Thread.deserialize(thread_data)
                threads.append(thread)
            message_data["threads"] = threads

        # replace attachment dicts with Attachment objects
        if "attachments" in message_data and message_data["attachments"]:
            attachments = []
            for attachment_data in message_data["attachments"]:
                attachment = Attachment.deserialize(attachment_data)
                attachments.append(attachment)
            message_data["attachments"] = attachments

        return Message(**message_data)
