from typing import Literal

from agents import Agent, Runner
from langgraph.graph import END, START, StateGraph

import rules
from data import CUSTOMERS, PRODUCTS, STOCK
from model_factory import build_model
from release_state import ReleaseRequest, ReleaseState

REQUEST_EXTRACTOR = Agent(
    name="Sale Release Request Extractor",
    model=build_model(),
    instructions=(
        "Extrae una solicitud de liberacion de venta de AndesSupply. "
        "customer_id tiene formato C-0000; sku como KRN-900X o CYC-3DX; "
        "quantity es la cantidad de unidades, entero positivo. "
        "Si un dato no aparece en el texto, devuelve null. No inventes identificadores ausentes."
    ),
    output_type=ReleaseRequest,
)


def extract_request(state: ReleaseState) -> dict:
    """Uses the LLM only to turn natural language into a typed contract."""
    result = Runner.run_sync(REQUEST_EXTRACTOR, state["request_text"])
    request: ReleaseRequest = result.final_output
    missing = [name for name in ("customer_id", "sku", "quantity") if getattr(request, name) is None]
    if missing:
        return {
            "status": "blocked",
            "message": f"Request blocked: missing {', '.join(missing)}. Please provide customer, SKU and quantity.",
        }
    return {
        "customer_id": request.customer_id.upper(),
        "sku": request.sku.upper(),
        "quantity": request.quantity,
        "status": "extracted",
    }


def validate_order(state: ReleaseState) -> dict:
    """Order preconditions (not credit): customer and SKU exist, enough stock."""
    if state.get("status") == "blocked":
        return {}
    customer = CUSTOMERS.get(state["customer_id"])
    product = PRODUCTS.get(state["sku"])
    rejection = rules.validate_order(customer, product, STOCK.get(state["sku"]), state["quantity"])
    if rejection:
        reasons = rejection.get("reasons") or [rejection["message"]]
        return {
            "decision": rules.REJECT,
            "reasons": reasons,
            "order_amount_usd": rejection.get("order_amount_usd"),
            "status": "rejected",
        }
    return {
        "order_amount_usd": rules.order_amount(product["price_usd"], state["quantity"]),
        "status": "validated",
    }


def route_after_validation(state: ReleaseState) -> Literal["fetch_credit_profile", "issue_release"]:
    # Early exit: an invalid order never reaches the credit service.
    if state.get("status") in ("blocked", "rejected"):
        return "issue_release"
    return "fetch_credit_profile"


def fetch_credit_profile(state: ReleaseState) -> dict:
    """Simulates the credit service: status, credit limit and current exposure."""
    customer = CUSTOMERS[state["customer_id"]]
    return {
        "credit_status": customer["credit_status"],
        "credit_limit_usd": customer["credit_limit_usd"],
        "current_exposure_usd": customer["current_exposure_usd"],
        "status": "credit_checked",
    }


def compute_exposure(state: ReleaseState) -> dict:
    """Calculations only, no decision."""
    return {
        "available_credit_usd": rules._round_usd(state["credit_limit_usd"] - state["current_exposure_usd"]),
        "projected_exposure_usd": rules._round_usd(state["current_exposure_usd"] + state["order_amount_usd"]),
        "status": "exposure_computed",
    }


def evaluate_release(state: ReleaseState) -> dict:
    """Credit decision with the same rules used by the calculate_release tool."""
    result = rules.evaluate_release(
        credit_status=state["credit_status"],
        credit_limit_usd=state["credit_limit_usd"],
        current_exposure_usd=state["current_exposure_usd"],
        order_amount_usd=state["order_amount_usd"],
    )
    return {"decision": result["decision"], "reasons": result["reasons"], "status": "evaluated"}


def route_after_evaluation(state: ReleaseState) -> Literal["finance_review", "issue_release"]:
    if state.get("decision") == rules.REVIEW:
        return "finance_review"
    return "issue_release"


def build_credit_memo(state: ReleaseState) -> dict:
    """What Finance / credit needs to decide on the exception."""
    utilization = state["projected_exposure_usd"] / state["credit_limit_usd"] * 100
    return {
        "type": "sale_release_credit_exception",
        "customer_id": state["customer_id"],
        "credit_status": state["credit_status"],
        "order": f"{state['quantity']} x {state['sku']} = USD {state['order_amount_usd']:,.2f}",
        "credit_limit_usd": state["credit_limit_usd"],
        "current_exposure_usd": state["current_exposure_usd"],
        "available_credit_usd": state["available_credit_usd"],
        "projected_exposure_usd": state["projected_exposure_usd"],
        "projected_utilization_pct": round(utilization, 1),
        "reasons": state["reasons"],
        "question": "¿Aprueba Finanzas liberar este pedido como excepcion?",
    }


def finance_review(state: ReleaseState) -> dict:
    # Hito 3: the order is held for Finance. Hito 4 adds interrupt() here with build_credit_memo().
    return {"status": "pending_review"}


def issue_release(state: ReleaseState) -> dict:
    status = state.get("status")
    if status == "blocked":
        return {"message": state["message"]}
    if status == "rejected":
        return {"message": f"Order rejected: {' '.join(state['reasons'])}"}
    if status == "pending_review":
        return {"message": f"Order held for Finance review: {' '.join(state['reasons'])}"}
    return {
        "status": "released",
        "message": (
            f"Order released for {state['customer_id']}: {state['quantity']} x {state['sku']} | "
            f"amount USD {state['order_amount_usd']:,.2f} | "
            f"available credit after order USD {state['available_credit_usd'] - state['order_amount_usd']:,.2f}."
        ),
    }


def build_graph(extractor=extract_request):
    """The extractor can be replaced in tests to run the graph without an LLM."""
    builder = StateGraph(ReleaseState)

    builder.add_node("extract_request", extractor)
    builder.add_node("validate_order", validate_order)
    builder.add_node("fetch_credit_profile", fetch_credit_profile)
    builder.add_node("compute_exposure", compute_exposure)
    builder.add_node("evaluate_release", evaluate_release)
    builder.add_node("finance_review", finance_review)
    builder.add_node("issue_release", issue_release)

    builder.add_edge(START, "extract_request")
    builder.add_edge("extract_request", "validate_order")
    builder.add_conditional_edges(
        "validate_order",
        route_after_validation,
        {"fetch_credit_profile": "fetch_credit_profile", "issue_release": "issue_release"},
    )
    builder.add_edge("fetch_credit_profile", "compute_exposure")
    builder.add_edge("compute_exposure", "evaluate_release")
    builder.add_conditional_edges(
        "evaluate_release",
        route_after_evaluation,
        {"finance_review": "finance_review", "issue_release": "issue_release"},
    )
    builder.add_edge("finance_review", "issue_release")
    builder.add_edge("issue_release", END)

    return builder.compile()


graph = build_graph()
