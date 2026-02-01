import json
from pathlib import Path
from typing import AsyncIterator

import pytest
import pytest_asyncio

from group_genie.datastore import DataStore


@pytest_asyncio.fixture
async def store(tmp_path: Path) -> AsyncIterator[DataStore]:
    async with DataStore(root_path=tmp_path) as ds:
        yield ds


@pytest.mark.asyncio
async def test_append_and_load(store: DataStore):
    data = {"name": "test", "value": 42}

    await store.append("test_key", [data])
    loaded = await store.load("test_key")

    assert loaded == [data]


@pytest.mark.asyncio
async def test_append_creates_jsonl_file(store: DataStore):
    data = {"name": "test"}

    await store.append("test_key", [data])

    expected_path = store.root_path / "test_key.jsonl"
    assert expected_path.exists()

    with expected_path.open("r") as f:
        content = f.read().strip()
        assert json.loads(content) == data


@pytest.mark.asyncio
async def test_append_creates_parent_directories(store: DataStore):
    data = {"nested": True}

    async with store.narrow("level1") as ns1:
        async with ns1.narrow("level2") as ns2:
            await ns2.append("test_key", [data])

            expected_path = store.root_path / "level1" / "level2" / "test_key.jsonl"
            assert expected_path.exists()
            assert expected_path.parent.parent.parent == store.root_path


@pytest.mark.asyncio
async def test_load_nonexistent_key_raises_error(store: DataStore):
    with pytest.raises(KeyError, match="Key not found: nonexistent"):
        await store.load("nonexistent")


@pytest.mark.asyncio
async def test_context_creates_substore(store: DataStore):
    async with store.narrow("subdir") as sub_store:
        data = {"context": "test"}
        await sub_store.append("test_key", [data])

        expected_path = store.root_path / "subdir" / "test_key.jsonl"
        assert expected_path.exists()


@pytest.mark.asyncio
async def test_key_sanitization(store: DataStore):
    data = {"sanitized": True}

    await store.append("test/key:with*special?chars", [data])

    sanitized_path = store.root_path / "test_key_with_special_chars.jsonl"
    assert sanitized_path.exists()

    loaded = await store.load("test/key:with*special?chars")
    assert loaded == [data]


@pytest.mark.asyncio
async def test_append_batch_writes_multiple_lines(store: DataStore):
    data1 = {"line": 1}
    data2 = {"line": 2}

    await store.append("test_key", [data1, data2])

    expected_path = store.root_path / "test_key.jsonl"
    with expected_path.open("r") as f:
        lines = f.readlines()
        assert len(lines) == 2
        assert json.loads(lines[0]) == data1
        assert json.loads(lines[1]) == data2


@pytest.mark.asyncio
async def test_multiple_appends_to_same_key(store: DataStore):
    await store.append("test_key", [{"version": 1}])
    await store.append("test_key", [{"version": 2}])

    loaded = await store.load("test_key")
    assert loaded == [{"version": 1}, {"version": 2}]


@pytest.mark.asyncio
async def test_context_isolation(store: DataStore):
    async with store.narrow("ctx1") as context1, store.narrow("ctx2") as context2:
        await context1.append("same_key", [{"context": 1}])
        await context2.append("same_key", [{"context": 2}])

        loaded1 = await context1.load("same_key")
        loaded2 = await context2.load("same_key")

        assert loaded1 == [{"context": 1}]
        assert loaded2 == [{"context": 2}]


@pytest.mark.asyncio
async def test_append_and_load_list(store: DataStore):
    data = [1, 2, 3, "four", {"five": 5}]

    await store.append("list_key", [data])
    loaded = await store.load("list_key")

    assert loaded == [data]


@pytest.mark.asyncio
async def test_append_and_load_string(store: DataStore):
    data = "simple string value"

    await store.append("string_key", [data])
    loaded = await store.load("string_key")

    assert loaded == [data]


@pytest.mark.asyncio
async def test_append_and_load_integer(store: DataStore):
    data = 42

    await store.append("int_key", [data])
    loaded = await store.load("int_key")

    assert loaded == [data]


@pytest.mark.asyncio
async def test_append_and_load_float(store: DataStore):
    data = 3.14159

    await store.append("float_key", [data])
    loaded = await store.load("float_key")

    assert loaded == [data]


@pytest.mark.asyncio
async def test_append_and_load_boolean(store: DataStore):
    await store.append("bool_true", [True])
    await store.append("bool_false", [False])

    assert await store.load("bool_true") == [True]
    assert await store.load("bool_false") == [False]


@pytest.mark.asyncio
async def test_append_and_load_none(store: DataStore):
    data = None

    await store.append("none_key", [data])
    loaded = await store.load("none_key")

    assert loaded == [None]


@pytest.mark.asyncio
async def test_append_and_load_complex_nested(store: DataStore):
    data = {
        "string": "value",
        "number": 123,
        "float": 45.67,
        "bool": True,
        "null": None,
        "list": [1, "two", 3.0, None, {"nested": "dict"}],
        "nested_dict": {"level2": {"items": [1, 2, 3]}},
    }

    await store.append("complex_key", [data])
    loaded = await store.load("complex_key")

    assert loaded == [data]


@pytest.mark.asyncio
async def test_load_malformed_json_raises_error(store: DataStore):
    # Write malformed JSON directly to file
    file_path = store.root_path / "malformed.jsonl"
    file_path.parent.mkdir(parents=True, exist_ok=True)
    with file_path.open("w") as f:
        f.write('{"valid": true}\n')
        f.write("invalid json line\n")
        f.write('{"also_valid": true}\n')

    with pytest.raises(ValueError, match="Malformed JSON on line 2"):
        await store.load("malformed")


@pytest.mark.asyncio
async def test_load_empty_lines_are_skipped(store: DataStore):
    # Write JSONL with empty lines
    file_path = store.root_path / "with_empty.jsonl"
    file_path.parent.mkdir(parents=True, exist_ok=True)
    with file_path.open("w") as f:
        f.write('{"line": 1}\n')
        f.write("\n")
        f.write('{"line": 2}\n')
        f.write("   \n")
        f.write('{"line": 3}\n')

    loaded = await store.load("with_empty")
    assert loaded == [{"line": 1}, {"line": 2}, {"line": 3}]


@pytest.mark.asyncio
async def test_append_empty_list_is_noop(store: DataStore):
    # Appending empty list should not create file
    future = store.append("empty_key", [])

    # Should return completed future
    assert future.done()

    # File should not exist
    expected_path = store.root_path / "empty_key.jsonl"
    assert not expected_path.exists()
