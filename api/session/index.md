## group_genie.session.GroupSession

```
GroupSession(id: str, group_reasoner_factory: GroupReasonerFactory, agent_factory: AgentFactory, data_store: DataStore | None = None, preferences_source: PreferencesSource | None = None)
```

Main entry point for managing group chat sessions with AI agents.

GroupSession orchestrates the flow of messages through group reasoners and agents, managing their lifecycle and state persistence. It maintains message ordering, handles concurrent processing for different users, and provides graceful shutdown.

Messages are stored internally in the order of handle() calls and processed concurrently for different senders. Messages from the same sender are always processed sequentially.

Persisted session state (messages and agent/reasoner state) is automatically loaded during initialization if a DataStore is provided.

Example

```
session = GroupSession(
    id="session123",
    group_reasoner_factory=create_group_reasoner_factory(),
    agent_factory=create_agent_factory(),
    data_store=DataStore(root_path=Path(".data/sessions/session123")),
)

# Handle incoming message
execution = session.handle(
    Message(content="What's the weather in Vienna?", sender="alice")
)

# Process execution
async for elem in execution.stream():
    match elem:
        case Decision.DELEGATE:
            print("Query delegated to agent")
        case Approval() as approval:
            approval.approve()
        case Message() as response:
            print(f"Response: {response.content}")

# Gracefully stop session
session.stop()
await session.join()
```

Initialize a new group chat session.

Parameters:

| Name                     | Type                   | Description                                                                                    | Default                                                                                                                                                                                                                |
| ------------------------ | ---------------------- | ---------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `id`                     | `str`                  | Unique identifier for this session. Used as the root key for persisted state in the DataStore. | *required*                                                                                                                                                                                                             |
| `group_reasoner_factory` | `GroupReasonerFactory` | Factory for creating group reasoner instances that decide when to delegate messages to agents. | *required*                                                                                                                                                                                                             |
| `agent_factory`          | `AgentFactory`         | Factory for creating agent instances that process delegated queries.                           | *required*                                                                                                                                                                                                             |
| `data_store`             | \`DataStore            | None\`                                                                                         | Optional persistent storage for session messages and agent state. If provided, session state is automatically loaded on initialization and saved after each message. Experimental feature not suitable for production. |
| `preferences_source`     | \`PreferencesSource    | None\`                                                                                         | Optional source for user-specific preferences that are included in agent prompts.                                                                                                                                      |

### get_group_chat_messages

```
get_group_chat_messages() -> str
```

Returns the group chat messages as a JSON string.

### handle

```
handle(message: Message) -> Execution
```

Process an incoming group chat message.

Adds the message to the session's message history and initiates processing through group reasoners and agents. Returns immediately with an Execution object that can be used to retrieve results.

Messages are stored in the order handle() is called. For different senders, messages are processed concurrently. For the same sender, messages are processed sequentially to maintain conversation coherence.

Parameters:

| Name      | Type      | Description             | Default    |
| --------- | --------- | ----------------------- | ---------- |
| `message` | `Message` | The message to process. | *required* |

Returns:

| Type        | Description                                                                         |
| ----------- | ----------------------------------------------------------------------------------- |
| `Execution` | An Execution object that provides access to the processing stream and final result. |

### join

```
join()
```

Wait for the session to complete shutdown.

Blocks until all internal workers, agents, and reasoners have stopped. Must be called after stop() to ensure proper cleanup.

### load_messages

```
load_messages(data_store: DataStore) -> list[Message] | None
```

Load persisted messages from a data store.

Utility method for accessing session messages without creating a full GroupSession instance. Automatically called during session initialization.

Parameters:

| Name         | Type        | Description                                    | Default    |
| ------------ | ----------- | ---------------------------------------------- | ---------- |
| `data_store` | `DataStore` | DataStore containing the session data to load. | *required* |

Returns:

| Type            | Description |
| --------------- | ----------- |
| \`list[Message] | None\`      |

### request_ids

```
request_ids() -> Future[set[str]]
```

Retrieve all request IDs from messages in this session.

Returns:

| Type               | Description                                                                                                                                                        |
| ------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `Future[set[str]]` | A Future that resolves to a set of request IDs from all messages that have been processed by this session. Only includes messages with non-None request_id values. |

### stop

```
stop()
```

Request graceful shutdown of the session.

Allows currently processing messages to complete before stopping all group reasoners and agents. Call join() after stop() to wait for shutdown completion.

## group_genie.session.Execution

```
Execution(preferences_source: PreferencesSource | None = None)
```

Represents the asynchronous processing of a message through the system.

Execution provides access to the stream of events (decision, approvals, and responses) generated while processing a message. It allows applications to monitor progress, handle approval requests, and retrieve the final result.

The execution stream follows a guaranteed order:

1. One Decision (IGNORE or DELEGATE)
1. Zero or more Approval requests (only if DELEGATE and tools/subagents are called)
1. One Message (only if DELEGATE, containing the agent's response)

Multiple calls to stream() are safe and will return the cached result after the first complete iteration.

Example

```
execution = session.handle(message)

