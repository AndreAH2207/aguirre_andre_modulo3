"""Pure MCP client against the real server over stdio (no LLM)."""

import asyncio

import pytest
from mcp import Client

from bootstrap_db import bootstrap
from mcp_client_demo import server_parameters


@pytest.fixture(scope="module", autouse=True)
def database():
    bootstrap()


def run(coroutine_function):
    async def wrapper():
        async with Client(server_parameters()) as client:
            return await coroutine_function(client)
    return asyncio.run(wrapper())


def test_list_tools_exposes_only_business_capabilities():
    async def check(client):
        return {item.name for item in (await client.list_tools()).tools}
    names = run(check)
    assert names == {"get_customer_credit", "get_stock", "calculate_release", "sales_summary"}


def test_call_tool_release_decision():
    async def check(client):
        return await client.call_tool("calculate_release", {"customer_id": "C-1003", "sku": "KRN-900X", "quantity": 9})
    result = run(check).structured_content
    assert result["decision"] == "REVIEW"
    assert len(result["reasons"]) == 2


def test_call_tool_credit_profile_without_full_record():
    async def check(client):
        return await client.call_tool("get_customer_credit", {"customer_id": "C-1003"})
    result = run(check).structured_content
    assert result["available_credit_usd"] == 20000
    assert "name" not in result


def test_call_tool_unknown_customer():
    async def check(client):
        return await client.call_tool("get_customer_credit", {"customer_id": "C-0000"})
    assert run(check).structured_content["ok"] is False


def test_call_tool_sales_summary():
    async def check(client):
        return await client.call_tool("sales_summary", {"customer_id": "C-1003", "year": 2026})
    assert run(check).structured_content["revenue_usd"] == 28559.8


def test_read_credit_policy_resource():
    async def check(client):
        uris = {str(item.uri) for item in (await client.list_resources()).resources}
        policy = await client.read_resource("policy://credit")
        return uris, policy.contents[0].text
    uris, text = run(check)
    assert uris == {"policy://credit", "policy://release"}
    assert "Clientes en hold" in text
