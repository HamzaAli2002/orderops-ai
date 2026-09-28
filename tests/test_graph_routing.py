from app.workflow.graph import route_after_fraud_check, route_after_inventory, route_after_customer_response


def test_route_after_fraud_check_flagged():
    assert route_after_fraud_check({"risk_flagged": True}) == "flag_manual_audit"


def test_route_after_fraud_check_clear():
    assert route_after_fraud_check({"risk_flagged": False}) == "validate_inventory"


def test_route_after_inventory_out_of_stock():
    assert route_after_inventory({"out_of_stock_items": [{"order_item_id": "x"}]}) == "generate_alternative"


def test_route_after_inventory_all_in_stock():
    assert route_after_inventory({"out_of_stock_items": []}) == "finalize_order"


def test_route_after_customer_response_pending():
    from langgraph.graph import END
    assert route_after_customer_response({}) == END
