# --8<-- [start:imports]

from pydantic_ai.mcp import MCPServerStdio
from pydantic_ai.models.google import GoogleModel, GoogleModelSettings
from pydantic_ai.providers.google import GoogleProvider

from group_genie.agent import Agent, AgentFactory
from group_genie.agent.provider.pydantic_ai import DefaultAgent
from group_genie.secrets import SecretsProvider

# --8<-- [end:imports]


# --8<-- [start:create-system-agent]
def create_system_agent(secrets: dict[str, str]) -> Agent:
    brave_mcp_server = MCPServerStdio(
        command="npx",
        args=["-y", "@modelcontextprotocol/server-brave-search"],
        env={
            "BRAVE_API_KEY": secrets.get("BRAVE_API_KEY", ""),
        },
    )

    model = GoogleModel(
        "gemini-2.5-flash",
        provider=GoogleProvider(api_key=secrets.get("GOOGLE_API_KEY", "")),
    )

    return DefaultAgent(
        system_prompt=(
            "You are a helpful assistant. "
            "Always search the web for checking facts. "
            "Provide short, concise answers."
        ),
        model=model,
        model_settings=GoogleModelSettings(
            google_thinking_config={
                "thinking_budget": 0,
            }
        ),
        toolsets=[brave_mcp_server],
    )


# --8<-- [end:create-system-agent]


# --8<-- [start:agent-factory]
def get_agent_factory(secrets_provider: SecretsProvider | None = None):
    return AgentFactory(
        system_agent_factory=create_system_agent,
        secrets_provider=secrets_provider,
    )


# --8<-- [end:agent-factory]
