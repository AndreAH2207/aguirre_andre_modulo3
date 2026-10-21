import re
import unicodedata

from agents import Agent, Runner

from model_factory import build_model
from schemas import Route,RouteDecision

RAG_KEYWORDS=["politica","sla","despacho","devolucion","reglamento","norma","procedimiento",
              "requisito","excepcion","aprobar","aprobacion","autoriza","escalar","quien decide"]
SQL_KEYWORDS=["ventas","vendimos","vendido","vendio","facturacion","facturado","facturamos","revenue",
              "historico","historial","ha comprado","compras anteriores","pedidos anteriores","unidades vendidas"]
TOOLS_KEYWORDS=["stock","sku","cliente","precio","cotiza","libera","pedido","linea","credito","limite",
                "exposicion","deuda","debe","saldo","disponible","bloqueado","hold","inventario"]
NEEDS_IDS_KEYWORDS=["precio","libera","pedido"]
ID_PATTERN=r"(C-\d{4}|[A-Z]{2,}-[A-Z0-9-]+)"


def _normalize(text:str)->str:
    """Lowercase and remove accents, so keywords can be written without tildes."""
    decomposed=unicodedata.normalize("NFD",text.lower().strip())
    return "".join(c for c in decomposed if unicodedata.category(c)!="Mn")


class DeterministicRouter:
    """Reglas rapidas y auditables para casos obvios."""

    def route(self,query:str)->RouteDecision:
        q=_normalize(query)

        if len(q)<4:
            return RouteDecision(
                route=Route.CLARIFY,confidence=0.99,
                reason="Consulta demasiado corta",
                clarification_question="¿Puedes describir que necesitas consultar?",
            )

        if any(k in q for k in RAG_KEYWORDS):
            return RouteDecision(route=Route.RAG,confidence=0.95,reason="Pregunta documental")

        if any(k in q for k in SQL_KEYWORDS):
            return RouteDecision(route=Route.SQL,confidence=0.95,reason="Pregunta historica/agregada")

        if any(k in q for k in TOOLS_KEYWORDS):
            if any(k in q for k in NEEDS_IDS_KEYWORDS) and not re.search(ID_PATTERN,query.upper()):
                return RouteDecision(
                    route=Route.CLARIFY,confidence=0.95,
                    reason="Faltan identificadores de cliente o SKU",
                    clarification_question="¿Que cliente, SKU y cantidad debo considerar?",
                )
            return RouteDecision(route=Route.TOOLS,confidence=0.92,reason="Dato operacional actual")

        if q.startswith(("que es","explica","define","cual es la diferencia")):
            return RouteDecision(route=Route.DIRECT,confidence=0.90,reason="Pregunta conceptual")

        return RouteDecision(route=Route.DIRECT,confidence=0.55,reason="No existe una regla de alta confianza")


class ModelRouter:
    """Usa un LLM solo como clasificador semantico con salida estructurada."""

    def __init__(self)->None:
        self.agent=Agent(
            name="Query Router",
            model=build_model(),
            instructions=(
                "Clasifica la consulta en exactamente una ruta. "
                "rag=politicas de credito y liberacion de ventas (documentos); "
                "sql=ventas historicas, facturacion o agregaciones del pasado; "
                "tools=estado actual: producto, stock, cliente, linea de credito, exposicion, "
                "o una solicitud de liberar un pedido; "
                "direct=conocimiento general que no necesita datos internos; "
                "clarify=informacion esencial faltante o solicitud ambigua. "
                "No respondas la consulta. Devuelve solo la decision estructurada."
            ),
            output_type=RouteDecision,
        )

    async def route(self,query:str)->RouteDecision:
        result=await Runner.run(self.agent,query)
        return result.final_output


class HybridRouter:
    """Rules first; LLM only when las reglas no estan suficientemente seguras."""

    def __init__(self,threshold:float=0.90)->None:
        self.rules=DeterministicRouter()
        self.model=ModelRouter()
        self.threshold=threshold

    async def route(self,query:str)->RouteDecision:
        decision=self.rules.route(query)
        if decision.confidence>=self.threshold:
            return decision
        return await self.model.route(query)
