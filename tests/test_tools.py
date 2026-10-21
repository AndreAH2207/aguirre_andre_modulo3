import json

import pytest

from bootstrap_db import bootstrap
from tools import execute


@pytest.fixture(scope="module",autouse=True)
def database():
    bootstrap()


def _call(name:str,**arguments)->dict:
    return json.loads(execute(name,json.dumps(arguments)))


# === SQL ===
def test_sql_revenue_by_customer_and_year():
    result=_call("sales_summary",customer_id="C-1003",year=2026)
    assert result["transactions"]==4
    assert result["revenue_usd"]==28559.8


def test_sql_units_by_sku():
    result=_call("sales_summary",sku="KRN-900X")
    assert result["units"]==5
    assert result["source_ref"]=="[SQL:sales]"


def test_sql_year_without_sales_returns_zero():
    result=_call("sales_summary",customer_id="C-1003",year=2025)
    assert result["ok"] is True
    assert result["transactions"]==0 and result["revenue_usd"]==0


# === Tools ===
def test_tool_customer_available_credit():
    result=_call("get_customer",customer_id="C-1003")
    assert result["available_credit_usd"]==20000


def test_tool_unknown_customer_is_recoverable_error():
    result=_call("get_customer",customer_id="C-0000")
    assert result["ok"] is False and result["error_type"]=="not_found"


def test_tool_release_review_by_amount():
    result=_call("calculate_release",customer_id="C-1003",sku="KRN-900X",quantity=7)
    assert result["decision"]=="REVIEW"
    assert len(result["reasons"])==1


def test_tool_release_rejects_insufficient_stock():
    result=_call("calculate_release",customer_id="C-1003",sku="CYC-3DX",quantity=15)
    assert result["decision"]=="REJECT"
