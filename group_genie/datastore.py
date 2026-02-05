import json
import logging
import re
from asyncio import CancelledError, Future, Queue, Task, create_task
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, AsyncIterator

from group_genie.utils import arun, completed_future

logger = logging.getLogger(__name__)

Data = Any
Work = tuple[str, list[Data], Future[None]]


class DataStore:
    """Persistent storage for session messages and agent state.

    DataStore provides a simple file-based persistence mechanism for Group Genie
    sessions. It stores data in JSONL files (one JSON object per line) organized
    in a hierarchical directory structure based on session IDs, owner IDs, and
    component keys.

    Key characteristics:

    - Append-only JSONL format (one JSON object per line)
    - Hierarchical key-based organization via
      [`narrow()`][group_genie.datastore.DataStore.narrow]
    - Asynchronous append operations (non-blocking)
    - Key sanitization for filesystem safety
    - No depth limits on hierarchy

    Note:
        This is an experimental store for development and testing. Do not use
        in production.

    Example:
        ```python
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
    """

    def __init__(self, root_path: Path):
        """Initialize a data store with a root directory.

        Args:
            root_path: Root directory for storing all data files.
        """
        self.root_path = root_path
        self._queue: Queue[Work] = Queue()
        self._task: Task[None] = create_task(self._append_worker())

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_value, traceback):
        self._task.cancel()
        try:
            await self._task
        except CancelledError:
            pass

    @asynccontextmanager
    async def narrow(self, key: str) -> AsyncIterator["DataStore"]:
        """Create a narrowed data store scoped to a subdirectory.

        Useful for organizing data hierarchically (e.g., by session, then by user,
        then by component). The key is sanitized for filesystem safety.

        Args:
            key: Subdirectory name. Special characters are sanitized.

        Yields:
            A new [`DataStore`][group_genie.datastore.DataStore] instance rooted at
            the subdirectory.

        Example:
            ```python
            async with store.narrow("alice") as alice_store:
                async with alice_store.narrow("agent") as agent_store:
                    await agent_store.save("state", {...})
            # Saves to: root_path/alice/agent/state.json
            ```
        """
        async with DataStore(root_path=self.narrow_path(key)) as ds:
            yield ds

    def narrow_path(self, *keys: str) -> Path:
        """Compute the path for a narrowed key hierarchy.

        Useful for checking paths or creating directories outside the narrow()
        context manager.

        Args:
            *keys: Sequence of keys defining the subdirectory hierarchy.

        Returns:
            Path to the narrowed directory.
        """
        _keys = [sanitize(k) for k in keys]
        return self.root_path.joinpath(*_keys)

    async def load(self, key: str) -> list[Data]:
        """Load all data lines from storage.

        Args:
            key: Storage key identifying the data to load.

        Returns:
            List of deserialized JSON objects, one per line in the file.

        Raises:
            KeyError: If the key does not exist in storage.
            ValueError: If any line contains malformed JSON.
        """
        return await arun(self._load, key)

    def append(self, key: str, data: list[Data]) -> Future[None]:
        """Append JSON objects as new lines to storage.

        Queues the append operation to execute in the background, allowing the
        caller to continue without blocking. All items are written atomically
        in a single file operation.

        Args:
            key: Storage key for the data.
            data: List of items to append (each must be JSON-serializable).

        Returns:
            A Future that resolves when the append completes. Can be ignored for
                fire-and-forget appends.
        """
        if not data:
            return completed_future()
        future = Future[None]()
        self._queue.put_nowait((key, data, future))
        return future

    async def _append_worker(self):
        while True:
            try:
                key, data, future = await self._queue.get()
            except CancelledError:
                break

            try:
                await arun(self._append, key, data)
            except Exception as e:
                logger.exception("Append error")
                future.set_exception(e)
            else:
                future.set_result(None)

    def _append(self, key: str, data: list[Data]):
        path = self.narrow_path(key)
        path.parent.mkdir(parents=True, exist_ok=True)

        with self._file(key).open("a") as f:
            for item in data:
                f.write(json.dumps(item) + "\n")

    def _load(self, key: str) -> list[Data]:
        path = self._file(key)

        if not path.exists():
            raise KeyError(f"Key not found: {key}")

        lines: list[Data] = []
        with path.open("r") as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                try:
                    lines.append(json.loads(line))
                except json.JSONDecodeError as e:
                    raise ValueError(f"Malformed JSON on line {line_num}: {e}")
        return lines

    def _file(self, key: str) -> Path:
        return self.narrow_path(key).with_suffix(".jsonl")


def sanitize(elem: str) -> str:
    return re.sub(r"[^\w\-]", "_", elem)


@asynccontextmanager
async def narrow(data_store: DataStore | None, key: str) -> AsyncIterator[DataStore | None]:
    if data_store is None:
        yield None
    else:
        async with data_store.narrow(key) as ds:
            yield ds
