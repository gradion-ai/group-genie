import tempfile
from dataclasses import asdict
from pathlib import Path

import pytest

from group_genie.message import Attachment, Message, Thread


class TestAttachment:
    def test_attachment_creation(self):
        attachment = Attachment(path="/tmp/file.txt", name="file.txt", media_type="text/plain")
        assert attachment.path == "/tmp/file.txt"
        assert attachment.name == "file.txt"
        assert attachment.media_type == "text/plain"

    @pytest.mark.asyncio
    async def test_attachment_bytes(self):
        with tempfile.NamedTemporaryFile(mode="wb", delete=False) as f:
            test_data = b"test content"
            f.write(test_data)
            temp_path = f.name

        try:
            attachment = Attachment(path=temp_path, name="test.txt", media_type="text/plain")
            content = await attachment.bytes()
            assert content == test_data
        finally:
            Path(temp_path).unlink()

    def test_attachment_deserialize(self):
        attachment_dict = {"path": "/tmp/file.txt", "name": "file.txt", "media_type": "text/plain"}
        result = Attachment.deserialize(attachment_dict)
        assert result.path == "/tmp/file.txt"
        assert result.name == "file.txt"
        assert result.media_type == "text/plain"


class TestThread:
    def test_thread_creation(self):
        message = Message(content="test", sender="user")
        thread = Thread(id="thread-1", messages=[message])
        assert thread.id == "thread-1"
        assert len(thread.messages) == 1
        assert thread.messages[0].content == "test"


