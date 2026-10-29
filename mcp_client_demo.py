"""Pure MCP client: no LLM. Lists and calls the server capabilities over stdio."""

import asyncio
import sys
from pathlib import Path

from mcp import Client, StdioServerParameters

ROOT = Path(__file__).parent
SERVER_FILE = ROOT / "mcp_server.py"


def server_parameters() -> StdioServerParameters:
    return StdioServerParameters(command=sys.executable, args=[str(SERVER_FILE)], cwd=ROOT)


async def main() -> None:
    async with Client(server_parameters()) as client:
        print("=== MCP CONNECTION (stdio) ===")
        print("protocol:", client.protocol_version)

        tools = await client.list_tools()
        print("\n=== list_tools ===")
        for item in tools.tools:
            print(f"- {item.name}: {item.description}")

        stock = await client.call_tool("get_stock", {"sku": "KRN-900X"})
        print("\n=== call_tool get_stock(KRN-900X) ===")
        print(stock.structured_content)

        credit = await client.call_tool("get_customer_credit", {"customer_id": "C-1003"})
        print("\n=== call_tool get_customer_credit(C-1003) ===")
        print(credit.structured_content)

        release = await client.call_tool(
            "calculate_release", {"customer_id": "C-1003", "sku": "KRN-900X", "quantity": 9}
        )
        print("\n=== call_tool calculate_release(C-1003, KRN-900X, 9) ===")
        print(release.structured_content)

        resources = await client.list_resources()
        print("\n=== list_resources ===")
        for item in resources.resources:
            print(f"- {item.uri}")

        policy = await client.read_resource("policy://credit")
        print("\n=== read_resource policy://credit ===")
        for content in policy.contents:
            text = getattr(content, "text", None)
            if text:
                print(text[:400])


if __name__ == "__main__":
    asyncio.run(main())
