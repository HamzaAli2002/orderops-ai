"""
StateGraph wiring for OrderOps AI.

Flow:
  check_fraud_risk
      -> flag_manual_audit                     (if risk_flagged)
      -> validate_inventory                     (else)

  validate_inventory
      -> finalize_order                         (if nothing out of stock)
      -> generate_alternative                   (if out_of_stock_items present)

  generate_alternative -> send_negotiation -> await_customer_response

  await_customer_response
      -> finalize_order                         (once resumed with a decision)

await_customer_response calls langgraph.types.interrupt() - this is a real
pause: the run suspends there and POST /orders returns with the order still
in AWAITING_RESPONSE. Resuming (via Command(resume=decision), triggered by
the /orders/{id}/customer-response webhook or the /orders/{id}/respond email
link) continues the SAME run from that exact point - check_fraud_risk,
validate_inventory, etc. are NOT re-executed.

The checkpointer is an in-memory MemorySaver, built once as a module-level
singleton so a paused run survives between the initial POST /orders call and
the later resume call, as long as they happen in the same process. This
keeps the skeleton dependency-free (no separate checkpoint database/driver)
- swap in a persistent checkpointer (SQLite/Redis/Postgres) before
production, since a paused negotiation is lost if the API process restarts.
"""

from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

from app.workflow.state import OrderState
from app.workflow.nodes import (
    check_fraud_risk,
    validate_inventory,
    generate_alternative,
    send_negotiation,
    await_customer_response,
    finalize_order,
    flag_manual_audit,
)


def route_after_fraud_check(state: OrderState) -> str:
    return "flag_manual_audit" if state.get("risk_flagged") else "validate_inventory"


def route_after_inventory(state: OrderState) -> str:
    return "generate_alternative" if state.get("out_of_stock_items") else "finalize_order"


def route_after_customer_response(state: OrderState) -> str:
    return "finalize_order" if state.get("customer_response") else END


def build_graph() -> StateGraph:
    graph = StateGraph(OrderState)

    graph.add_node("check_fraud_risk", check_fraud_risk)
    graph.add_node("flag_manual_audit", flag_manual_audit)
    graph.add_node("validate_inventory", validate_inventory)
    graph.add_node("generate_alternative", generate_alternative)
    graph.add_node("send_negotiation", send_negotiation)
    graph.add_node("await_customer_response", await_customer_response)
    graph.add_node("finalize_order", finalize_order)

    graph.add_edge(START, "check_fraud_risk")

    graph.add_conditional_edges(
        "check_fraud_risk",
        route_after_fraud_check,
        {"flag_manual_audit": "flag_manual_audit", "validate_inventory": "validate_inventory"},
    )

    graph.add_conditional_edges(
        "validate_inventory",
        route_after_inventory,
        {"generate_alternative": "generate_alternative", "finalize_order": "finalize_order"},
    )

    graph.add_edge("generate_alternative", "send_negotiation")
    graph.add_edge("send_negotiation", "await_customer_response")

    graph.add_conditional_edges(
        "await_customer_response",
        route_after_customer_response,
        {"finalize_order": "finalize_order", END: END},
    )

    graph.add_edge("finalize_order", END)
    graph.add_edge("flag_manual_audit", END)

    return graph


_checkpointer = MemorySaver()
_compiled_graph = None


def get_compiled_graph():
    """Build the compiled graph once and reuse it (singleton) so paused runs stay resumable."""
    global _compiled_graph
    if _compiled_graph is None:
        _compiled_graph = build_graph().compile(checkpointer=_checkpointer)
    return _compiled_graph
