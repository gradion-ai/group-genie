from agents import ModelSettings, OpenAIResponsesModel
from agents.mcp import MCPServerStdio
from openai import AsyncOpenAI

from group_genie.agent import Agent, AgentFactory
from group_genie.agent.provider.openai import DefaultAgent
from group_genie.secrets import SecretsProvider


def create_system_agent(secrets: dict[str, str]) -> Agent:
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
        system_prompt=(
            "You are a helpful assistant. "
            "Always search the web for checking facts. "
            "Provide short, concise answers."
        ),
        model=OpenAIResponsesModel(
            model="gpt-4.1",
            openai_client=AsyncOpenAI(api_key=secrets.get("OPENAI_API_KEY", "")),
        ),
        model_settings=ModelSettings(),
        mcp_servers=[brave_mcp_server],
    )


def get_agent_factory(secrets_provider: SecretsProvider | None = None):
    return AgentFactory(
        system_agent_factory=create_system_agent,
        secrets_provider=secrets_provider,
    )
