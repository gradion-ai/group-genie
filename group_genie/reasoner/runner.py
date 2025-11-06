import logging
from asyncio import CancelledError, Future, Queue, Task, create_task, sleep
from dataclasses import dataclass, field

from group_sense import Decision, Response

from group_genie.datastore import DataStore, narrow
from group_genie.message import Message
from group_genie.reasoner.factory import GroupReasonerFactory

logger = logging.getLogger(__name__)


class GroupReasonerRunner:
    def __init__(
        self,
        key: str,
        owner: str,
        group_reasoner_factory: GroupReasonerFactory,
        data_store: DataStore | None = None,
    ):
        self.key = key
        self.owner = owner
        self.data_store = data_store

        self._group_reasoner = group_reasoner_factory.create_group_reasoner(owner=owner)
        self._idle_timeout = group_reasoner_factory.group_reasoner_idle_timeout
        self._idle_timer: Task | None = None

        self._worker_queue: Queue[Invoke | Stop] = Queue()
        self._worker_task = create_task(self._work())
        self._stopped = False

    @property
    def stopped(self) -> bool:
        return self._stopped

    def stop(self):
        if not self.stopped:
            self._stopped = True
            self._worker_queue.put_nowait(Stop())

    async def _stop_after(self, timeout: float):
        try:
            await sleep(timeout)
        except CancelledError:
            pass
        else:
            self.stop()

    async def join(self):
        await self._worker_task
        if self._idle_timer is not None:
            self._idle_timer.cancel()
            await self._idle_timer

    def invoke(self, messages: list[Message]) -> Future[Response]:
        if self._idle_timer is not None:
            self._idle_timer.cancel()
            self._idle_timer = None

        if self._stopped:
            raise RuntimeError(f"Agent {self.key} stopped")

        invoke = Invoke(messages=messages)
        self._worker_queue.put_nowait(invoke)

        if self._idle_timeout is not None:
            self._idle_timer = create_task(self._stop_after(self._idle_timeout))

        return invoke.future

    def _save(self, data_store: DataStore | None) -> Future[None]:
        if data_store is None:
            future = Future[None]()
            future.set_result(None)
            return future

        data = self._group_reasoner.get_serialized()
        return data_store.save("reasoner", data)

    async def _load(self, data_store: DataStore | None):
        if data_store is None:
            return

        try:
            data = await data_store.load("reasoner")
        except KeyError:
            pass  # reasoner wasn't persisted yet
        else:
            self._group_reasoner.set_serialized(data)

    async def _work(self):
        # TODO: handle connect errors
        async with narrow(self.data_store, self.owner) as data_store:
            # TODO: handle load errors
            await self._load(data_store)
            await self._loop(data_store)

    async def _loop(self, data_store: DataStore | None):
        while True:
            match await self._worker_queue.get():
                case Invoke(messages=messages, future=future):
                    updates = messages[self._group_reasoner.processed :]
                    message = updates[-1]

                    if message.sender != self.owner:
                        logger.warning(f"Last message in update batch is not from the owner: {message.sender}")

                    try:
                        if message.receiver == "system":
                            response = Response(
                                decision=Decision.DELEGATE,
                                query=message.content,
                                receiver=message.sender,
                            )
                        else:
                            response = await self._group_reasoner.run(updates)
                    except Exception as e:
                        future.set_exception(e)
                    else:
                        future.set_result(response)
                        self._save(data_store)  # background
                case Stop():
                    await self._save(data_store)
                    logger.debug(f"Group reasoner {self.key} stopped")
                    break


@dataclass
class Invoke:
    messages: list[Message]
    future: Future[Response] = field(default_factory=Future)


@dataclass
class Stop:
    pass
