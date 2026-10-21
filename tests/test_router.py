from router import DeterministicRouter
from schemas import Route


def test_routes_policy_to_rag():
    assert DeterministicRouter().route("¿Qué dice la política sobre venderle a un cliente en hold?").route==Route.RAG


def test_routes_sales_to_sql():
    assert DeterministicRouter().route("¿Cuánto le hemos facturado a C-1003 en 2026?").route==Route.SQL


def test_routes_stock_to_tools():
    assert DeterministicRouter().route("¿Hay stock de CYC-3DX?").route==Route.TOOLS


def test_routes_release_with_ids_to_tools():
    assert DeterministicRouter().route("Libera 4 KRN-900X para C-1003").route==Route.TOOLS


def test_routes_release_without_ids_to_clarify():
    assert DeterministicRouter().route("¿Puedo liberar el pedido?").route==Route.CLARIFY


def test_routes_short_query_to_clarify():
    assert DeterministicRouter().route("ok").route==Route.CLARIFY


def test_accents_do_not_change_route():
    router=DeterministicRouter()
    assert router.route("política de crédito").route==router.route("politica de credito").route==Route.RAG
