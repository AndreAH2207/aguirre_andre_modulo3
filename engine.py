import uuid

from agents import Agent, Runner

from context import AppContext
from model_factory import build_model
from router import DeterministicRouter,HybridRouter,ModelRouter
from schemas import FinalAnswer,Route,RouteDecision
from tools import (
    calculate_release,get_customer,get_product,get_stock,
    sales_summary,search_policies,
)


def _tools_for(route:Route):
    """Una sola aplicacion; el router reduce la superficie de tools por solicitud."""
    if route==Route.RAG:
        return [search_policies]
    if route==Route.SQL:
        return [sales_summary]
    if route==Route.TOOLS:
        return [get_product,get_stock,get_customer,calculate_release]
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
            "Responde con estado operacional actual: producto, stock, cliente o linea de credito. "
            "Para liberar un pedido usa calculate_release y reporta su decision y motivos sin cambiarlos."
        )
    return base+"Responde conceptualmente sin afirmar datos internos de AndesSupply."


async def choose_route(query:str,strategy:str)->RouteDecision:
    if strategy=="deterministic":
        return DeterministicRouter().route(query)
    if strategy=="model":
        return await ModelRouter().route(query)
    if strategy=="hybrid":
        return await HybridRouter().route(query)
    raise ValueError(f"ROUTER_STRATEGY no soportado: {strategy}")


async def answer(query:str,strategy:str)->tuple[RouteDecision,FinalAnswer]:
    decision=await choose_route(query,strategy)

    if decision.route==Route.CLARIFY:
        return decision,FinalAnswer(
            answer=decision.clarification_question or "Necesito mas informacion.",
            facts=[],warnings=[decision.reason],
        )

    agent=Agent[AppContext](
        name="AI Operations Agent",
        model=build_model(),
        instructions=_instructions_for(decision.route),
        tools=_tools_for(decision.route),
        output_type=FinalAnswer,
    )
    result=await Runner.run(
        agent,
        query,
        context=AppContext(str(uuid.uuid4())),
    )
    return decision,result.final_output
