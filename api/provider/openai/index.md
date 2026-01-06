## group_genie.agent.provider.openai.DefaultAgent

```
DefaultAgent(system_prompt: str, model: str | Model, model_settings: ModelSettings, tools: list[Tool] = [], mcp_servers: list[Any] = [], **kwargs: Any)
```

Bases: `Agent`

Default Agent implementation using the [OpenAI Agents SDK](https://openai.github.io/openai-agents-python/).

DefaultAgent is a ready-to-use Agent implementation built on the OpenAI Agents SDK. It supports conversation state management, tool calling with approval workflows, and MCP server lifecycle management.

The agent can be configured with:

- Custom system prompts (instructions)
- Any OpenAI Agents SDK compatible model
- Individual tools (function tools)
- MCP servers for external integrations

For model and tool configuration details, consult the [OpenAI Agents SDK documentation](https://openai.github.io/openai-agents-python/).

Example

```
from agents import Model, ModelSettings, function_tool

@function_tool
def get_weather(city: str) -> str:
    return f"Weather in {city}: sunny"

agent = DefaultAgent(
    system_prompt="You are a helpful weather assistant",
    model="gpt-4o",
    model_settings=ModelSettings(temperature=0.7),
    tools=[get_weather],
)
```

Initialize an OpenAI Agents SDK based agent.

Parameters:

| Name             | Type            | Description                                                                                                              | Default                                                                                                    |
| ---------------- | --------------- | ------------------------------------------------------------------------------------------------------------------------ | ---------------------------------------------------------------------------------------------------------- |
| `system_prompt`  | `str`           | System prompt (instructions) that defines the agent's behavior and personality.                                          | *required*                                                                                                 |
| `model`          | \`str           | Model\`                                                                                                                  | Model identifier or OpenAI Agents SDK Model instance. Can be any model supported by the OpenAI Agents SDK. |
| `model_settings` | `ModelSettings` | Model-specific settings from the OpenAI Agents SDK. See the SDK documentation for available settings per model provider. | *required*                                                                                                 |
| `tools`          | `list[Tool]`    | List of individual tools (typically function tools created with @function_tool decorator from the OpenAI Agents SDK).    | `[]`                                                                                                       |
| `mcp_servers`    | `list[Any]`     | List of MCP server instances from the OpenAI Agents SDK. These will be wrapped with approval interceptors.               | `[]`                                                                                                       |
| `**kwargs`       | `Any`           | Additional arguments passed to the underlying OpenAI Agent constructor.                                                  | `{}`                                                                                                       |

### run

```
run(input: AgentInput, callback: ApprovalCallback) -> str
```

Process a query and return a response.

Runs the OpenAI Agents SDK agent with the provided query, attachments, and preferences. Tool call approvals are requested through the approval callback, allowing the application to approve or deny tool execution. Image attachments are converted to base64-encoded data URLs. User preferences are temporarily added to the conversation but removed from the persisted history after execution.

Parameters:

| Name       | Type               | Description                                                                                                 | Default    |
| ---------- | ------------------ | ----------------------------------------------------------------------------------------------------------- | ---------- |
| `input`    | `AgentInput`       | Query, attachments, and preferences to process. See AgentInput for details.                                 | *required* |
| `callback` | `ApprovalCallback` | Approval callback for tool calls. Called for each tool execution to request approval. See ApprovalCallback. | *required* |

Returns:

| Type  | Description                       |
| ----- | --------------------------------- |
| `str` | The agent's response as a string. |

Raises:

| Type         | Description                                  |
| ------------ | -------------------------------------------- |
| `ValueError` | If an attachment has a non-image media type. |

### mcp

```
mcp() -> AsyncIterator[DefaultAgent]
```

Manage MCP server lifecycle for this agent.

Connects to all configured MCP servers and wraps them with approval interceptors. Creates the underlying OpenAI Agents SDK agent instance with all tools and MCP servers. On exit, disconnects from MCP servers and cleans up the agent.

Yields:

| Type                          | Description          |
| ----------------------------- | -------------------- |
| `AsyncIterator[DefaultAgent]` | This agent instance. |
