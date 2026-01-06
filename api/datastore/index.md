## group_genie.datastore.DataStore

```
DataStore(root_path: Path)
```

Persistent storage for session messages and agent state.

DataStore provides a simple file-based persistence mechanism for Group Genie sessions. It stores data in JSON files organized in a hierarchical directory structure based on session IDs, owner IDs, and component keys.

Key characteristics:

- Automatic JSON serialization
- Hierarchical key-based organization via narrow()
- Asynchronous save operations (non-blocking)
- Key sanitization for filesystem safety
- No depth limits on hierarchy

Note

This is an experimental snapshot store for development and testing. Do not use in production.

Example

```
# Create data store for a session
store = DataStore(root_path=Path(".data/sessions/session123"))

# Save data
await store.save("messages", {"messages": [...]})

# Load data
data = await store.load("messages")

# Create narrowed store for a component
async with store.narrow("alice") as alice_store:
    await alice_store.save("agent", agent_state)

# Path structure: .data/sessions/session123/alice/agent.json
```

Initialize a data store with a root directory.

Parameters:

| Name        | Type   | Description                                | Default    |
| ----------- | ------ | ------------------------------------------ | ---------- |
| `root_path` | `Path` | Root directory for storing all data files. | *required* |

### load

```
load(key: str) -> Data
```

Load data from storage.

Parameters:

| Name  | Type  | Description                               | Default    |
| ----- | ----- | ----------------------------------------- | ---------- |
| `key` | `str` | Storage key identifying the data to load. | *required* |

Returns:

| Type   | Description                               |
| ------ | ----------------------------------------- |
| `Data` | The loaded data (deserialized from JSON). |

Raises:

| Type       | Description                           |
| ---------- | ------------------------------------- |
| `KeyError` | If the key does not exist in storage. |

### narrow

```
narrow(key: str) -> AsyncIterator[DataStore]
```

Create a narrowed data store scoped to a subdirectory.

Useful for organizing data hierarchically (e.g., by session, then by user, then by component). The key is sanitized for filesystem safety.

Parameters:

| Name  | Type  | Description                                          | Default    |
| ----- | ----- | ---------------------------------------------------- | ---------- |
| `key` | `str` | Subdirectory name. Special characters are sanitized. | *required* |

Yields:

| Type                       | Description                        |
| -------------------------- | ---------------------------------- |
| `AsyncIterator[DataStore]` | A new DataStore instance rooted at |
| `AsyncIterator[DataStore]` | the subdirectory.                  |

Example

```
async with store.narrow("alice") as alice_store:
    async with alice_store.narrow("agent") as agent_store:
        await agent_store.save("state", {...})
# Saves to: root_path/alice/agent/state.json
```

### narrow_path

```
narrow_path(*keys: str) -> Path
```

Compute the path for a narrowed key hierarchy.

Useful for checking paths or creating directories outside the narrow() context manager.

Parameters:

| Name    | Type  | Description                                           | Default |
| ------- | ----- | ----------------------------------------------------- | ------- |
| `*keys` | `str` | Sequence of keys defining the subdirectory hierarchy. | `()`    |

Returns:

| Type   | Description                     |
| ------ | ------------------------------- |
| `Path` | Path to the narrowed directory. |

### save

```
save(key: str, data: Data) -> Future[None]
```

Save data to storage asynchronously.

Queues the save operation to execute in the background, allowing the caller to continue without blocking.

Parameters:

| Name   | Type   | Description                               | Default    |
| ------ | ------ | ----------------------------------------- | ---------- |
| `key`  | `str`  | Storage key for the data.                 | *required* |
| `data` | `Data` | Data to save (must be JSON-serializable). | *required* |

Returns:

| Type           | Description                                                                               |
| -------------- | ----------------------------------------------------------------------------------------- |
| `Future[None]` | A Future that resolves when the save completes. Can be ignored for fire-and-forget saves. |
