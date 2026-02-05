## group_genie.reasoner.GroupReasoner

Bases: `ABC`

Abstract base class for group reasoning logic.

Group reasoners analyze incoming group chat messages and decide whether to ignore them or generate a query for downstream agents. They maintain conversation history across update messages supplied via run() calls.

State persistence is managed automatically by the framework using JSONL format (one JSON object per line). Persisted state is never transferred between different owners (users).

Example

```
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

### processed

```
processed: int
```

Number of messages processed so far by this reasoner.

Used for tracking conversation history and providing context to the reasoner.

### get_new_messages

```
get_new_messages() -> list[Any]
```

Return new data since last save for appending.

Returns the new data generated during the most recent run() call. Called automatically by the framework after each run to persist incremental state.

Returns:

| Type        | Description                                             |
| ----------- | ------------------------------------------------------- |
| `list[Any]` | List of JSON-serializable objects to append to storage. |

### run

```
run(updates: list[Message]) -> Response
```

Analyze message updates and decide whether to delegate.

Processes new group messages in the context of the entire conversation history and decides whether to ignore them or generate a query for agent processing.

Parameters:

| Name      | Type            | Description                                                                                                     | Default    |
| --------- | --------------- | --------------------------------------------------------------------------------------------------------------- | ---------- |
| `updates` | `list[Message]` | List of new messages to process. Must not be empty. Represents messages that arrived since the last run() call. | *required* |

Returns:

| Type       | Description                                                                                                                     |
| ---------- | ------------------------------------------------------------------------------------------------------------------------------- |
| `Response` | Response from group-sense containing the decision (IGNORE or DELEGATE) and optional delegation parameters (query and receiver). |

### set_serialized

```
set_serialized(lines: list[Any])
```

Reconstruct reasoner state from all JSONL lines.

Rebuilds conversation history and internal state from all previously stored lines. Called automatically by the framework when loading from DataStore.

Parameters:

| Name    | Type        | Description                                      | Default    |
| ------- | ----------- | ------------------------------------------------ | ---------- |
| `lines` | `list[Any]` | All previously stored lines from the JSONL file. | *required* |

## group_genie.reasoner.GroupReasonerFactory

```
GroupReasonerFactory(group_reasoner_factory_fn: GroupReasonerFactoryFn, group_reasoner_idle_timeout: float | None = None, secrets_provider: SecretsProvider | None = None)
```

Bases: `GroupReasonerFactory`

Factory for creating group reasoner instances.

GroupReasonerFactory creates reasoner instances customized for specific users (owners). It provides user-specific secrets and stores idle timeout configuration.

Each user typically gets their own reasoner instance to maintain independent reasoning state and conversation history.

Example

```
def create_reasoner(secrets: dict[str, str], owner: str) -> GroupReasoner:
    template = "You are assisting {owner} in a group chat..."
    system_prompt = template.format(owner=owner)
    return DefaultGroupReasoner(system_prompt=system_prompt)

factory = GroupReasonerFactory(
    group_reasoner_factory_fn=create_reasoner,
    group_reasoner_idle_timeout=600,
    secrets_provider=my_secrets_provider,
)

# Factory creates reasoner for specific user
reasoner = factory.create_group_reasoner(owner="alice")
```

Initialize the group reasoner factory.

Parameters:

| Name                          | Type                     | Description                                                                                        | Default                                                                                                               |
| ----------------------------- | ------------------------ | -------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------- |
| `group_reasoner_factory_fn`   | `GroupReasonerFactoryFn` | Factory function that creates a GroupReasoner for a specific owner. Receives secrets and owner ID. | *required*                                                                                                            |
| `group_reasoner_idle_timeout` | \`float                  | None\`                                                                                             | Optional timeout in seconds after which an idle reasoner is stopped to free resources. Defaults to 600s (10 minutes). |
| `secrets_provider`            | \`SecretsProvider        | None\`                                                                                             | Optional provider for user-specific secrets (e.g., API keys).                                                         |

### create_group_reasoner

```
create_group_reasoner(owner: str, **kwargs: Any) -> GroupReasoner
```

Create a group reasoner instance for a specific owner.

Retrieves secrets for the owner and creates a reasoner instance using the factory function.

Parameters:

| Name       | Type  | Description                                                  | Default    |
| ---------- | ----- | ------------------------------------------------------------ | ---------- |
| `owner`    | `str` | User ID of the reasoner owner.                               | *required* |
| `**kwargs` | `Any` | Additional keyword arguments passed to the factory function. | `{}`       |

Returns:

| Type            | Description                                            |
| --------------- | ------------------------------------------------------ |
| `GroupReasoner` | A new GroupReasoner instance configured for the owner. |

## group_genie.reasoner.GroupReasonerFactoryFn

```
GroupReasonerFactoryFn = Callable[[dict[str, str], str], GroupReasoner]
```

Factory function signature for creating group reasoners.

Creates reasoner instances customized for specific users (owners). Each user typically gets their own reasoner instance to enable concurrent reasoning for different users.

Parameters:

| Name      | Type             | Description                                                                                                                              | Default    |
| --------- | ---------------- | ---------------------------------------------------------------------------------------------------------------------------------------- | ---------- |
| `secrets` | `dict[str, str]` | User-specific credentials (e.g., API keys) retrieved from a SecretsProvider. Common keys include "GOOGLE_API_KEY", "BRAVE_API_KEY", etc. | *required* |
| `owner`   | `str`            | Username of the reasoner owner. Can be used to personalize behavior (e.g., formatting system prompts with the owner's name).             | *required* |

Returns:

| Type | Description                                                  |
| ---- | ------------------------------------------------------------ |
|      | A configured GroupReasoner instance for the specified owner. |

Example

```
def create_reasoner(secrets: dict[str, str], owner: str) -> GroupReasoner:
    template = "You are assisting {owner} in a group chat..."
    system_prompt = template.format(owner=owner)
    model = GoogleModel(
        "gemini-3-flash-preview",
        provider=GoogleProvider(api_key=secrets.get("GOOGLE_API_KEY", "")),
    )
    return DefaultGroupReasoner(
        system_prompt=system_prompt,
        model=model,
    )
```