class TestMessage:
    def test_message_basic_creation(self):
        message = Message(content="Hello", sender="user")
        assert message.content == "Hello"
        assert message.sender == "user"
        assert message.receiver is None
        assert message.threads == []
        assert message.attachments == []

    def test_message_with_receiver(self):
        message = Message(content="Hello", sender="user", receiver="assistant")
        assert message.receiver == "assistant"

    def test_message_with_attachments(self):
        attachments = [Attachment(path="/tmp/file.txt", name="file.txt", media_type="text/plain")]
        message = Message(content="Hello", sender="user", attachments=attachments)
        assert len(message.attachments) == 1
        assert message.attachments[0].name == "file.txt"

    def test_message_with_threads(self):
        nested_message = Message(content="nested", sender="user")
        thread = Thread(id="thread-1", messages=[nested_message])
        message = Message(content="parent", sender="user", threads=[thread])
        assert len(message.threads) == 1
        assert message.threads[0].id == "thread-1"
        assert len(message.threads[0].messages) == 1

    def test_message_deserialize_basic(self):
        message_dict = {"content": "test", "sender": "user"}
        message = Message.deserialize(message_dict)
        assert message.content == "test"
        assert message.sender == "user"
        assert message.receiver is None
        assert message.threads == []
        assert message.attachments == []

    def test_message_deserialize_with_receiver(self):
        message_dict = {"content": "test", "sender": "user", "receiver": "assistant"}
        message = Message.deserialize(message_dict)
        assert message.receiver == "assistant"

    def test_message_deserialize_with_attachments(self):
        message_dict = {
            "content": "test",
            "sender": "user",
            "attachments": [{"path": "/tmp/file.txt", "name": "file.txt", "media_type": "text/plain"}],
        }
        message = Message.deserialize(message_dict)
        assert len(message.attachments) == 1
        assert message.attachments[0].path == "/tmp/file.txt"
        assert message.attachments[0].name == "file.txt"
        assert message.attachments[0].media_type == "text/plain"

    def test_message_deserialize_with_empty_collections(self):
        message_dict = {"content": "test", "sender": "user", "attachments": [], "threads": []}
        message = Message.deserialize(message_dict)
        assert message.attachments == []
        assert message.threads == []

    def test_message_deserialize_with_one_level_threads(self):
        message_dict = {
            "content": "parent message",
            "sender": "user",
            "threads": [
                {
                    "id": "thread-1",
                    "messages": [{"content": "child message", "sender": "assistant"}],
                }
            ],
        }
        message = Message.deserialize(message_dict)
        assert message.content == "parent message"
        assert len(message.threads) == 1
        assert message.threads[0].id == "thread-1"
        assert len(message.threads[0].messages) == 1
        assert message.threads[0].messages[0].content == "child message"
        assert message.threads[0].messages[0].sender == "assistant"

    def test_message_deserialize_with_multiple_threads(self):
        message_dict = {
            "content": "parent message",
            "sender": "user",
            "threads": [
                {
                    "id": "thread-1",
                    "messages": [{"content": "child message 1", "sender": "assistant"}],
                },
                {
                    "id": "thread-2",
                    "messages": [{"content": "child message 2", "sender": "assistant"}],
                },
            ],
        }
        message = Message.deserialize(message_dict)
        assert len(message.threads) == 2
        assert message.threads[0].id == "thread-1"
        assert message.threads[1].id == "thread-2"
        assert message.threads[0].messages[0].content == "child message 1"
        assert message.threads[1].messages[0].content == "child message 2"

    def test_message_deserialize_recursive_three_levels(self):
        message_dict = {
            "content": "level 0",
            "sender": "user",
            "threads": [
                {
                    "id": "thread-1",
                    "messages": [
                        {
                            "content": "level 1",
                            "sender": "assistant",
                            "threads": [
                                {
                                    "id": "thread-2",
                                    "messages": [
                                        {
                                            "content": "level 2",
                                            "sender": "user",
                                            "threads": [
                                                {
                                                    "id": "thread-3",
                                                    "messages": [{"content": "level 3", "sender": "assistant"}],
                                                }
                                            ],
                                        }
                                    ],
                                }
                            ],
                        }
                    ],
                }
            ],
        }
        message = Message.deserialize(message_dict)
        assert message.content == "level 0"
        level_1_message = message.threads[0].messages[0]
        assert level_1_message.content == "level 1"
        level_2_message = level_1_message.threads[0].messages[0]
        assert level_2_message.content == "level 2"
        level_3_message = level_2_message.threads[0].messages[0]
        assert level_3_message.content == "level 3"

    def test_message_deserialize_complex_nested_structure(self):
        message_dict = {
            "content": "root message",
            "sender": "user",
            "threads": [
                {
                    "id": "thread-1",
                    "messages": [
                        {
                            "content": "branch 1 level 1",
                            "sender": "assistant",
                            "threads": [
                                {
                                    "id": "thread-1-1",
                                    "messages": [{"content": "branch 1 level 2", "sender": "user"}],
                                }
                            ],
                        }
                    ],
                },
                {
                    "id": "thread-2",
                    "messages": [
                        {
                            "content": "branch 2 level 1",
                            "sender": "assistant",
                            "threads": [
                                {
                                    "id": "thread-2-1",
                                    "messages": [{"content": "branch 2 level 2", "sender": "user"}],
                                }
                            ],
                        }
                    ],
                },
            ],
        }
        message = Message.deserialize(message_dict)
        assert message.content == "root message"
        assert len(message.threads) == 2
        assert message.threads[0].messages[0].content == "branch 1 level 1"
        assert message.threads[0].messages[0].threads[0].messages[0].content == "branch 1 level 2"
        assert message.threads[1].messages[0].content == "branch 2 level 1"
        assert message.threads[1].messages[0].threads[0].messages[0].content == "branch 2 level 2"

    def test_message_deserialize_with_threads_and_attachments(self):
        message_dict = {
            "content": "complex message",
            "sender": "user",
            "threads": [
                {
                    "id": "thread-1",
                    "messages": [
                        {
                            "content": "nested message",
                            "sender": "assistant",
                            "attachments": [
                                {"path": "/tmp/nested.txt", "name": "nested.txt", "media_type": "text/plain"}
                            ],
                        }
                    ],
                }
            ],
            "attachments": [{"path": "/tmp/root.txt", "name": "root.txt", "media_type": "text/plain"}],
        }
        message = Message.deserialize(message_dict)
        assert len(message.attachments) == 1
        assert message.attachments[0].name == "root.txt"
        assert len(message.threads[0].messages[0].attachments) == 1
        assert message.threads[0].messages[0].attachments[0].name == "nested.txt"

    def test_message_roundtrip_serialization(self):
        attachment = Attachment(path="/tmp/file.txt", name="file.txt", media_type="text/plain")
        nested_message = Message(content="nested", sender="assistant", attachments=[attachment])
        thread = Thread(id="thread-1", messages=[nested_message])
        original = Message(content="parent", sender="user", receiver="bot", threads=[thread])
        serialized = asdict(original)
        deserialized = Message.deserialize(serialized)
        assert deserialized.content == original.content
        assert deserialized.sender == original.sender
        assert deserialized.receiver == original.receiver
        assert len(deserialized.threads) == 1
        assert deserialized.threads[0].id == original.threads[0].id
        assert len(deserialized.threads[0].messages[0].attachments) == 1
