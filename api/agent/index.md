## group_genie.agent.Agent

Bases: `ABC`

Abstract base class for creating custom agents.

Agents are the core processing units that handle delegated queries from group reasoners. They can be standalone agents or coordinator agents that orchestrate subagents in a hierarchical architecture.

Implementations must handle conversation state serialization (via get_serialized and set_serialized), MCP server lifecycle management (via mcp context manager), and query processing with tool approval callbacks.

State persistence is managed automatically by the framework and stored in JSON format. Persisted state is never transferred between different owners (users).

Example

```
class MyAgent(Agent):
    def __init__(self, system_prompt: str):
        self._history = []
        self._system_prompt = system_prompt

    def get_serialized(self):
        return {"history": self._history}

    def set_serialized(self, state):
        self._history = state["history"]

    @asynccontextmanager
    async def mcp(self):
        # Initialize MCP servers if needed
        yield self

    async def run(self, input: AgentInput, callback: ApprovalCallback) -> str:
        # Process query and return response
        return f"Processed: {input.query}"
```

### get_serialized

```
get_serialized() -> Any
```

Serialize agent state for persistence.

Returns conversation history and any other state needed to resume the agent after a restart. Called automatically by the framework before saving to DataStore.

Returns:

| Type  | Description                                                                   |
| ----- | ----------------------------------------------------------------------------- |
| `Any` | Serializable state (must be JSON-compatible). Implementation-specific format. |

### mcp

```
mcp() -> AbstractAsyncContextManager[Agent]
```

Context manager for MCP server lifecycle.

Manages the lifecycle of any MCP (Model Context Protocol) servers used by this agent. Connects to the agent's MCP servers on entering the context, and disconnects on exit.

Returns:

| Type                                 | Description                             |
| ------------------------------------ | --------------------------------------- |
| `AbstractAsyncContextManager[Agent]` | Async context manager that yields self. |

### run

```
run(input: AgentInput, callback: ApprovalCallback) -> str
```

Process a query and return a response.

Executes the agent's core logic to process the query. Must use the provided callback for any tool calls that require approval. Agent execution blocks until all approvals are granted or denied.

Parameters:

| Name       | Type               | Description                                                                                                              | Default    |
| ---------- | ------------------ | ------------------------------------------------------------------------------------------------------------------------ | ---------- |
| `input`    | `AgentInput`       | The query and associated data to process.                                                                                | *required* |
| `callback` | `ApprovalCallback` | Async callback for requesting approval of tool calls. Must be called for any tool execution that requires user approval. | *required* |

Returns:

| Type  | Description                       |
| ----- | --------------------------------- |
| `str` | The agent's response as a string. |

### set_serialized

```
set_serialized(state: Any)
```

Restore agent state from serialized data.

Reconstructs conversation history and internal state from previously serialized data. Called automatically by the framework after loading from DataStore.

Parameters:

| Name    | Type  | Description                                        | Default    |
| ------- | ----- | -------------------------------------------------- | ---------- |
| `state` | `Any` | Previously serialized state from get_serialized(). | *required* |

## group_genie.agent.AgentInput

```
AgentInput(query: str, attachments: list[Attachment] = list(), preferences: str | None = None)
```

Input data for agent execution.

Encapsulates all information needed for an agent to process a query, including the query text, any attached files, and user-specific preferences.

Attributes:

