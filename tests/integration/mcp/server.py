from pathlib import Path

from mcp.server.fastmcp import FastMCP

STDIO_SERVER_PATH = Path(__file__)


async def tool_1(s: str) -> str:
    """
    This is tool 1.

    Args:
        s: A string
    """
    return f"You passed to tool 1: {s}"


async def tool_2(s: str) -> str:
    """
    This is tool 2.
    """
    return f"You passed to tool 2: {s}"


def create_server(**kwargs) -> FastMCP:
    server = FastMCP("Test MCP Server", **kwargs)
    server.add_tool(tool_1)
    server.add_tool(tool_2)
    return server


def main():
    server = create_server()
    server.run(transport="stdio")


if __name__ == "__main__":
    import logging

    logger = logging.getLogger("mcp")
    logger.setLevel(logging.WARNING)

    main()
