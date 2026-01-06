## group_genie.message.Message

```
Message(content: str, sender: str, receiver: str | None = None, threads: list[Thread] = list(), attachments: list[Attachment] = list(), request_id: str | None = None)
```

Represents a message in a group chat conversation.

Messages are the primary unit of communication in Group Genie. Messages can include attachments, reference other threads, and optionally specify receivers and correlation IDs.

Attributes:

| Name          | Type               | Description                                                                               |
| ------------- | ------------------ | ----------------------------------------------------------------------------------------- |
| `content`     | `str`              | The text content of the message.                                                          |
| `sender`      | `str`              | User ID of the message sender. Use "system" for agent-generated messages.                 |
| `receiver`    | \`str              | None\`                                                                                    |
| `threads`     | `list[Thread]`     | List of referenced threads from other group chats, providing cross- conversation context. |
| `attachments` | `list[Attachment]` | List of files attached to this message.                                                   |
| `request_id`  | \`str              | None\`                                                                                    |

Example

```
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

### deserialize

```
deserialize(message_dict: dict[str, Any]) -> Message
```

Reconstruct a Message from a dictionary.

Parameters:

| Name           | Type             | Description                                                                                                                                        | Default    |
| -------------- | ---------------- | -------------------------------------------------------------------------------------------------------------------------------------------------- | ---------- |
| `message_dict` | `dict[str, Any]` | Dictionary containing message data with nested Thread and Attachment dictionaries, typically obtained from calling asdict() on a Message instance. | *required* |

Returns:

| Type      | Description                                                       |
| --------- | ----------------------------------------------------------------- |
| `Message` | A Message instance with all nested objects properly deserialized. |

## group_genie.message.Attachment

```
Attachment(path: str, name: str, media_type: str)
```

Metadata for files attached to group chat messages.

Attachments represent files (images, documents, etc.) that accompany messages. They reference local filesystem paths and provide metadata for agents to understand and process the files.

The file at the specified path must exist when bytes is called, otherwise an error is raised and the agent run fails.

Attributes:

| Name         | Type  | Description                                                         |
| ------------ | ----- | ------------------------------------------------------------------- |
| `path`       | `str` | Local filesystem path to the attachment file.                       |
| `name`       | `str` | Display name of the attachment.                                     |
| `media_type` | `str` | MIME type of the attachment (e.g., 'image/png', 'application/pdf'). |

Example

```
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

### media_type

```
media_type: str
```

MIME type of the attachment.

### name

```
name: str
```

Name of the attachment.

### path

```
path: str
```

Local file path to the attachment.

### bytes

```
bytes() -> bytes
```

Read the attachment file contents.

Returns:

| Type    | Description                           |
| ------- | ------------------------------------- |
| `bytes` | The raw bytes of the attachment file. |

Raises:

| Type                | Description                         |
| ------------------- | ----------------------------------- |
| `FileNotFoundError` | If the file at path does not exist. |

### deserialize

```
deserialize(attachment_dict: dict[str, Any]) -> Attachment
```

Reconstruct an Attachment from a dictionary.

Parameters:

| Name              | Type             | Description                                                                                                | Default    |
| ----------------- | ---------------- | ---------------------------------------------------------------------------------------------------------- | ---------- |
| `attachment_dict` | `dict[str, Any]` | Dictionary containing attachment data, typically obtained from calling asdict() on an Attachment instance. | *required* |

Returns:

| Type         | Description             |
| ------------ | ----------------------- |
| `Attachment` | An Attachment instance. |

## group_genie.message.Thread

```
Thread(id: str, messages: list[Message])
```

Reference to a conversation thread from another group chat.

Threads allow messages to include context from other group conversations, enabling agents to access related discussions. Thread IDs are application-managed and typically correspond to GroupSession IDs.

Applications are responsible for loading thread messages from the referenced group session and including them in the Thread object.

Attributes:

| Name       | Type            | Description                                                               |
| ---------- | --------------- | ------------------------------------------------------------------------- |
| `id`       | `str`           | Unique identifier of the referenced thread (typically a GroupSession ID). |
| `messages` | `list[Message]` | List of messages from the referenced thread.                              |

Example

```
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

### deserialize

```
deserialize(thread_dict: dict[str, Any]) -> Thread
```

Reconstruct a Thread from a dictionary.

Parameters:

| Name          | Type             | Description                                                                                                                     | Default    |
| ------------- | ---------------- | ------------------------------------------------------------------------------------------------------------------------------- | ---------- |
| `thread_dict` | `dict[str, Any]` | Dictionary containing thread data with 'id' and 'messages' keys, typically obtained from calling asdict() on a Thread instance. | *required* |

Returns:

| Type     | Description        |
| -------- | ------------------ |
| `Thread` | A Thread instance. |
