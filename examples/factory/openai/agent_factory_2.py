from agents import ModelSettings, OpenAIResponsesModel, function_tool
from agents.mcp import MCPServerStdio
from openai import AsyncOpenAI

from group_genie.agent import Agent, AgentFactory, AgentInfo, AsyncTool
from group_genie.agent.provider.openai import DefaultAgent
from group_genie.secrets import SecretsProvider


def create_search_agent(secrets: dict[str, str]) -> Agent:
    brave_mcp_server = MCPServerStdio(
        name="Brave Search",
        params={
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-brave-search"],
            "env": {
                "BRAVE_API_KEY": secrets.get("BRAVE_API_KEY", ""),
            },
        },
    )

    return DefaultAgent(
        system_prompt="You are a search specialist. Use web search to find accurate, up-to-date information. Provide concise answers.",
        model=OpenAIResponsesModel(
            model="gpt-4.1",
            openai_client=AsyncOpenAI(api_key=secrets.get("OPENAI_API_KEY", "")),
        ),
        model_settings=ModelSettings(),
        mcp_servers=[brave_mcp_server],
    )


def create_math_agent(secrets: dict[str, str]) -> Agent:
    ipybox_mcp_server = MCPServerStdio(
        name="IPyBox Python Executor",
        params={
            "command": "uvx",
            "args": ["ipybox", "mcp"],
        },
    )

    return DefaultAgent(
        system_prompt="You are a computational mathematician. For every math problem, write and execute Python code to calculate the answer.",
        model=OpenAIResponsesModel(
            model="gpt-4.1",
            openai_client=AsyncOpenAI(api_key=secrets.get("OPENAI_API_KEY", "")),
        ),
        model_settings=ModelSettings(),
        mcp_servers=[ipybox_mcp_server],
    )


def create_system_agent(
    secrets: dict[str, str],
    extra_tools: dict[str, AsyncTool],
    agent_infos: list[AgentInfo],
) -> Agent:
    from examples.prompts.coordinator.prompt import system_prompt

    tools = [function_tool(extra_tools["run_subagent"])]
    if tool := extra_tools.get("get_group_chat_messages"):
        tools.append(function_tool(tool))

    return DefaultAgent(
        system_prompt=system_prompt(agent_infos),
        model=OpenAIResponsesModel(
            model="gpt-4.1",
            openai_client=AsyncOpenAI(api_key=secrets.get("OPENAI_API_KEY", "")),
        ),
        model_settings=ModelSettings(),
        tools=tools,
    )


def get_agent_factory(secrets_provider: SecretsProvider | None = None):
    registry = AgentFactory(
        system_agent_factory=create_system_agent,
        secrets_provider=secrets_provider,
    )

    registry.add_agent_factory_fn(
        factory_fn=create_search_agent,
        info=AgentInfo(
            name="search",
            description="Searches the web for current information. Use for real-time facts, recent events, or up-to-date data.",
        ),
    )

    registry.add_agent_factory_fn(
        factory_fn=create_math_agent,
        info=AgentInfo(
            name="math",
            description="Solves math problems using Python code execution. Use for calculations or numerical analysis.",
        ),
    )

    return registry
