# Chat Server Integration

This guide demonstrates how to integrate Group Genie into a chat server to enable multi-party reasoning and agent responses in group chat environments. We'll use the [group-terminal](https://github.com/gradion-ai/group-terminal) chat server as a reference implementation, but the patterns apply to any chat server architecture.

!!! Note

    This integration guide assumes you are familiar with the Group Genie [tutorial](tutorial.md).

## Overview

Integrating Group Genie into a chat server involves connecting two key components:

1. **Chat Server**: Receives messages from users and broadcasts responses back to connected clients
2. **Group Session**: Processes messages through group reasoning and agent execution and publishes responses to the group.

## Key Integration Points

A chat server usually provides two integration points. The following are specific to the [group-terminal](https://gradion-ai.github.io/group-terminal/) chat server:

1. **Message Handler**: A callback that receives incoming messages from chat clients
    - Signature: `async def handler(content: str, sender: str)`
    - Called sequentially in message arrival order
    - Must be non-blocking to avoid delaying subsequent messages

2. **Send Message**: A method to broadcast responses back to chat clients
    - Signature: `async def send_message(content: str, sender: str)`
    - Called from message processing tasks to deliver agent responses

## Implementation Pattern

### Message Ingestion

```python
from asyncio import create_task
from group_terminal.server import ChatServer
from group_genie.session import GroupSession
from group_genie.message import Message

class App:
    def __init__(
        self,
        group_reasoner_factory,
        agent_factory,
        session_id,
        host="0.0.0.0",
        port=8723,
    ):
        # Initialize Group Session
        self._session = GroupSession(
            id=session_id,
            group_reasoner_factory=group_reasoner_factory,
            agent_factory=agent_factory,
            data_store=data_store,
        )

        # Initialize chat server and register message handler
        self._server = ChatServer(host=host, port=port)
        self._server.add_handler(self._handle_message)

    async def _handle_message(self, content: str, sender: str):
        # Create Group Genie message from chat message
        message = Message(content=content, sender=sender)

        # Add message to session in arrival order
        # handle() must be called sequentially
        # to maintain consistent message ordering
        execution = self._session.handle(message)

        # Process messages asynchronously to avoid blocking
        # the message handler from receiving subsequent messages
        create_task(self._complete_execution(execution))
```

Message ingestion includes:

- `session.handle(message)` is called synchronously in the message handler, ensuring messages are added to the session in arrival order
- `create_task()` runs the message processing coroutine asynchronously, allowing the message handler to return immediately and receive the next message
- This design maintains ordering guarantees while preventing long-running agent executions from blocking the message queue

## Message Processing

The `_complete_execution()` message processing coroutine processes three types of elements from an [`Execution`][group_genie.session.Execution] stream:

```python
from group_genie.session import Execution
from group_genie.agent import Approval, Decision
from group_genie.message import Message

async def _complete_execution(self, execution: Execution):
    async for elem in execution.stream():
        match elem:
            case Decision() as decision:
                # Group reasoner decided to IGNORE or DELEGATE
                logger.debug(f"Reasoner decision: {decision.value}")

            case Approval() as approval:
                # Agent requests tool call approval
                logger.debug(f"Auto-approve {approval}")
                elem.approve()

            case Message() as message:
                # Agent generated a response message
                logger.debug(f"Agent response: {message.content}")
                await self._server.send_message(
                    message.content,
                    sender=message.sender
                )
```

- **Decision**: Logs the group reasoner's decision (IGNORE or DELEGATE). If IGNORE, the stream completes with no further elements.
- **Approval**: Handles tool call approval requests. In this example, all tool calls are auto-approved. Production systems might implement manual approval workflows.
- **Message**: Send agent responses back to chat clients via the server's `send_message` method.

## Complete Example

The complete example is available at [examples/guide/chat.py](https://github.com/gradion-ai/group-genie/blob/main/examples/guide/chat.py).

### Running the Example

Start the chat server with the [fact-checking](https://github.com/gradion-ai/group-genie/blob/main/examples/prompts/reasoner/fact_check.md) template:

```bash
python examples/guide/chat.py --template-name fact_check
```

In separate terminals, launch three clients:

```bash
python -m group_terminal.client --username user1
python -m group_terminal.client --username user2
python -m group_terminal.client --username user3
```

### Example Conversation

The screenshots below show the fact-checking scenario from the tutorial, but running in a group chat environment. The same three users (user1, user2, user3) participate in the conversation:


`user1`'s view:
![User1's view](images/chat-user1.png)

`user2`'s view:
![User2's view](images/chat-user2.png)

`user3`'s view:
![User3's view](images/chat-user3.png)

The group reasoner detects the factual inconsistency (Hofbräuhaus is in Munich, not Vienna) and delegates to the system agent to resolve it.
