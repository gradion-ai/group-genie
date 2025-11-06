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
async def test_save_and_load(store: DataStore):
    data = {"name": "test", "value": 42}

    await store.save("test_key", data)
    loaded = await store.load("test_key")

    assert loaded == data


@pytest.mark.asyncio
async def test_save_creates_json_file(store: DataStore):
    data = {"name": "test"}

    await store.save("test_key", data)

    expected_path = store.root_path / "test_key.json"
    assert expected_path.exists()

    with expected_path.open("r") as f:
        content = json.load(f)
        assert content == data


@pytest.mark.asyncio
async def test_save_creates_parent_directories(store: DataStore):
    data = {"nested": True}

    async with store.narrow("level1") as ns1:
        async with ns1.narrow("level2") as ns2:
            await ns2.save("test_key", data)

            expected_path = store.root_path / "level1" / "level2" / "test_key.json"
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
        await sub_store.save("test_key", data)

        expected_path = store.root_path / "subdir" / "test_key.json"
        assert expected_path.exists()


@pytest.mark.asyncio
async def test_key_sanitization(store: DataStore):
    data = {"sanitized": True}

    await store.save("test/key:with*special?chars", data)

    sanitized_path = store.root_path / "test_key_with_special_chars.json"
    assert sanitized_path.exists()

    loaded = await store.load("test/key:with*special?chars")
    assert loaded == data


@pytest.mark.asyncio
async def test_save_formats_json_with_indent(store: DataStore):
    data = {"name": "test", "nested": {"value": 42}}

    await store.save("test_key", data)

    expected_path = store.root_path / "test_key.json"
    with expected_path.open("r") as f:
        content = f.read()
        assert "\n" in content
        assert "  " in content


@pytest.mark.asyncio
async def test_multiple_saves_to_same_key(store: DataStore):
    await store.save("test_key", {"version": 1})
    await store.save("test_key", {"version": 2})

    loaded = await store.load("test_key")
    assert loaded == {"version": 2}


@pytest.mark.asyncio
async def test_context_isolation(store: DataStore):
    async with store.narrow("ctx1") as context1, store.narrow("ctx2") as context2:
        await context1.save("same_key", {"context": 1})
        await context2.save("same_key", {"context": 2})

        loaded1 = await context1.load("same_key")
        loaded2 = await context2.load("same_key")

        assert loaded1 == {"context": 1}
        assert loaded2 == {"context": 2}


@pytest.mark.asyncio
async def test_save_and_load_list(store: DataStore):
    data = [1, 2, 3, "four", {"five": 5}]

    await store.save("list_key", data)
    loaded = await store.load("list_key")

    assert loaded == data


@pytest.mark.asyncio
async def test_save_and_load_string(store: DataStore):
    data = "simple string value"

    await store.save("string_key", data)
    loaded = await store.load("string_key")

    assert loaded == data


@pytest.mark.asyncio
async def test_save_and_load_integer(store: DataStore):
    data = 42

    await store.save("int_key", data)
    loaded = await store.load("int_key")

    assert loaded == data


@pytest.mark.asyncio
async def test_save_and_load_float(store: DataStore):
    data = 3.14159

    await store.save("float_key", data)
    loaded = await store.load("float_key")

    assert loaded == data


@pytest.mark.asyncio
async def test_save_and_load_boolean(store: DataStore):
    await store.save("bool_true", True)
    await store.save("bool_false", False)

    assert await store.load("bool_true") is True
    assert await store.load("bool_false") is False


@pytest.mark.asyncio
async def test_save_and_load_none(store: DataStore):
    data = None

    await store.save("none_key", data)
    loaded = await store.load("none_key")

    assert loaded is None


@pytest.mark.asyncio
async def test_save_and_load_complex_nested(store: DataStore):
    data = {
        "string": "value",
        "number": 123,
        "float": 45.67,
        "bool": True,
        "null": None,
        "list": [1, "two", 3.0, None, {"nested": "dict"}],
        "nested_dict": {"level2": {"items": [1, 2, 3]}},
    }

    await store.save("complex_key", data)
    loaded = await store.load("complex_key")

    assert loaded == data
