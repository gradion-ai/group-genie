## group_genie.datastore.DataStore

```
DataStore(root_path: Path)
```

Persistent storage for session messages and agent state.

DataStore provides a simple file-based persistence mechanism for Group Genie sessions. It stores data in JSONL files (one JSON object per line) organized in a hierarchical directory structure based on session IDs, owner IDs, and component keys.

Key characteristics:

- Append-only JSONL format (one JSON object per line)
- Hierarchical key-based organization via narrow()
- Asynchronous append operations (non-blocking)
- Key sanitization for filesystem safety
- No depth limits on hierarchy

Note

This is an experimental store for development and testing. Do not use in production.

Example

```
# Create data store for a session
store = DataStore(root_path=Path(".data/sessions/session123"))

# Append data (one line per call)
store.append("messages", {"content": "hello", "sender": "alice"})

# Load all lines
lines = await store.load("messages")  # Returns list of dicts

# Create narrowed store for a component
async with store.narrow("alice") as alice_store:
    alice_store.append("agent", message_data)

# Path structure: .data/sessions/session123/alice/agent.jsonl
```

Initialize a data store with a root directory.

Parameters:

| Name        | Type   | Description                                | Default    |
| ----------- | ------ | ------------------------------------------ | ---------- |
| `root_path` | `Path` | Root directory for storing all data files. | *required* |

### append

```
append(key: str, data: list[Data]) -> Future[None]
```

Append JSON objects as new lines to storage.

Queues the append operation to execute in the background, allowing the caller to continue without blocking. All items are written atomically in a single file operation.

Parameters:

| Name   | Type         | Description                                               | Default    |
| ------ | ------------ | --------------------------------------------------------- | ---------- |
| `key`  | `str`        | Storage key for the data.                                 | *required* |
| `data` | `list[Data]` | List of items to append (each must be JSON-serializable). | *required* |

Returns:

| Type           | Description                                                                                   |
| -------------- | --------------------------------------------------------------------------------------------- |
| `Future[None]` | A Future that resolves when the append completes. Can be ignored for fire-and-forget appends. |

### load

```
load(key: str) -> list[Data]
```

Load all data lines from storage.

Parameters:

| Name  | Type  | Description                               | Default    |
| ----- | ----- | ----------------------------------------- | ---------- |
| `key` | `str` | Storage key identifying the data to load. | *required* |

Returns:

| Type         | Description                                                  |
| ------------ | ------------------------------------------------------------ |
| `list[Data]` | List of deserialized JSON objects, one per line in the file. |

Raises:

| Type         | Description                           |
| ------------ | ------------------------------------- |
| `KeyError`   | If the key does not exist in storage. |
| `ValueError` | If any line contains malformed JSON.  |

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
