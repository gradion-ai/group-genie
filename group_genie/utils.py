from asyncio import Future, get_running_loop
from functools import partial
from typing import Callable, TypeVar
from uuid import uuid4

T = TypeVar("T")


async def arun(func: Callable[..., T], *args, **kwargs) -> T:
    return await get_running_loop().run_in_executor(None, partial(func, *args, **kwargs))


def identifier() -> str:
    return uuid4().hex


def completed_future() -> Future[None]:
    """Return a Future that is already resolved with None."""
    future: Future[None] = Future()
    future.set_result(None)
    return future
