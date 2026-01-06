## group_genie.reasoner.GroupReasoner

Bases: `ABC`

Abstract base class for group reasoning logic.

Group reasoners analyze incoming group chat messages and decide whether to ignore them or generate a query for downstream agents. They maintain conversation history across update messages supplied via run() calls.

State persistence is managed automatically by the framework and stored in JSON format. Persisted state is never transferred between different owners (users).

Example

```
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

### processed

```
processed: int
```

Number of messages processed so far by this reasoner.

Used for tracking conversation history and providing context to the reasoner.

### get_serialized

```
get_serialized() -> Any
```

Serialize reasoner state for persistence.

Returns conversation history and any other state needed to resume the reasoner after a restart. Called automatically by the framework before saving to DataStore.

Returns:

| Type  | Description                                                                   |
| ----- | ----------------------------------------------------------------------------- |
| `Any` | Serializable state (must be JSON-compatible). Implementation-specific format. |

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
set_serialized(serialized: Any)
```

Restore reasoner state from serialized data.

Reconstructs conversation history and internal state from previously serialized data. Called automatically by the framework after loading from DataStore.

Parameters:

| Name         | Type  | Description                                        | Default    |
| ------------ | ----- | -------------------------------------------------- | ---------- |
| `serialized` | `Any` | Previously serialized state from get_serialized(). | *required* |

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
        "gemini-2.5-flash",
        provider=GoogleProvider(api_key=secrets.get("GOOGLE_API_KEY", "")),
    )
    return DefaultGroupReasoner(
        system_prompt=system_prompt,
        model=model,
    )
```
