import logging
from asyncio import Future, Queue, create_task
from dataclasses import asdict, dataclass, field
from typing import AsyncIterator, Callable

from group_sense import Decision

from group_genie.agent import AgentFactory, Approval, ApprovalContext
from group_genie.agent.base import AgentInput
from group_genie.agent.runner import AgentRunner
from group_genie.datastore import DataStore, narrow
from group_genie.message import Attachment, Message
from group_genie.preferences import PreferencesSource
from group_genie.reasoner import GroupReasonerFactory
from group_genie.reasoner.runner import GroupReasonerRunner

logger = logging.getLogger(__name__)


class GroupSession:
    """Main entry point for managing group chat sessions with AI agents.

    [`GroupSession`][group_genie.session.GroupSession] orchestrates the flow of
    messages through group reasoners and agents, managing their lifecycle and state
    persistence. It maintains message ordering, handles concurrent processing for
    different users, and provides graceful shutdown.

    Messages are stored internally in the order of
    [`handle()`][group_genie.session.GroupSession.handle] calls and processed
    concurrently for different senders. Messages from the same sender are always
    processed sequentially.

    Persisted session state (messages and agent/reasoner state) is automatically
    loaded during initialization if a [`DataStore`][group_genie.datastore.DataStore]
    is provided.

    Example:
        ```python
        session = GroupSession(
            id="session123",
            group_reasoner_factory=create_group_reasoner_factory(),
            agent_factory=create_agent_factory(),
            data_store=DataStore(root_path=Path(".data/sessions/session123")),
        )

        # Handle incoming message
        execution = session.handle(
            Message(content="What's the weather in Vienna?", sender="alice")
        )

        # Process execution
        async for elem in execution.stream():
            match elem:
                case Decision.DELEGATE:
                    print("Query delegated to agent")
                case Approval() as approval:
                    approval.approve()
                case Message() as response:
                    print(f"Response: {response.content}")

        # Gracefully stop session
        session.stop()
        await session.join()
        ```
    """

    def __init__(
        self,
        id: str,
        group_reasoner_factory: GroupReasonerFactory,
        agent_factory: AgentFactory,
        data_store: DataStore | None = None,
        preferences_source: PreferencesSource | None = None,
    ):
        """Initialize a new group chat session.

        Args:
            id: Unique identifier for this session. Used as the root key for persisted
                state in the [`DataStore`][group_genie.datastore.DataStore].
            group_reasoner_factory: Factory for creating group reasoner instances that
                decide when to delegate messages to agents.
            agent_factory: Factory for creating agent instances that process delegated
                queries.
            data_store: Optional persistent storage for session messages and agent state.
                If provided, session state is automatically loaded on initialization and
                saved after each message. Experimental feature not suitable for production.
            preferences_source: Optional source for user-specific preferences that are
                included in agent prompts.
        """
        self.id = id
        self.group_reasoner_factory = group_reasoner_factory
        self.agent_factory = agent_factory
        self.data_store = data_store
        self.preferences_source = preferences_source

        self._group_reasoner_runners: dict[str, GroupReasonerRunner] = {}
        self._system_agent_runners: dict[str, AgentRunner] = {}
        self._messages: list[Message] = []

        self._worker_queue: Queue[Invoke | RequestIds | Stop] = Queue()
        self._worker_task = create_task(self._work())
        self._stopped = False

    @property
    def stopped(self) -> bool:
        return self._stopped

    def stop(self):
        """Request graceful shutdown of the session.

        Allows currently processing messages to complete before stopping all group
        reasoners and agents. Call join() after stop() to wait for shutdown completion.
        """
        if not self.stopped:
            self._stopped = True
            self._worker_queue.put_nowait(Stop())

    async def join(self):
        """Wait for the session to complete shutdown.

        Blocks until all internal workers, agents, and reasoners have stopped. Must be
        called after stop() to ensure proper cleanup.
        """
        await self._worker_task

    def _stop_group_reasoners(self):
        for runner in self._group_reasoner_runners.values():
            runner.stop()

    async def _join_group_reasoners(self):
        for runner in self._group_reasoner_runners.values():
            await runner.join()

    def _stop_system_agents(self):
        for runner in self._system_agent_runners.values():
            runner.stop()

    async def _join_system_agents(self):
        for runner in self._system_agent_runners.values():
            await runner.join()

    def request_ids(self) -> Future[set[str]]:
        """Retrieve all request IDs from messages in this session.

        Returns:
            A Future that resolves to a set of request IDs from all messages that have
                been processed by this session. Only includes messages with non-None
                request_id values.
        """
        _request_ids = RequestIds()
        self._worker_queue.put_nowait(_request_ids)
        return _request_ids.future

    def handle(self, message: Message) -> "Execution":
        """Process an incoming group chat message.

        Adds the message to the session's message history and initiates processing
        through group reasoners and agents. Returns immediately with an
        [`Execution`][group_genie.session.Execution] object that can be used to
        retrieve results.

        Messages are stored in the order
        [`handle()`][group_genie.session.GroupSession.handle] is called. For
        different senders, messages are processed concurrently. For the same sender,
        messages are processed sequentially to maintain conversation coherence.

        Args:
            message: The message to process.

        Returns:
            An [`Execution`][group_genie.session.Execution] object that provides
                access to the processing stream and final result.
        """
        execution = Execution(preferences_source=self.preferences_source)
        invoke = Invoke(message=message, execution=execution)
        self._worker_queue.put_nowait(invoke)
        return execution

    def _save(self, data_store: DataStore | None) -> Future[None]:
        if data_store is None:
            future = Future[None]()
            future.set_result(None)
            return future

        data = {"messages": [asdict(message) for message in self._messages]}
        return data_store.save("session", data)

    @staticmethod
    async def load_messages(data_store: DataStore) -> list[Message] | None:
        """Load persisted messages from a data store.

        Utility method for accessing session messages without creating a full
        [`GroupSession`][group_genie.session.GroupSession] instance. Automatically
        called during session initialization.

        Args:
            data_store: [`DataStore`][group_genie.datastore.DataStore] containing the
                session data to load.

        Returns:
            List of messages if the session exists in the data store, None otherwise.
        """
        try:
            data = await data_store.load("session")
        except KeyError:
            return None
        else:
            return [Message.deserialize(message) for message in data["messages"]]

    async def _load(self, data_store: DataStore | None):
        if data_store is None:
            return

        if messages := await self.load_messages(data_store):
            self._messages = messages

    def _update(self, message: Message, data_store: DataStore | None):
        self._messages.append(message)

        if data_store is not None:
            self._save(data_store)  # background (preserves order)

    async def _get_group_reasoner_runner(
        self,
        owner: str,
        session_store: DataStore | None = None,
    ) -> GroupReasonerRunner:
        if runner := self._group_reasoner_runners.get(owner):
            if runner.stopped:
                self._group_reasoner_runners.pop(owner)
                await runner.join()

        if owner not in self._group_reasoner_runners:
            runner = GroupReasonerRunner(
                key=f"reasoner:{owner}",
                owner=owner,
                group_reasoner_factory=self.group_reasoner_factory,
                data_store=session_store,
            )
            self._group_reasoner_runners[owner] = runner

        return self._group_reasoner_runners[owner]

    async def _get_system_agent_runner(
        self,
        owner: str,
        session_store: DataStore | None = None,
    ) -> AgentRunner:
        if runner := self._system_agent_runners.get(owner):
            if runner.stopped:
                self._system_agent_runners.pop(owner)
                await runner.join()

        if owner not in self._system_agent_runners:
            runner = AgentRunner(
                key="system",
                name="system",
                owner=owner,
                agent_factory=self.agent_factory,
                data_store=session_store,
                extra_tools={"get_group_chat_messages": self.get_group_chat_messages},
            )
            self._system_agent_runners[owner] = runner

        return self._system_agent_runners[owner]

    async def get_group_chat_messages(self) -> str:
        """Returns the group chat messages as a JSON string."""
        from group_sense.reasoner.prompt import format_update_messages

        from group_genie.agent.provider.pydantic_ai.group import convert_messages

        # Referenced threads are currently not included in the result ...
        return format_update_messages(convert_messages(self._messages), start_seq_nr=0)

    async def _work(self):
        async with narrow(self.data_store, self.id) as data_store:
            # TODO: handle load errors
            await self._load(data_store)
            await self._loop(data_store)

    async def _loop(self, data_store: DataStore | None):
        while True:
            match await self._worker_queue.get():
                case Invoke(message=message, execution=execution):
                    # store request message in group session
                    self._update(message, data_store=data_store)
                    # snapshot messages for asynchronous processing
                    messages_snapshot = self._messages.copy()

                    reasoner_runner = await self._get_group_reasoner_runner(
                        owner=message.sender,
                        session_store=data_store,
                    )
                    agent_runner = await self._get_system_agent_runner(
                        owner=message.sender,
                        session_store=data_store,
                    )

                    def callback(message: Message):
                        # store response message in group session
                        self._update(message, data_store=data_store)

                    exchange = Exchange(
                        group_reasoner_runner=reasoner_runner,
                        system_agent_runner=agent_runner,
                        messages=messages_snapshot,
                        callback=callback,
                    )
                    execution._unblock(exchange)
                case RequestIds(future=future):
                    request_ids = {message.request_id for message in self._messages if message.request_id}
                    future.set_result(request_ids)
                case Stop():
                    await self._save(data_store)
                    self._stop_group_reasoners()
                    self._stop_system_agents()
                    await self._join_group_reasoners()
                    await self._join_system_agents()
                    logger.debug(f"Group session {self.id} stopped")
                    break