| Name          | Type               | Description                                                                                   |
| ------------- | ------------------ | --------------------------------------------------------------------------------------------- |
| `query`       | `str`              | The query text for the agent to process. Should be self-contained with all necessary context. |
| `attachments` | `list[Attachment]` | List of file attachments that accompany the query.                                            |
| `preferences` | \`str              | None\`                                                                                        |

Example

```
input = AgentInput(
    query="Analyze this report and summarize key findings",
    attachments=[Attachment(
        path="/tmp/report.pdf",
        name="Q3 Report",
        media_type="application/pdf"
    )],
    preferences="Concise responses, no emojis"
)
```

## group_genie.agent.AgentInfo

```
AgentInfo(name: str, description: str, emoji: str | None = None, idle_timeout: float | None = None)
```

Metadata about an agent.

Provides descriptive information about an agent for configuration purposes. Used by AgentFactory coordinator agents to learn about available subagents.

Attributes:

| Name           | Type    | Description                                                                                          |
| -------------- | ------- | ---------------------------------------------------------------------------------------------------- |
| `name`         | `str`   | Unique identifier for the agent (e.g., "search", "math", "system").                                  |
| `description`  | `str`   | Description of the agent's capabilities and purpose. Used by coordinator agents to select subagents. |
| `emoji`        | \`str   | None\`                                                                                               |
| `idle_timeout` | \`float | None\`                                                                                               |

Example

```
info = AgentInfo(
    name="search",
    description="Searches the web for current information",
    emoji="mag",
    idle_timeout=300.0
)
```

## group_genie.agent.AgentRunner

```
AgentRunner(key: str, name: str, owner: str, agent_factory: AgentFactory, data_store: DataStore | None = None, extra_tools: dict[str, AsyncTool] | None = None)
```

### run_subagent

```
run_subagent(query: str, subagent_name: str, subagent_instance: str | None = None, attachments: list[Attachment] = []) -> str
```

Runs a subagent and returns its response.

Subagents maintain state between runs. If you want to re-use a subagent instance, e.g. for a follow-up query or for an ongoing conversation with a subagent, set the `subagent_instance` to the instance id of a previously created subagent instance.

Pass attachments metadata to the subagent only if you think it is required by the subagent to process the query. If you have received attachments in a query message, and already extracted the required information from them, do not pass them to the subagent.

Parameters:

| Name                | Type               | Description                                       | Default                                                                                               |
| ------------------- | ------------------ | ------------------------------------------------- | ----------------------------------------------------------------------------------------------------- |
| `query`             | `str`              | The query to run the subagent with.               | *required*                                                                                            |
| `subagent_name`     | `str`              | The name of the subagent to run.                  | *required*                                                                                            |
| `subagent_instance` | \`str              | None\`                                            | The 8-digit hex instance id of the subagent to run. If null, a new subagent instance will be created. |
| `attachments`       | `list[Attachment]` | The attachments metadata to pass to the subagent. | `[]`                                                                                                  |

Returns:

| Type  | Description                                                                                                                                                                                                                |
| ----- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `str` | A JSON string containing the subagent name, 8-digit hex instance id, and response, e.g. { "subagent_name": subagent name, "subagent_instance": subagent 8-digit hex instance id, "subagent_response": subagent response, } |

Raises:

| Type         | Description                                 |
| ------------ | ------------------------------------------- |
| `ValueError` | If the name of the subagent does not exist. |

## group_genie.agent.Approval

```
Approval(sender: str, tool_name: str, tool_args: tuple, tool_kwargs: dict[str, Any], ftr: Future[bool])
```

Represents a tool call awaiting user approval.

Approval objects are emitted by Execution.stream() when an agent attempts to call a tool that requires approval. Applications must approve or deny the request by calling approve() or deny(), which unblocks the agent execution.

Attributes:

| Name          | Type             | Description                                                                                  |
| ------------- | ---------------- | -------------------------------------------------------------------------------------------- |
| `sender`      | `str`            | Identifier of the agent or subagent requesting approval (e.g., "system", "search:a1b2c3d4"). |
| `tool_name`   | `str`            | Name of the tool being called.                                                               |
| `tool_args`   | `tuple`          | Positional arguments for the tool call.                                                      |
| `tool_kwargs` | `dict[str, Any]` | Keyword arguments for the tool call.                                                         |
| `ftr`         | `Future[bool]`   | Internal future for communicating the approval decision.                                     |

Example

```
async for elem in execution.stream():
    match elem:
        case Approval() as approval:
            print(f"Tool call: {approval.call_repr()}")
            if is_safe(approval.tool_name):
                approval.approve()
            else:
                approval.deny()
