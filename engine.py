import sys
import uuid
from contextlib import AsyncExitStack
from pathlib import Path

from agents import Agent, Runner
from agents.mcp import MCPServerStdio, create_static_tool_filter

from context import AppContext
from model_factory import build_model
from router import DeterministicRouter,HybridRouter,ModelRouter
from schemas import FinalAnswer,Route,RouteDecision
from tools import search_policies

MCP_SERVER_FILE=Path(__file__).parent/"mcp_server.py"

# Each route only sees the MCP tools it needs (least privilege per request).
MCP_TOOLS_FOR={
    Route.SQL:["sales_summary"],
    Route.TOOLS:["get_customer_credit","get_stock"],
}


def _local_tools_for(route:Route):
    """RAG stays local; operational and SQL capabilities come from the MCP server."""
    if route==Route.RAG:
        return [search_policies]
    return []


def _instructions_for(route:Route)->str:
    base=(
        "Eres AI Operations Agent de AndesSupply. No inventes datos internos. "
        "Usa solo las tools disponibles en esta ejecucion. "
        "Si una tool devuelve un error recuperable, explica que informacion falta. "
    )
    if route==Route.RAG:
        return base+"Responde usando la evidencia recuperada y cita source_ref en facts."
    if route==Route.SQL:
        return base+"Responde con los agregados historicos obtenidos desde SQL y cita [SQL:sales]."
    if route==Route.TOOLS:
        return base+(
            "Responde con estado operacional actual: stock o credito del cliente "
            "(estado, limite, exposicion y linea disponible). No liberas pedidos."
        )
    return base+"Responde conceptualmente sin afirmar datos internos de AndesSupply."


def _mcp_server(route:Route)->MCPServerStdio:
    return MCPServerStdio(
        name="AndesSupply Sale Release MCP",
        params={"command":sys.executable,"args":[str(MCP_SERVER_FILE)],"cwd":str(MCP_SERVER_FILE.parent)},
        cache_tools_list=True,
        use_structured_content=True,
        tool_filter=create_static_tool_filter(allowed_tool_names=MCP_TOOLS_FOR[route]),
    )


async def choose_route(query:str,strategy:str)->RouteDecision:
    if strategy=="deterministic":
        return DeterministicRouter().route(query)
    if strategy=="model":
        return await ModelRouter().route(query)
    if strategy=="hybrid":
        return await HybridRouter().route(query)
    raise ValueError(f"ROUTER_STRATEGY no soportado: {strategy}")


async def answer_with_agent(query:str,decision:RouteDecision)->FinalAnswer:
    """Answers rag, sql, tools, direct and clarify routes. The release route goes to the workflow."""
    if decision.route==Route.CLARIFY:
        return FinalAnswer(
            answer=decision.clarification_question or "Necesito mas informacion.",
            facts=[],warnings=[decision.reason],
        )
    if decision.route==Route.RELEASE:
        raise ValueError("The release route is handled by the release workflow, not by the agent.")

    async with AsyncExitStack() as stack:
        mcp_servers=[]
        if decision.route in MCP_TOOLS_FOR:
            mcp_servers.append(await stack.enter_async_context(_mcp_server(decision.route)))

        agent=Agent[AppContext](
            name="AI Operations Agent",
            model=build_model(),
            instructions=_instructions_for(decision.route),
            tools=_local_tools_for(decision.route),
            mcp_servers=mcp_servers,
            output_type=FinalAnswer,
        )
        result=await Runner.run(agent,query,context=AppContext(str(uuid.uuid4())))
    return result.final_output


async def answer(query:str,strategy:str)->tuple[RouteDecision,FinalAnswer]:
    decision=await choose_route(query,strategy)
    return decision,await answer_with_agent(query,decision)
