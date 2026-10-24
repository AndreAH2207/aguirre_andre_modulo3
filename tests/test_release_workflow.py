from release_workflow import build_graph, route_after_evaluation, route_after_validation


def fake_extractor(customer_id, sku, quantity):
    """Replaces the LLM node: returns fixed fields, as the extractor would."""
    def extract(state):
        return {"customer_id": customer_id, "sku": sku, "quantity": quantity, "status": "extracted"}
    return extract


def run(customer_id, sku, quantity):
    graph = build_graph(extractor=fake_extractor(customer_id, sku, quantity))
    return graph.invoke({"request_text": "test"})


def test_direct_route_releases_order():
    result = run("C-1003", "KRN-900X", 4)
    assert result["decision"] == "RELEASE"
    assert result["status"] == "released"
    assert result["available_credit_usd"] == 20000


def test_review_route_goes_to_finance():
    result = run("C-1003", "KRN-900X", 9)
    assert result["decision"] == "REVIEW"
    assert result["status"] == "pending_review"
    assert result["projected_exposure_usd"] == 32054.5


def test_insufficient_stock_exits_before_credit_check():
    result = run("C-1003", "CYC-3DX", 15)
    assert result["status"] == "rejected"
    assert "credit_status" not in result


def test_unknown_customer_is_rejected():
    result = run("C-0000", "KRN-900X", 1)
    assert result["status"] == "rejected"
    assert result["reasons"] == ["Customer not found"]


def test_missing_data_is_blocked():
    def extract(state):
        return {"status": "blocked", "message": "Request blocked: missing customer_id."}
    result = build_graph(extractor=extract).invoke({"request_text": "test"})
    assert result["status"] == "blocked"


def test_conditional_edges():
    assert route_after_validation({"status": "rejected"}) == "issue_release"
    assert route_after_validation({"status": "validated"}) == "fetch_credit_profile"
    assert route_after_evaluation({"decision": "REVIEW"}) == "finance_review"
    assert route_after_evaluation({"decision": "RELEASE"}) == "issue_release"