```

### approve

```
approve()
```

Approve the tool call and unblock agent execution.

Allows the agent to proceed with the tool execution. The agent will receive the tool's result.

### approved

```
approved() -> bool
```

Wait for and return the approval decision.

Blocks until approve() or deny() is called, then returns the decision.

Returns:

| Type   | Description                        |
| ------ | ---------------------------------- |
| `bool` | True if approved, False if denied. |

### call_repr

```
call_repr() -> str
```

Get a string representation of the tool call.

### deny

```
deny()
```

Deny the tool call and unblock agent execution.

Prevents the tool from executing. The agent will receive a denial message (implementation-specific behavior).

## group_genie.agent.ApprovalCallback

```
ApprovalCallback = Callable[[str, dict[str, Any]], Awaitable[bool]]
```

Callback function type for requesting approval of tool calls.

When called, approval is requested and blocks until the application approves or denies the request. This callback is typically provided by ApprovalContext.approval_callback() and passed to Agent.run() to enable approval workflows.

Parameters:

| Name        | Type | Description                          | Default    |
| ----------- | ---- | ------------------------------------ | ---------- |
| `tool_name` |      | Name of the tool being called.       | *required* |
| `tool_args` |      | Keyword arguments for the tool call. | *required* |

Returns:

| Type | Description                                         |
| ---- | --------------------------------------------------- |
|      | True if the tool call is approved, False if denied. |

## group_genie.agent.ApprovalContext

```
ApprovalContext(queue: Queue[Approval], auto_approve: bool = False)
```

Context for managing the approval workflow.

ApprovalContext coordinates approval requests between agents and the application. It manages a queue of Approval objects that are emitted through Execution.stream() and provides callbacks for agents to request approval.

When auto_approve is enabled, all tool calls are automatically approved and Approval objects are not emitted through the stream.

Attributes:

| Name           | Type              | Description                                                                                  |
| -------------- | ----------------- | -------------------------------------------------------------------------------------------- |
| `queue`        | `Queue[Approval]` | Queue for Approval objects that need user attention.                                         |
| `auto_approve` | `bool`            | If True, automatically approve all tool calls without emitting Approvals. Defaults to False. |

Example

```
# Auto-approve mode (used by Execution.result())
context = ApprovalContext(queue=queue, auto_approve=True)

# Manual approval mode (used by Execution.stream())
context = ApprovalContext(queue=queue, auto_approve=False)
```

### approval

```
approval(sender: str, tool_name: str, tool_args: dict[str, Any]) -> bool
```

Request approval for a tool call.

If auto_approve is enabled, immediately returns True. Otherwise, creates an Approval object, adds it to the queue for the application to handle, and blocks until approve() or deny() is called.

Parameters:

| Name        | Type             | Description                                  | Default    |
| ----------- | ---------------- | -------------------------------------------- | ---------- |
| `sender`    | `str`            | Identifier of the agent requesting approval. | *required* |
| `tool_name` | `str`            | Name of the tool being called.               | *required* |
| `tool_args` | `dict[str, Any]` | Arguments for the tool call.                 | *required* |

Returns:

| Type   | Description                        |
| ------ | ---------------------------------- |
| `bool` | True if approved, False if denied. |

### approval_callback

```
approval_callback(sender: str) -> ApprovalCallback
```

Create an approval callback for a specific sender.

Parameters:

| Name     | Type  | Description                                  | Default    |
| -------- | ----- | -------------------------------------------- | ---------- |
| `sender` | `str` | Identifier of the agent requesting approval. | *required* |

Returns:

| Type               | Description                                          |
| ------------------ | ---------------------------------------------------- |
| `ApprovalCallback` | Callback function that can be passed to Agent.run(). |

## group_genie.agent.AgentFactory

```
AgentFactory(system_agent_factory: SingleAgentFactoryFn | MultiAgentFactoryFn, system_agent_info: AgentInfo | None = None, secrets_provider: SecretsProvider | None = None)
```

Factory for creating agent instances.

AgentFactory provides centralized agent creation and configuration. It supports two types of agents:

1. Standalone agents (SingleAgentFactoryFn): Simple agents that process queries independently without subagent orchestration.
1. Coordinator agents (MultiAgentFactoryFn): Complex agents that can run other agents as subagents, receiving information about available subagents and extra tools (like run_subagent).

The factory automatically provides user-specific secrets to agents and maintains agent metadata for introspection.

Example

```
# Standalone agent factory
def create_search_agent(secrets: dict[str, str]) -> Agent:
    return DefaultAgent(
        system_prompt="You are a search specialist",
        model="google-gla:google-gla:gemini-3-flash-preview",
        builtin_tools=[WebSearchTool()],
    )

