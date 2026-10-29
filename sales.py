"""Historical sales query shared by the agent tools and the MCP server.

Fixed, parameterized SQL: callers only choose the filters, never the query.
"""

import sqlite3

from bootstrap_db import DB_PATH


def sales_summary(sku: str | None = None, customer_id: str | None = None, year: int | None = None) -> dict:
    if not DB_PATH.exists():
        return {
            "ok": False,
            "error_type": "database_missing",
            "message": "Ejecuta primero: uv run python bootstrap_db.py",
            "recoverable": True,
        }

    where = []
    params = []
    if sku:
        where.append("sku=?")
        params.append(sku.upper())
    if customer_id:
        where.append("customer_id=?")
        params.append(customer_id.upper())
    if year:
        where.append("substr(sale_date,1,4)=?")
        params.append(str(year))
    clause = " WHERE " + " AND ".join(where) if where else ""
    query = (
        "SELECT COUNT(*) AS transactions, "
        "COALESCE(SUM(quantity),0) AS units, "
        "ROUND(COALESCE(SUM(net_revenue_usd),0),2) AS revenue_usd "
        "FROM sales" + clause
    )
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        row = dict(conn.execute(query, tuple(params)).fetchone())
    return {
        "ok": True,
        "filters": {"sku": sku, "customer_id": customer_id, "year": year},
        "source_ref": "[SQL:sales]",
        **row,
    }
