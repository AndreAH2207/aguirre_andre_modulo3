import pytest
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command

import release_workflow
from release_workflow import build_graph, route_after_evaluation, route_after_validation


@pytest.fixture(autouse=True)
def reset_credit_attempts():
    release_workflow.credit_service_attempts.clear()


def fake_extractor(customer_id, sku, quantity):
    """Replaces the LLM node: returns fixed fields, as the extractor would."""
    def extract(state):
        return {"customer_id": customer_id, "sku": sku, "quantity": quantity, "status": "extracted"}
    return extract


def start(customer_id, sku, quantity, thread_id="t-1"):
    """Runs the graph with an in-memory checkpoint; returns the graph, config and result."""
    graph = build_graph(extractor=fake_extractor(customer_id, sku, quantity), checkpointer=InMemorySaver())
    config = {"configurable": {"thread_id": thread_id}}
    return graph, config, graph.invoke({"request_text": "test"}, config=config)


# === Hito 3: routes ===
def test_direct_route_releases_order():
    _, _, result = start("C-1003", "KRN-900X", 4)
    assert result["decision"] == "RELEASE"
    assert result["status"] == "released"
    assert "__interrupt__" not in result


def test_insufficient_stock_exits_before_credit_check():
    _, _, result = start("C-1003", "CYC-3DX", 15)
    assert result["status"] == "rejected"
    assert "credit_status" not in result


def test_unknown_customer_is_rejected():
    _, _, result = start("C-0000", "KRN-900X", 1)
    assert result["status"] == "rejected"
    assert result["reasons"] == ["Customer not found"]


def test_missing_data_is_blocked():
    def extract(state):
        return {"status": "blocked", "message": "Request blocked: missing customer_id."}
    graph = build_graph(extractor=extract, checkpointer=InMemorySaver())
    result = graph.invoke({"request_text": "test"}, config={"configurable": {"thread_id": "t-1"}})
    assert result["status"] == "blocked"


def test_conditional_edges():
    assert route_after_validation({"status": "rejected"}) == "issue_release"
    assert route_after_validation({"status": "validated"}) == "fetch_credit_profile"
    assert route_after_evaluation({"decision": "REVIEW"}) == "finance_review"
    assert route_after_evaluation({"decision": "RELEASE"}) == "issue_release"


# === Hito 4: pause, resume, retry ===
def test_review_route_pauses_with_credit_memo():
    graph, config, result = start("C-1003", "KRN-900X", 9)
    memo = result["__interrupt__"][0].value
    assert memo["projected_exposure_usd"] == 32054.5
    assert graph.get_state(config).next == ("finance_review",)


def test_resume_approve_releases_by_exception():
    graph, config, _ = start("C-1003", "KRN-900X", 9)
    result = graph.invoke(Command(resume={"decision": "approve", "reviewer": "ana"}), config=config)
    assert result["status"] == "released_by_exception"
    assert result["reviewer"] == "ana"


def test_resume_reject_rejects_by_finance():
    graph, config, _ = start("C-1003", "KRN-900X", 9)
    result = graph.invoke(Command(resume={"decision": "reject", "reviewer": "ana"}), config=config)
    assert result["status"] == "rejected_by_finance"


def test_invalid_finance_answer_pauses_again():
    graph, config, _ = start("C-1003", "KRN-900X", 9)
    result = graph.invoke(Command(resume={"decision": "no", "reviewer": "ana"}), config=config)
    assert "error" in result["__interrupt__"][0].value
    assert graph.get_state(config).next == ("finance_review",)
    result = graph.invoke(Command(resume={"decision": "reject", "reviewer": "ana"}), config=config)
    assert result["status"] == "rejected_by_finance"


def test_transient_credit_failure_is_retried(monkeypatch):
    monkeypatch.setenv("SIMULATE_CREDIT_TIMEOUT", "1")
    _, _, result = start("C-1003", "KRN-900X", 4)
    assert release_workflow.credit_service_attempts["C-1003"] == 2
    assert result["status"] == "released"


def test_business_rejection_is_not_retried(monkeypatch):
    monkeypatch.setenv("SIMULATE_CREDIT_TIMEOUT", "1")
    _, _, result = start("C-1003", "CYC-3DX", 15)
    assert result["status"] == "rejected"
    assert "C-1003" not in release_workflow.credit_service_attempts


def test_credit_service_down_keeps_order_at_failed_node(monkeypatch):
    class CreditServiceDown(dict):
        def __getitem__(self, key):
            raise TimeoutError("Credit service down")
    monkeypatch.setattr(release_workflow, "CUSTOMERS", CreditServiceDown(release_workflow.CUSTOMERS))
    graph = build_graph(extractor=fake_extractor("C-1003", "KRN-900X", 4), checkpointer=InMemorySaver())
    config = {"configurable": {"thread_id": "t-1"}}
    with pytest.raises(TimeoutError):
        graph.invoke({"request_text": "test"}, config=config)
    assert release_workflow.credit_service_attempts["C-1003"] == 3
    assert graph.get_state(config).next == ("fetch_credit_profile",)
