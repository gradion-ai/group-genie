from typing import Any

from pydantic_ai.messages import ModelMessage, ModelMessagesTypeAdapter
from pydantic_core import to_jsonable_python


class Stateful:
    def __init__(self):
        self._history: list[ModelMessage] = []

    def get_serialized(self) -> Any:
        return to_jsonable_python(self._history, bytes_mode="base64")

    def set_serialized(self, state: Any):
        self._history = ModelMessagesTypeAdapter.validate_python(state)
