# Group Genie

## Introduction

Group Genie enables existing single-user AI agents to participate in group chat conversations without requiring modification to the agents themselves. While many AI agents excel at responding to direct queries from individual users, they typically cannot handle multi-party conversations where relevant information emerges from complex exchanges between multiple participants. Group Genie solves this by combining [Group Sense](https://gradion-ai.github.io/group-sense/)'s intelligent pattern detection with a flexible agent integration layer. Agents can be based on any technology stack (framework, API, etc.) and integrated through a simple agent interface, with default implementations provided for Pydantic AI and the OpenAI Agents SDK.

## Key Features

- **Group conversation understanding**: Built on [Group Sense](https://gradion-ai.github.io/group-sense/), which monitors group chats, detects conversation patterns, and reformulates multi-party exchanges into self-contained queries that AI agents can process.
- **Dynamic response routing**: Group Sense reasoners determine recipients of agent responses based on conversation context and semantics, enabling agents to respond to appropriate group members.
- **Agent connectors**: Connect existing AI agents to group chats without modification. Default connectors are provided for Pydantic AI and the OpenAI Agents SDK, based on a simple interface.
- **Agent hierarchies**: Organize agents into coordinator-subagent hierarchies of any depth, each having their own context window for focused conversations and task-specific expertise.
- **User-specific credentials**: Agents can act on behalf of individual group members using their credentials, enabling secure access to a user's private resources while maintaining proper access boundaries to other users.
- **Agent lifecycle management**: Configurable idle timeouts optimize resource usage by automatically stopping idle agents and freeing their memory and MCP server connections.
- **Session persistence**: File-based persistence for group chat messages and agent states allows group sessions to be suspended and resumed.
- **Unified tool approval mechanism**: Consistent approval workflow for tool calls across agent hierarchies, with support for manual and automatic approval modes.
- **Rich message support**: Handles message attachments with automatic propagation through agent chains. Thread references provide context from related group chats.

## Next steps

1. [Install](installation/) the library and configure API keys
1. Follow the [tutorial](tutorial/) to build your first group chat agent
1. Learn how to [integrate](integration/) Group Genie into your application

## LLM-optimized documentation

- [llms.txt](/group-genie/llms.txt)
- [llms-full.txt](/group-genie/llms-full.txt)