# Coordinator agent factory
def create_coordinator(
    secrets: dict[str, str],
    extra_tools: dict[str, AsyncTool],
    agent_infos: list[AgentInfo]
) -> Agent:
    # Has access to run_subagent tool and info about subagents
    return DefaultAgent(
        system_prompt=f"Available subagents: {agent_infos}",
        tools=[extra_tools["run_subagent"]],
    )

# Create factory
factory = AgentFactory(
    system_agent_factory=create_coordinator,
    secrets_provider=my_secrets_provider,
)

# Register subagents
factory.add_agent_factory_fn(
    factory_fn=create_search_agent,
    info=AgentInfo(name="search", description="Web search specialist")
)
```

Initialize the agent factory.

Parameters:

| Name                   | Type                   | Description           | Default                                                                                                                                                                            |
| ---------------------- | ---------------------- | --------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `system_agent_factory` | \`SingleAgentFactoryFn | MultiAgentFactoryFn\` | Factory function for creating the main system agent. Can be either SingleAgentFactoryFn (takes only secrets) or MultiAgentFactoryFn (takes secrets, extra_tools, and agent_infos). |
| `system_agent_info`    | \`AgentInfo            | None\`                | Optional metadata for the system agent. Defaults to a basic AgentInfo with name="system" and 600s idle timeout.                                                                    |
| `secrets_provider`     | \`SecretsProvider      | None\`                | Optional provider for user-specific secrets (e.g., API keys).                                                                                                                      |

### add_agent_factory_fn

```
add_agent_factory_fn(factory_fn: SingleAgentFactoryFn | MultiAgentFactoryFn, info: AgentInfo)
```

Register a new agent factory function.

Adds a factory function that can create agents of a specific type. The agent can then be used as a subagent by coordinator agents.

Parameters:

| Name         | Type                   | Description                                                       | Default                                                                                             |
| ------------ | ---------------------- | ----------------------------------------------------------------- | --------------------------------------------------------------------------------------------------- |
| `factory_fn` | \`SingleAgentFactoryFn | MultiAgentFactoryFn\`                                             | Factory function for creating the agent. Can be either SingleAgentFactoryFn or MultiAgentFactoryFn. |
| `info`       | `AgentInfo`            | Metadata about the agent (name, description, idle timeout, etc.). | *required*                                                                                          |

### agent_info

```
agent_info(name: str) -> AgentInfo
```

Get metadata for a specific agent by name.

Parameters:

| Name   | Type  | Description        | Default    |
| ------ | ----- | ------------------ | ---------- |
| `name` | `str` | Name of the agent. | *required* |

Returns:

| Type        | Description                        |
| ----------- | ---------------------------------- |
| `AgentInfo` | AgentInfo for the specified agent. |

### agent_infos

```
agent_infos(exclude: str | None = None) -> list[AgentInfo]
```

Get metadata for all registered agents.

Parameters:

| Name      | Type  | Description | Default                                                                                                                    |
| --------- | ----- | ----------- | -------------------------------------------------------------------------------------------------------------------------- |
| `exclude` | \`str | None\`      | Optional agent name to exclude from the results (e.g., exclude the coordinator agent itself when providing subagent info). |

Returns:

| Type              | Description                                                          |
| ----------------- | -------------------------------------------------------------------- |
| `list[AgentInfo]` | List of AgentInfo for all registered agents except the excluded one. |

### create_agent

```
create_agent(name: str, owner: str, extra_tools: dict[str, AsyncTool] | None = None) -> Agent
```

Create an agent by name for a specific owner.

Looks up the registered factory function for the given name and creates an agent instance.

Parameters:

| Name          | Type                   | Description                                                                               | Default                                                                                      |
| ------------- | ---------------------- | ----------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------- |
| `name`        | `str`                  | Name of the agent to create (must be registered via add_agent_factory_fn or be "system"). | *required*                                                                                   |
| `owner`       | `str`                  | User ID of the agent owner.                                                               | *required*                                                                                   |
| `extra_tools` | \`dict[str, AsyncTool] | None\`                                                                                    | Optional additional tools to provide to the agent. Only used for MultiAgentFactoryFn agents. |

Returns:

| Type    | Description                                    |
| ------- | ---------------------------------------------- |
| `Agent` | A new Agent instance configured for the owner. |

### create_system_agent

```
create_system_agent(owner: str, extra_tools: dict[str, AsyncTool]) -> Agent
```

Create the main system agent for a specific owner.

Parameters:

| Name          | Type                   | Description                                                                               | Default    |
| ------------- | ---------------------- | ----------------------------------------------------------------------------------------- | ---------- |
| `owner`       | `str`                  | User ID of the agent owner.                                                               | *required* |
| `extra_tools` | `dict[str, AsyncTool]` | Additional tools provided by the framework (e.g., run_subagent, get_group_chat_messages). | *required* |

Returns:

| Type    | Description                  |
| ------- | ---------------------------- |
| `Agent` | A new system Agent instance. |

### system_agent_info

```
system_agent_info() -> AgentInfo
```

Get metadata for the system agent.

Returns:

| Type        | Description                     |
| ----------- | ------------------------------- |
| `AgentInfo` | AgentInfo for the system agent. |

## group_genie.agent.SingleAgentFactoryFn

```
SingleAgentFactoryFn = Callable[[dict[str, str]], Agent]
```

Factory function signature for creating standalone agents.

Creates agents that process queries independently without orchestrating subagents. These are "leaf" agents in an agent hierarchy.

Parameters:

| Name      | Type             | Description                                                                                                                              | Default    |
| --------- | ---------------- | ---------------------------------------------------------------------------------------------------------------------------------------- | ---------- |
| `secrets` | `dict[str, str]` | User-specific credentials (e.g., API keys) retrieved from a SecretsProvider. Common keys include "GOOGLE_API_KEY", "BRAVE_API_KEY", etc. | *required* |

Returns:

| Type | Description                                           |
| ---- | ----------------------------------------------------- |
|      | A configured Agent instance ready to process queries. |

Example

```
def create_search_agent(secrets: dict[str, str]) -> Agent:
    model = GoogleModel(
        "gemini-3-flash-preview",
        provider=GoogleProvider(api_key=secrets.get("GOOGLE_API_KEY", "")),
    )
    return DefaultAgent(
        system_prompt="You are a web search specialist",
        model=model,
        builtin_tools=[WebSearchTool()],
    )
