"""Agent consuming the same MCP server as the pure client."""

import asyncio
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from agents import Agent, Runner
from agents.mcp import MCPServerStdio

from model_factory import build_model
from schemas import FinalAnswer

ROOT = Path(__file__).parent
SERVER_FILE = ROOT / "mcp_server.py"
DEFAULT_QUERY = (
    "Revisa la linea de credito de C-1003, el stock de KRN-900X "
    "y si se puede liberar un pedido de 9 unidades de KRN-900X para C-1003."
)


async def main() -> None:
    query = " ".join(sys.argv[1:]) or DEFAULT_QUERY
    async with MCPServerStdio(
        name="AndesSupply Sale Release MCP",
        params={"command": sys.executable, "args": [str(SERVER_FILE)], "cwd": str(ROOT)},
        cache_tools_list=True,
        use_structured_content=True,
    ) as server:
        agent = Agent(
            name="AndesSupply Credit Agent",
            model=build_model(),
            instructions=(
                "Eres el agente de liberacion de ventas de AndesSupply. "
                "Usa las herramientas MCP para obtener datos internos; no inventes credito, stock ni decisiones. "
                "Para saber si un pedido se libera usa calculate_release y reporta su decision y motivos sin cambiarlos. "
                "No puedes aprobar excepciones: si la decision es REVIEW, indica que pasa a Finanzas / credito."
            ),
            mcp_servers=[server],
            output_type=FinalAnswer,
        )
        print("Query:", query)
        result = await Runner.run(agent, query)

        print("\n=== AGENT + MCP ===")
        print(result.final_output.model_dump_json(indent=2))


if __name__ == "__main__":
    asyncio.run(main())
