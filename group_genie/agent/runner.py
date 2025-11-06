import json
import logging
from asyncio import CancelledError, Future, Queue, Task, create_task, sleep
from contextvars import ContextVar
from dataclasses import dataclass, field
from typing import AsyncIterator

from group_genie.agent.approval import Approval, ApprovalContext
from group_genie.agent.base import Agent, AgentInput
from group_genie.agent.factory import AgentFactory, AsyncTool
from group_genie.datastore import DataStore, narrow
from group_genie.message import Attachment
from group_genie.utils import identifier

logger = logging.getLogger(__name__)


class AgentRunner:
    def __init__(
        self,
        key: str,
        name: str,
        owner: str,
        agent_factory: AgentFactory,
        data_store: DataStore | None = None,
        extra_tools: dict[str, AsyncTool] | None = None,
    ):
        self.key = key
        self.name = name
        self.owner = owner
        self.agent_factory = agent_factory
        self.data_store = data_store

        extra_tools = extra_tools or {}
        extra_tools |= {"run_subagent": self.run_subagent}

        self._agent: Agent = agent_factory.create_agent(name=name, owner=owner, extra_tools=extra_tools)
        self._idle_timeout = agent_factory.agent_info(name=name).idle_timeout
        self._idle_timer: Task | None = None

        self._subagent_runners: dict[str, AgentRunner] = {}
        self._approval_context = ContextVar[ApprovalContext]("approval_context")
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

    def _stop_subagents(self):
        for runner in self._subagent_runners.values():
            runner.stop()

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

    async def _join_subagents(self):
        for runner in self._subagent_runners.values():
            await runner.join()

    def invoke(self, input: AgentInput, context: ApprovalContext) -> Future[str]:
        if self._idle_timer is not None:
            self._idle_timer.cancel()
            self._idle_timer = None

        if self._stopped:
            raise RuntimeError(f"Agent {self.key} stopped")

        invoke = Invoke(input=input, context=context)
        self._worker_queue.put_nowait(invoke)

        if self._idle_timeout is not None:
            self._idle_timer = create_task(self._stop_after(self._idle_timeout))

        return invoke.future

    async def run(self, input: AgentInput) -> AsyncIterator[Approval | str]:
        queue: Queue[Approval | Future[str]] = Queue()
        context = ApprovalContext(queue=queue)  # type: ignore

        def callback(result: Future[str]):
            queue.put_nowait(result)

        future = self.invoke(input, context)
        future.add_done_callback(callback)

        while True:
            elem = await queue.get()
            match elem:
                case Approval():
                    yield elem
                case Future():
                    yield elem.result()
                    break

    async def run_subagent(
        self,
        query: str,
        subagent_name: str,
        subagent_instance: str | None = None,
        attachments: list[Attachment] = [],
    ) -> str:
        """Runs a subagent and returns its response.

        Subagents maintain state between runs. If you want to re-use a subagent instance,
        e.g. for a follow-up query or for an ongoing conversation with a subagent, set the
        `subagent_instance` to the instance id of a previously created subagent instance.

        Pass attachments metadata to the subagent only if you think it is required by the
        subagent to process the query. If you have received attachments in a query message,
        and already extracted the required information from them, do not pass them to the
        subagent.

        Args:
            query: The query to run the subagent with.
            subagent_name: The name of the subagent to run.
            subagent_instance: The 8-digit hex instance id of the subagent to run. If `null`, a new subagent instance will be created.
            attachments: The attachments metadata to pass to the subagent.

        Returns:
            A JSON string containing the subagent name, 8-digit hex instance id, and response, e.g.
                ```json
                {
                    "subagent_name": subagent name,
                        "subagent_instance": subagent 8-digit hex instance id,
                        "subagent_response": subagent response,
                }
                ```

        Raises:
            ValueError: If the name of the subagent does not exist.
        """
        if subagent_instance is None:
            subagent_instance = identifier()[:8]

        key = f"{subagent_name}:{subagent_instance}"

        if runner := self._subagent_runners.get(key):
            if runner.stopped:
                self._subagent_runners.pop(key)
                await runner.join()

        if key not in self._subagent_runners:
            runner = AgentRunner(
                key=key,
                name=subagent_name,
                owner=self.owner,
                agent_factory=self.agent_factory,
                data_store=self.data_store,
            )
            self._subagent_runners[key] = runner

        runner = self._subagent_runners[key]

        try:
            input = AgentInput(
                query=query,
                attachments=attachments,
            )
            response = await runner.invoke(
                input=input,
                context=self._approval_context.get(),
            )
        except Exception as e:
            logger.exception("Subagent error")
            response = f"Subagent ({subagent_name}) error: {e}"

        result = {
            "subagent_name": subagent_name,
            "subagent_instance": subagent_instance,
            "subagent_response": response,
        }

        result_json = json.dumps(result, indent=2)
        logger.debug(result_json)
        return result_json

    def _save(self, data_store: DataStore | None) -> Future[None]:
        if data_store is None:
            future = Future[None]()
            future.set_result(None)
            return future

        system_agent_data = {"agent": self._agent.get_serialized()}
        return data_store.save(self.key, system_agent_data)

    async def _load(self, data_store: DataStore | None):
        if data_store is None:
            return

        try:
            system_agent_data = await data_store.load(self.key)
        except KeyError:
            pass
        else:
            self._agent.set_serialized(system_agent_data["agent"])

    async def _work(self):
        # TODO: handle connect errors
        async with self._agent.mcp():
            async with narrow(self.data_store, self.owner) as data_store:
                # TODO: handle load errors
                await self._load(data_store)
                await self._loop(data_store)

    async def _loop(self, data_store: DataStore | None):
        while True:
            match await self._worker_queue.get():
                case Invoke(input=input, context=context, future=future):
                    self._approval_context.set(context)
                    try:
                        callback = context.approval_callback(sender=self.key)
                        response = await self._agent.run(input, callback)
                    except Exception as e:
                        future.set_exception(e)
                    else:
                        future.set_result(response)
                        self._save(data_store)  # background
                case Stop():
                    await self._save(data_store)
                    self._stop_subagents()
                    await self._join_subagents()
                    logger.debug(f"Agent {self.key} stopped")
                    break


@dataclass
class Invoke:
    input: AgentInput
    context: ApprovalContext
    future: Future[str] = field(default_factory=Future)


@dataclass
class Stop:
    pass
