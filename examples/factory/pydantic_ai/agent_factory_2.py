from pydantic_ai.builtin_tools import WebSearchTool
from pydantic_ai.mcp import MCPServerStdio
from pydantic_ai.models.google import GoogleModel, GoogleModelSettings
from pydantic_ai.providers.google import GoogleProvider

from group_genie.agent import Agent, AgentFactory, AgentInfo, AsyncTool
from group_genie.agent.provider.pydantic_ai import DefaultAgent
from group_genie.secrets import SecretsProvider


def create_search_agent(secrets: dict[str, str]) -> Agent:
    model = GoogleModel(
        "gemini-3-flash-preview",
        provider=GoogleProvider(api_key=secrets.get("GOOGLE_API_KEY", "")),
    )

    return DefaultAgent(
        system_prompt="You are a search specialist. Use web search to find accurate, up-to-date information. Provide concise answers.",
        model=model,
        model_settings=GoogleModelSettings(
            google_thinking_config={
                "thinking_level": "minimal",
                "include_thoughts": False,
            }
        ),
        builtin_tools=[WebSearchTool()],
    )


def create_math_agent(secrets: dict[str, str]) -> Agent:
    ipybox_mcp_server = MCPServerStdio(
        command="uvx",
        args=["ipybox", "mcp"],
    )

    model = GoogleModel(
        "gemini-3-flash-preview",
        provider=GoogleProvider(api_key=secrets.get("GOOGLE_API_KEY", "")),
    )

    return DefaultAgent(
        system_prompt="You are a computational mathematician. For every math problem, write and execute Python code to calculate the answer.",
        model=model,
        model_settings=GoogleModelSettings(
            google_thinking_config={
                "thinking_level": "minimal",
                "include_thoughts": False,
            }
        ),
        toolsets=[ipybox_mcp_server],
    )


def create_system_agent(
    secrets: dict[str, str],
    extra_tools: dict[str, AsyncTool],
    agent_infos: list[AgentInfo],
) -> Agent:
    from examples.prompts.coordinator.prompt import system_prompt

    tools: list[AsyncTool] = [extra_tools["run_subagent"]]
    if tool := extra_tools.get("get_group_chat_messages"):
        tools.append(tool)

    model = GoogleModel(
        "gemini-3-flash-preview",
        provider=GoogleProvider(api_key=secrets.get("GOOGLE_API_KEY", "")),
    )

    return DefaultAgent(
        system_prompt=system_prompt(agent_infos),
        model=model,
        model_settings=GoogleModelSettings(
            google_thinking_config={
                "thinking_level": "high",
                "include_thoughts": True,
            }
        ),
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
