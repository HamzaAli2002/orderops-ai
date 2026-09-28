"""
LangGraph node implementations for the OrderOps AI order-resolution flow.

Each node takes the current OrderState, performs one step of work
(usually a DB call), and returns a partial state update dict, which
LangGraph merges into the running state.
"""

from datetime import datetime, timezone

from langgraph.types import interrupt

from app.config import settings
from app.database import AsyncSessionLocal
from app.models import (
    Order,
    OrderItem,
    Customer,
    Negotiation,
    AuditLog,
    OrderStatus,
    NegotiationChannel,
    NegotiationResponse,
)
from app.workflow.state import OrderState
from app.services.fraud_service import compute_risk_score
from app.services.inventory_service import check_stock
from app.services.negotiation_service import pick_alternative_product, build_negotiation_email
from app.services.notification_service import send_email


async def check_fraud_risk(state: OrderState) -> dict:
    """Compute a risk score for the order; flag high-risk orders for manual audit."""
    risk_score = await compute_risk_score(state["order_id"], state["customer_id"])
    risk_flagged = risk_score >= settings.fraud_risk_threshold

    async with AsyncSessionLocal() as db:
        order = await db.get(Order, state["order_id"])
        order.risk_score = risk_score
        order.status = OrderStatus.RISK_FLAGGED if risk_flagged else OrderStatus.VALIDATING
        db.add(AuditLog(order_id=order.id, event_type="fraud_check", payload={"risk_score": risk_score}))
        await db.commit()

    return {"risk_score": risk_score, "risk_flagged": risk_flagged}


async def validate_inventory(state: OrderState) -> dict:
    """Check live stock for every item on the order."""
    updated_items = []
    out_of_stock = []

    async with AsyncSessionLocal() as db:
        for item in state["items"]:
            in_stock = await check_stock(db, item["product_id"], item["quantity"])
            item = {**item, "in_stock": in_stock}
            updated_items.append(item)
            if not in_stock:
                out_of_stock.append(item)

        order = await db.get(Order, state["order_id"])
        order.status = OrderStatus.VALIDATING
        db.add(AuditLog(
            order_id=order.id,
            event_type="inventory_validation",
            payload={"out_of_stock_count": len(out_of_stock)},
        ))
        await db.commit()

    return {"items": updated_items, "out_of_stock_items": out_of_stock}


async def generate_alternative(state: OrderState) -> dict:
    """Pick a substitute product and draft the negotiation offer for the first out-of-stock item."""
    target_item = state["out_of_stock_items"][0]

    async with AsyncSessionLocal() as db:
        alt_product = await pick_alternative_product(db, target_item["product_id"])

    offer = {
        "order_item_id": target_item["order_item_id"],
        "alt_product_id": alt_product.id if alt_product else None,
        "discount_pct": settings.negotiation_discount_pct,
    }
    return {"alternative_offer": offer}


async def send_negotiation(state: OrderState) -> dict:
    """Persist the negotiation and email the offer to the customer (with Accept/Reject links)."""
    offer = state["alternative_offer"]

    async with AsyncSessionLocal() as db:
        order = await db.get(Order, state["order_id"])
        customer = await db.get(Customer, order.customer_id)

        negotiation = Negotiation(
            order_id=state["order_id"],
            original_item_id=offer["order_item_id"],
            alternative_product_id=offer["alt_product_id"],
            discount_pct=offer["discount_pct"],
            channel=NegotiationChannel.EMAIL,
            message_sent_at=datetime.now(timezone.utc),
            customer_response=NegotiationResponse.PENDING,
        )
        db.add(negotiation)
        order.status = OrderStatus.AWAITING_RESPONSE
        await db.commit()
        await db.refresh(negotiation)

        subject, html_body = await build_negotiation_email(db, offer, order.id, negotiation.id)
        await send_email(customer.email, subject, html_body)

        db.add(AuditLog(order_id=order.id, event_type="negotiation_sent", payload={"negotiation_id": negotiation.id}))
        await db.commit()

    return {"negotiation_id": negotiation.id, "negotiation_channel": "email"}


async def await_customer_response(state: OrderState) -> dict:
    """
    True pause point: interrupt() suspends this graph run right here and
    returns control to the caller. The run only continues past this line
    when someone resumes it with Command(resume=<decision>) - typically via
    the /orders/{id}/customer-response webhook or the /orders/{id}/respond
    email link - and it resumes exactly here, without re-running any earlier
    node (fraud check, inventory validation, negotiation are NOT re-executed).
    """
    decision = interrupt({
        "reason": "awaiting_customer_response",
        "order_id": state["order_id"],
        "negotiation_id": state.get("negotiation_id"),
    })
    return {"customer_response": decision}


async def finalize_order(state: OrderState) -> dict:
    """Route the order to fulfillment, item update, or refund based on the customer's decision."""
    decision = state.get("customer_response")

    async with AsyncSessionLocal() as db:
        order = await db.get(Order, state["order_id"])

        if decision == "accepted":
            offer = state["alternative_offer"]
            item = await db.get(OrderItem, offer["order_item_id"])
            item.product_id = offer["alt_product_id"]
            item.stock_status = "substituted"
            order.status = OrderStatus.FULFILLED
            final_status = "fulfilled"
        elif decision in ("rejected", "timeout"):
            order.status = OrderStatus.REFUNDED
            final_status = "refunded"
        else:
            order.status = OrderStatus.FULFILLED
            final_status = "fulfilled"

        db.add(AuditLog(order_id=order.id, event_type="order_finalized", payload={"final_status": final_status}))
        await db.commit()

    return {"final_status": final_status}


async def flag_manual_audit(state: OrderState) -> dict:
    async with AsyncSessionLocal() as db:
        order = await db.get(Order, state["order_id"])
        order.status = OrderStatus.RISK_FLAGGED
        db.add(AuditLog(order_id=order.id, event_type="manual_audit_flagged", payload={}))
        await db.commit()

    return {"final_status": "manual_audit"}