```

## group_genie.agent.MultiAgentFactoryFn

```
MultiAgentFactoryFn = Callable[[dict[str, str], dict[str, AsyncTool], list[AgentInfo]], Agent]
```

Factory function signature for creating coordinator agents.

Creates agents that can orchestrate other agents as subagents. These coordinator agents receive information about available subagents and framework-provided tools like `run_subagent` to delegate work.

Parameters:

| Name          | Type                   | Description                                                                                                                                                                       | Default    |
| ------------- | ---------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------- |
| `secrets`     | `dict[str, str]`       | User-specific credentials (e.g., API keys) retrieved from a SecretsProvider.                                                                                                      | *required* |
| `extra_tools` | `dict[str, AsyncTool]` | Framework-provided tools. Always includes run_subagent for delegating to subagents. May include get_group_chat_messages and other tools depending on the framework configuration. | *required* |
| `agent_infos` | `list[AgentInfo]`      | Metadata about all other registered agents (excluding the coordinator itself). Used to inform the coordinator what subagents are available. Each entry is an AgentInfo instance.  | *required* |

Returns:

| Type | Description                                                     |
| ---- | --------------------------------------------------------------- |
|      | A configured Agent instance capable of orchestrating subagents. |

Example

```
def create_coordinator(
    secrets: dict[str, str],
    extra_tools: dict[str, AsyncTool],
    agent_infos: list[AgentInfo],
) -> Agent:
    system_prompt = f"You can delegate to: {[a.name for a in agent_infos]}"
    return DefaultAgent(
        system_prompt=system_prompt,
        model="google-gla:gemini-3-flash-preview",
        tools=[extra_tools["run_subagent"]],
    )
```

## group_genie.agent.Decision

```
Decision = Decision
```
