"""Deterministic sale release rules. No LLM: only objective comparisons.

Two separate steps:
- validate_order: order preconditions (quantity, customer and SKU exist, stock).
  Stock is not a credit criterion; it is checked first because an order that
  cannot be shipped has nothing to release.
- evaluate_release: the credit decision (hold -> credit line -> review amount).
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


def order_amount(price_usd: float, quantity: int) -> float:
    return _round_usd(price_usd * quantity)


def validate_order(
    customer: dict | None, product: dict | None, available_stock: int | None, quantity: int
) -> dict | None:
    """Returns an error or a REJECT result when the order cannot be evaluated; None if valid."""
    if quantity <= 0:
        return _error("invalid_quantity", "quantity must be > 0")
    if not customer:
        return _error("not_found", "Customer not found")
    if not product or available_stock is None:
        return _error("not_found", "SKU not found")
    if quantity > available_stock:
        return {
            "ok": True,
            "decision": REJECT,
            "order_amount_usd": order_amount(product["price_usd"], quantity),
            "reasons": [f"Insufficient stock: requested {quantity}, available {available_stock}."],
        }
    return None


def evaluate_release(
    *,
    credit_status: str,
    credit_limit_usd: float,
    current_exposure_usd: float,
    order_amount_usd: float,
    review_amount_usd: float = REVIEW_AMOUNT_USD,
) -> dict:
    """Credit decision for a valid order: RELEASE or REVIEW (Finance)."""
    reasons = []
    if credit_status == "hold":
        reasons.append("Customer is on credit hold.")

    projected_exposure = _round_usd(current_exposure_usd + order_amount_usd)
    if projected_exposure > credit_limit_usd:
        reasons.append(
            f"Insufficient credit line: exposure + order = {projected_exposure:,.2f} "
            f"exceeds limit {credit_limit_usd:,.2f}."
        )

    if order_amount_usd >= review_amount_usd:
        reasons.append(
            f"Order of {order_amount_usd:,.2f} reaches review amount {review_amount_usd:,.2f}."
        )

    return {
        "ok": True,
        "decision": REVIEW if reasons else RELEASE,
        "order_amount_usd": order_amount_usd,
        "reasons": reasons,
    }


def calculate_release(customer_id: str, sku: str, quantity: int) -> dict:
    """Decides whether an order can be released: RELEASE, REVIEW or REJECT."""
    customer = CUSTOMERS.get(customer_id.upper())
    product = PRODUCTS.get(sku.upper())
    rejection = validate_order(customer, product, STOCK.get(sku.upper()), quantity)
    if rejection:
        return rejection
    return evaluate_release(
        credit_status=customer["credit_status"],
        credit_limit_usd=customer["credit_limit_usd"],
        current_exposure_usd=customer["current_exposure_usd"],
        order_amount_usd=order_amount(product["price_usd"], quantity),
    )
