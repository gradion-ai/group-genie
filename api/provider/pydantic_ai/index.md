## group_genie.agent.provider.pydantic_ai.DefaultAgent

```
DefaultAgent(system_prompt: str, model: str | Model, model_settings: ModelSettings | None = None, toolsets: list[AbstractToolset] = [], tools: list[AsyncTool] = [], builtin_tools: list[AbstractBuiltinTool] = [])
```

Bases: `Stateful`, `Agent`

Default `Agent` implementation using [pydantic-ai](https://ai.pydantic.dev/).

DefaultAgent is a ready-to-use Agent implementation built on pydantic-ai. It supports conversation state management, tool calling with approval workflows, and MCP server lifecycle management.

The agent can be configured with:

- Custom system prompts
- Any pydantic-ai compatible model
- Toolsets (collections of tools, including MCP servers)
- Individual tools (async functions)
- Built-in tools (like `WebSearchTool`)

For model and tool configuration details, consult the pydantic-ai documentation.

Example

```
from pydantic_ai.builtin_tools import WebSearchTool
from pydantic_ai.models.google import GoogleModelSettings

agent = DefaultAgent(
    system_prompt="You are a helpful assistant",
    model="gemini-2.5-flash",
    model_settings=GoogleModelSettings(
        google_thinking_config={
            "thinking_budget": -1,
            "include_thoughts": True,
        }
    ),
    builtin_tools=[WebSearchTool()],
)
```

Initialize a pydantic-ai based agent.

Parameters:

| Name             | Type                        | Description                                                                                     | Default                                                                                                    |
| ---------------- | --------------------------- | ----------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------- |
| `system_prompt`  | `str`                       | System prompt that defines the agent's behavior and personality.                                | *required*                                                                                                 |
| `model`          | \`str                       | Model\`                                                                                         | Model identifier or pydantic-ai Model instance. Can be any model supported by pydantic-ai.                 |
| `model_settings` | \`ModelSettings             | None\`                                                                                          | Optional model-specific settings. See pydantic-ai documentation for available settings per model provider. |
| `toolsets`       | `list[AbstractToolset]`     | List of tool collections (including MCP servers). Use this for organized sets of related tools. | `[]`                                                                                                       |
| `tools`          | `list[AsyncTool]`           | List of individual async functions to make available as tools.                                  | `[]`                                                                                                       |
| `builtin_tools`  | `list[AbstractBuiltinTool]` | List of pydantic-ai built-in tools (e.g., WebSearchTool).                                       | `[]`                                                                                                       |

### mcp

```
mcp()
```

Manage MCP server lifecycle for this agent.

Delegates MCP server management to the underlying pydantic-ai agent, which handles connection and cleanup of any MCP servers included in toolsets.

Yields:

| Type | Description          |
| ---- | -------------------- |
|      | This agent instance. |

### run

```
run(input: AgentInput, callback: ApprovalCallback) -> str
```

Process a query and return a response.

Runs the pydantic-ai agent with the provided query, attachments, and preferences. Tool calls are intercepted and routed through the approval callback, allowing the application to approve or deny tool execution.

Parameters:

| Name       | Type               | Description                                                                           | Default    |
| ---------- | ------------------ | ------------------------------------------------------------------------------------- | ---------- |
| `input`    | `AgentInput`       | Query, attachments, and preferences to process.                                       | *required* |
| `callback` | `ApprovalCallback` | Approval callback for tool calls. Called for each tool execution to request approval. | *required* |

Returns:

| Type  | Description                       |
| ----- | --------------------------------- |
| `str` | The agent's response as a string. |

## group_genie.agent.provider.pydantic_ai.DefaultGroupReasoner

```
DefaultGroupReasoner(system_prompt: str, model: str | Model | None = None, model_settings: ModelSettings | None = None)
```

Bases: `GroupReasoner`

Default group reasoner implementation using [group-sense](https://gradion-ai.github.io/group-sense/).

DefaultGroupReasoner wraps the group-sense library's DefaultGroupReasoner, adapting Group Genie's Message types to group-sense's message format.

The reasoner analyzes group chat messages according to the system prompt's engagement criteria and decides whether to delegate queries to agents.

For model and configuration details, consult the group-sense and pydantic-ai documentation. Tested with gemini-2.5-flash but compatible with any pydantic-ai supported model.

Example

```
reasoner = DefaultGroupReasoner(
    system_prompt='''
        You are monitoring a group chat for {owner}.
        Delegate when {owner} asks questions.
        Generate self-contained queries.
    '''.format(owner="alice"),
    model="gemini-2.5-flash",
)

# Process messages
response = await reasoner.run([
    Message(content="What's the weather?", sender="alice")
])

if response.decision == Decision.DELEGATE:
    print(f"Query: {response.query}")
```

Initialize a group-sense based reasoner.

Parameters:

| Name             | Type            | Description                                                                                                                                      | Default                                                                                                    |
| ---------------- | --------------- | ------------------------------------------------------------------------------------------------------------------------------------------------ | ---------------------------------------------------------------------------------------------------------- |
| `system_prompt`  | `str`           | System prompt defining the engagement criteria. Should describe when to delegate messages and how to transform them into self-contained queries. | *required*                                                                                                 |
| `model`          | \`str           | Model                                                                                                                                            | None\`                                                                                                     |
| `model_settings` | \`ModelSettings | None\`                                                                                                                                           | Optional model-specific settings. See pydantic-ai documentation for available settings per model provider. |

### run

```
run(updates: list[Message]) -> Response
```

Analyze message updates and decide whether to delegate.

Converts Group Genie messages to group-sense format and delegates to the underlying group-sense reasoner for processing.

Parameters:

| Name      | Type            | Description                      | Default    |
| --------- | --------------- | -------------------------------- | ---------- |
| `updates` | `list[Message]` | List of new messages to analyze. | *required* |

Returns:

| Type       | Description                                                          |
| ---------- | -------------------------------------------------------------------- |
| `Response` | Response from group-sense with decision and optional query/receiver. |

## group_genie.agent.provider.pydantic_ai.ToolFilter

```
ToolFilter(included: list[str] | None = None, excluded: list[str] | None = None)
```

Filter function for selectively exposing tools to agents based on whitelists and blacklists.

This class is designed to be passed to pydantic-ai's `FilteredToolset` or the `filtered()` method on any toolset. It implements a callable filter that receives the run context and tool definition for each tool and returns whether the tool should be available.

The filter operates as follows:

- If `included` is specified, only tools in the whitelist are allowed
- If `excluded` is specified, tools in the blacklist are rejected
- If both are specified, a tool must be in `included` and not in `excluded`
- If neither is specified, all tools are allowed

Example

```
 filter = ToolFilter(included=["read_file", "write_file"])
 filtered_toolset = my_toolset.filtered(filter)
```

Attributes:

| Name       | Type        | Description |
| ---------- | ----------- | ----------- |
| `included` | \`list[str] | None\`      |
| `excluded` | \`list[str] | None\`      |
