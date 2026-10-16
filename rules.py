"""Deterministic sale release rules. No LLM: only objective comparisons.

Order: existence -> stock -> hold -> credit line -> review amount.
Rejections stop the evaluation; review reasons accumulate.
"""

from decimal import ROUND_HALF_UP, Decimal

from data import CUSTOMERS, PRODUCTS, REVIEW_AMOUNT_USD, STOCK

RELEASE = "RELEASE"
REVIEW = "REVIEW"
REJECT = "REJECT"


def _error(kind: str, message: str) -> dict:
    return {"ok": False, "error_type": kind, "message": message, "recoverable": True}


def _round_usd(value: float) -> float:
    """Round USD to 2 decimals (half up). Decimal avoids float cases like 2.675."""
    return float(Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def calculate_release(customer_id: str, sku: str, quantity: int) -> dict:
    """Decides whether an order can be released: RELEASE, REVIEW or REJECT."""
    if quantity <= 0:
        return _error("invalid_quantity", "quantity must be > 0")
    customer = CUSTOMERS.get(customer_id.upper())
    product = PRODUCTS.get(sku.upper())
    if not customer:
        return _error("not_found", "Customer not found")
    if not product:
        return _error("not_found", "SKU not found")

    order_amount = _round_usd(product["price_usd"] * quantity)
    available = STOCK[product["sku"]]

    if quantity > available:
        return {
            "ok": True,
            "decision": REJECT,
            "order_amount_usd": order_amount,
            "reasons": [f"Insufficient stock: requested {quantity}, available {available}."],
        }

    reasons = []
    if customer["credit_status"] == "hold":
        reasons.append("Customer is on credit hold.")

    final_exposure = _round_usd(customer["current_exposure_usd"] + order_amount)
    if final_exposure > customer["credit_limit_usd"]:
        reasons.append(
            f"Insufficient credit line: exposure + order = {final_exposure:,.2f} "
            f"exceeds limit {customer['credit_limit_usd']:,.2f}."
        )

    if order_amount >= REVIEW_AMOUNT_USD:
        reasons.append(
            f"Order of {order_amount:,.2f} reaches review amount {REVIEW_AMOUNT_USD:,.2f}."
        )

    return {
        "ok": True,
        "decision": REVIEW if reasons else RELEASE,
        "order_amount_usd": order_amount,
        "reasons": reasons,
    }