# Stream events
async for elem in execution.stream():
    match elem:
        case Decision.IGNORE:
            print("Message ignored by reasoner")
        case Decision.DELEGATE:
            print("Message delegated to agent")
        case Approval() as approval:
            print(f"Tool call requires approval: {approval}")
            approval.approve()
        case Message() as response:
            print(f"Agent response: {response.content}")

# Or get result directly (auto-approves all tool calls)
result = await execution.result()
if result:
    print(f"Response: {result.content}")
```

### result

```
result() -> Message | None
```

Retrieve the final message result, automatically approving all tool calls.

Convenience method that streams through all events, auto-approving any Approval requests, and returns the final Message. Useful when manual approval handling is not needed.

Returns:

| Type      | Description |
| --------- | ----------- |
| \`Message | None\`      |

### stream

```
stream() -> AsyncIterator[Decision | Approval | Message]
```

Stream execution events as they occur.

Yields events in guaranteed order:

1. One Decision (IGNORE or DELEGATE)
1. Zero or more Approval requests (if DELEGATE and tools are called)
1. One Message (if DELEGATE, containing the final response)

Agent execution blocks on Approval requests until they are approved or denied. Applications must handle all emitted Approvals by calling approve() or deny().

If auto_approve is enabled in the ApprovalContext, Approval events are not emitted and all tool calls are automatically approved.

Can be called multiple times. After the first complete iteration, cached results are returned immediately.

Yields:

| Type                      | Description |
| ------------------------- | ----------- |
| \`AsyncIterator\[Decision | Approval    |
| \`AsyncIterator\[Decision | Approval    |
| \`AsyncIterator\[Decision | Approval    |
| \`AsyncIterator\[Decision | Approval    |

## group_genie.preferences.PreferencesSource

Bases: `ABC`

Abstract base class for providing user-specific preferences.

PreferencesSource supplies user preferences that customize agent behavior and response style. Preferences are typically free-form text (often bullet points) describing formatting, tone, verbosity, and other stylistic choices.

Preferences are included in agent prompts to personalize responses without modifying agent system prompts.

Example

```
class DatabasePreferencesSource(PreferencesSource):
    async def get_preferences(self, username: str) -> str | None:
        user = await database.get_user(username)
        if not user or not user.preferences:
            return None

        return user.preferences
        # Example preferences:
        # "- Prefer concise responses
        #  - Use bullet points for lists
        #  - Include code examples when relevant
        #  - Avoid technical jargon"

class StaticPreferencesSource(PreferencesSource):
    def __init__(self, preferences_map: dict[str, str]):
        self._preferences = preferences_map

    async def get_preferences(self, username: str) -> str | None:
        return self._preferences.get(username)
```

### get_preferences

```
get_preferences(username: str) -> str | None
```

Retrieve preferences for a specific user.

Parameters:

| Name       | Type  | Description                       | Default    |
| ---------- | ----- | --------------------------------- | ---------- |
| `username` | `str` | User ID to fetch preferences for. | *required* |

Returns:

| Type  | Description |
| ----- | ----------- |
| \`str | None\`      |