class Execution:
    """Represents the asynchronous processing of a message through the system.

    [`Execution`][group_genie.session.Execution] provides access to the stream of
    events (decision, approvals, and responses) generated while processing a message.
    It allows applications to monitor progress, handle approval requests, and retrieve
    the final result.

    The execution stream follows a guaranteed order:

    1. One [`Decision`][group_genie.agent.Decision] (IGNORE or DELEGATE)
    2. Zero or more [`Approval`][group_genie.agent.approval.Approval] requests (only
       if DELEGATE and tools/subagents are called)
    3. One [`Message`][group_genie.message.Message] (only if DELEGATE, containing the
       agent's response)

    Multiple calls to [`stream()`][group_genie.session.Execution.stream] are safe and
    will return the cached result after the first complete iteration.

    Example:
        ```python
        execution = session.handle(message)

        # Stream events
        async for elem in execution.stream():
            match elem:
                case Decision.IGNORE:
                    print("Message ignored by reasoner")
                case Decision.DELEGATE:
                    print("Message delegated to agent")
                case Approval() as approval:
                    print(f"Tool call requires approval: {approval}")
                    approval.approve()
                case Message() as response:
                    print(f"Agent response: {response.content}")

        # Or get result directly (auto-approves all tool calls)
        result = await execution.result()
        if result:
            print(f"Response: {result.content}")
        ```
    """

    def __init__(self, preferences_source: PreferencesSource | None = None):
        self._preferences_source = preferences_source
        self._result: Message | None = None
        self._exchange: Future[Exchange] = Future()

    async def result(self) -> Message | None:
        """Retrieve the final message result, automatically approving all tool calls.

        Convenience method that streams through all events, auto-approving any
        [`Approval`][group_genie.agent.approval.Approval] requests, and returns the
        final [`Message`][group_genie.message.Message]. Useful when manual approval
        handling is not needed.

        Returns:
            The agent's response [`Message`][group_genie.message.Message] if the
                reasoner delegated, None if the reasoner ignored the message.
        """
        async for elem in self.stream():
            match elem:
                case Decision.IGNORE:
                    return None
                case Approval():
                    elem.approve()
                case Message():
                    return elem

        return None

    async def stream(self) -> AsyncIterator[Decision | Approval | Message]:
        """Stream execution events as they occur.

        Yields events in guaranteed order:

        1. One [`Decision`][group_genie.agent.Decision] (IGNORE or DELEGATE)
        2. Zero or more [`Approval`][group_genie.agent.approval.Approval] requests
           (if DELEGATE and tools are called)
        3. One [`Message`][group_genie.message.Message] (if DELEGATE, containing the
           final response)

        Agent execution blocks on [`Approval`][group_genie.agent.approval.Approval]
        requests until they are approved or denied. Applications must handle all
        emitted Approvals by calling
        [`approve()`][group_genie.agent.approval.Approval.approve] or
        [`deny()`][group_genie.agent.approval.Approval.deny].

        If auto_approve is enabled in the
        [`ApprovalContext`][group_genie.agent.approval.ApprovalContext],
        [`Approval`][group_genie.agent.approval.Approval] events are not emitted and
        all tool calls are automatically approved.

        Can be called multiple times. After the first complete iteration, cached
        results are returned immediately.

        Yields:
            [`Decision`][group_genie.agent.Decision],
            [`Approval`][group_genie.agent.approval.Approval], or
            [`Message`][group_genie.message.Message] objects representing execution
            progress.
        """
        if self._result is not None:
            yield self._result
            return

        exchange = await self._exchange

        queue: Queue[Decision | Approval | Future[str]] = Queue()
        context = ApprovalContext(queue=queue)  # type: ignore

        try:
            response = await exchange.group_reasoner_runner.invoke(exchange.messages)
        except Exception:
            logger.exception("Reasoner error")
            queue.put_nowait(Decision.IGNORE)
        else:
            queue.put_nowait(response.decision)

            if response.decision == Decision.DELEGATE:
                query = response.query or ""
                logger.debug(f"Delegate query: {query}")

                attachments: list[Attachment] = []

                for message in exchange.messages:
                    attachments.extend(message.attachments)
                logger.debug(f"Delegate attachments: {[attachment.name for attachment in attachments]}")

                if response.receiver is None:
                    preferences = None
                else:
                    preferences = await self._preferences(response.receiver)

                agent_input = AgentInput(
                    query=query,
                    attachments=attachments,
                    preferences=preferences,
                )

                def callback(response: Future[str]):
                    queue.put_nowait(response)

                future = exchange.system_agent_runner.invoke(agent_input, context)
                future.add_done_callback(callback)

        while elem := await queue.get():
            match elem:
                case Decision.IGNORE:
                    yield elem
                    break
                case Decision():
                    yield elem
                case Approval():
                    yield elem
                case Future():
                    try:
                        message = Message(
                            content=elem.result(),
                            sender="system",
                            receiver=response.receiver,
                            request_id=exchange.message.request_id,
                        )
                    except Exception as e:
                        logger.exception("System agent error")
                        message = Message(
                            content=f"System agent error: {e}",
                            sender="system",
                            receiver=exchange.message.sender,
                            request_id=exchange.message.request_id,
                        )

                    self._result = message
                    exchange.callback(message)
                    yield message
                    break

    async def _preferences(self, receiver: str) -> str | None:
        if self._preferences_source is None:
            return None
        return await self._preferences_source.get_preferences(receiver)

    def _unblock(self, exchange: "Exchange"):
        self._exchange.set_result(exchange)


@dataclass
class Exchange:
    group_reasoner_runner: GroupReasonerRunner
    system_agent_runner: AgentRunner
    messages: list[Message]
    callback: Callable[[Message], None]

    @property
    def message(self):
        return self.messages[-1]


@dataclass
class Invoke:
    message: Message
    execution: Execution


@dataclass
class RequestIds:
    future: Future[set[str]] = field(default_factory=Future)


@dataclass
class Stop:
    pass
