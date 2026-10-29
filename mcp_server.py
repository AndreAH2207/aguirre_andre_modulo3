"""MCP server for sale release credit capabilities.

Least privilege: read-only business capabilities. It does NOT expose free SQL,
full customer records, writes, or approving credit exceptions (that decision
belongs to Finance / credit inside the release workflow).

Important for stdio: nothing in this process may print to stdout.
"""

from pathlib import Path
from typing import Any

from mcp.server import MCPServer

import rules
import sales
from data import CUSTOMERS, STOCK

ROOT = Path(__file__).parent
DOCS_DIR = ROOT / "docs"

# MCPServer is an SDK class, so it keeps its English name.
mcp = MCPServer(
    "AndesSupply Sale Release",
    instructions=(
        "MCP server for AndesSupply sale release. Exposes read-only credit capabilities: "
        "customer credit profile, stock, release decision, historical sales and policies."
    ),
)


@mcp.tool(structured_output=True)
def get_customer_credit(customer_id: str) -> dict[str, Any]:
    """Credit profile of a customer: status, credit limit, current exposure and available credit."""
    normalized = customer_id.upper().strip()
    customer = CUSTOMERS.get(normalized)
    if customer is None:
        return {"ok": False, "error": "customer_not_found", "customer_id": normalized}
    return {
        "ok": True,
        "customer_id": normalized,
        "credit_status": customer["credit_status"],
        "credit_limit_usd": customer["credit_limit_usd"],
        "current_exposure_usd": customer["current_exposure_usd"],
        "available_credit_usd": rules._round_usd(customer["credit_limit_usd"] - customer["current_exposure_usd"]),
        "source": "credit_service",
    }


@mcp.tool(structured_output=True)
def get_stock(sku: str) -> dict[str, Any]:
    """Current available stock of a known SKU."""
    normalized = sku.upper().strip()
    if normalized not in STOCK:
        return {"ok": False, "error": "sku_not_found", "sku": normalized}
    return {"ok": True, "sku": normalized, "available_units": STOCK[normalized], "source": "inventory"}


@mcp.tool(structured_output=True)
def calculate_release(customer_id: str, sku: str, quantity: int) -> dict[str, Any]:
    """Release decision for an order: RELEASE, REVIEW (Finance) or REJECT. Read-only: approves nothing."""
    return rules.calculate_release(customer_id.strip(), sku.strip(), quantity)


@mcp.tool(structured_output=True)
def sales_summary(sku: str | None = None, customer_id: str | None = None, year: int | None = None) -> dict[str, Any]:
    """Historical sales with optional filters (SKU, customer, year). Fixed parameterized SQL."""
    return sales.sales_summary(sku, customer_id, year)


@mcp.resource("policy://credit", mime_type="text/markdown")
def credit_policy() -> str:
    """Credit policy: hold, credit line, review amount and approvals."""
    return (DOCS_DIR / "credit_policy.md").read_text(encoding="utf-8")


@mcp.resource("policy://release", mime_type="text/markdown")
def release_policy() -> str:
    """Sale release policy: steps, insufficient stock and unknown identifiers."""
    return (DOCS_DIR / "release_policy.md").read_text(encoding="utf-8")


if __name__ == "__main__":
    # stdio is the SDK's default local transport.
    mcp.run()
