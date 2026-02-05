from typing import Any

from pydantic_ai.messages import ModelMessage, ModelMessagesTypeAdapter
from pydantic_core import to_jsonable_python


class Stateful:
    def __init__(self):
        self._history: list[ModelMessage] = []
        self._new_messages: list[ModelMessage] = []

    def get_new_messages(self) -> list[Any]:
        result = [to_jsonable_python(msg, bytes_mode="base64") for msg in self._new_messages]
        self._new_messages = []
        return result

    def set_serialized(self, lines: list[Any]):
        self._history = ModelMessagesTypeAdapter.validate_python(lines)
        self._new_messages = []
