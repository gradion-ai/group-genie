## Key modules

### `group_genie.message`
Contains core message types for group chat communication (`Message`, `Attachment`, `Thread`). Messages are the primary unit of communication with support for file attachments, cross-conversation thread references, and correlation IDs for tracking request-response pairs.

### `group_genie.datastore`
Provides file-based JSON persistence (`DataStore`) for session messages and agent state. Features hierarchical key-based organization via `narrow()`, asynchronous non-blocking saves, and automatic key sanitization for filesystem safety.

### `group_genie.preferences`
Abstract interface (`PreferencesSource`) for supplying user-specific preferences that customize agent behavior and response style. Preferences are free-form text included in agent prompts without modifying system prompts.

### `group_genie.secrets`
Abstract interface (`SecretsProvider`) for providing user-specific credentials to agents and reasoners. Enables agents to act on behalf of individual users while maintaining proper access boundaries.

### `group_genie.session`
Main entry point for managing group chat sessions (`GroupSession`) and execution tracking (`Execution`). Orchestrates message flow through group reasoners and agents, manages lifecycle and state persistence, and provides concurrent processing with guaranteed message ordering.

### `group_genie.agent.base`
Defines the core agent abstraction (`Agent`) with metadata (`AgentInfo`) and input types (`AgentInput`). Agents are processing units that handle delegated queries with support for state serialization, MCP server lifecycle management, and tool approval callbacks.

### `group_genie.agent.approval`
Implements the unified tool approval mechanism (`Approval`, `ApprovalCallback`, `ApprovalContext`). Provides consistent approval workflow across agent hierarchies with support for manual and automatic approval modes.

### `group_genie.agent.factory`
Factory for creating agent instances (`AgentFactory`). Supports standalone agents and coordinator agents that orchestrate subagents, with automatic provisioning of user-specific secrets and storage of agent metadata.

### `group_genie.agent.group.base`
Abstract base class for group reasoning logic (`GroupReasoner`). Reasoners analyze group chat messages and decide whether to ignore them or generate queries for agents, maintaining conversation history across message updates.

### `group_genie.agent.group.factory`
Factory for creating group reasoner instances (`GroupReasonerFactory`) customized for specific users. Provides user-specific secrets and stores idle timeout configuration for independent reasoning state per user.

### `group_genie.agent.provider.pydantic_ai.group`
Default group reasoner implementation (`DefaultGroupReasoner`) using group-sense library. Wraps group-sense's DefaultGroupReasoner and adapts Group Genie's message types to group-sense format.

### `group_genie.agent.provider.pydantic_ai.utils`
Utility classes for pydantic-ai integration including `ToolFilter` for selective tool exposure and `ApprovalInterceptor` for intercepting and routing tool calls through approval callbacks.

### `group_genie.agent.provider.pydantic_ai.agent.default`
Ready-to-use agent implementation (`DefaultAgent`) built on pydantic-ai. Supports conversation state management, tool calling with approval workflows, MCP server lifecycle management, and configuration with custom prompts, models, toolsets, and built-in tools.
