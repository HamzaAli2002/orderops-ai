from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from langgraph.types import Command

from app.database import get_db
from app.models import Order, OrderItem, Negotiation, NegotiationResponse
from app.schemas import OrderCreate, OrderOut, CustomerResponseIn, NegotiationOut
from app.workflow.graph import get_compiled_graph
from app.workflow.state import OrderState

router = APIRouter()


@router.post("", response_model=OrderOut)
async def create_order(payload: OrderCreate, db: AsyncSession = Depends(get_db)):
    order = Order(customer_id=payload.customer_id)
    db.add(order)
    await db.flush()

    items = []
    for item_in in payload.items:
        item = OrderItem(order_id=order.id, product_id=item_in.product_id, quantity=item_in.quantity, unit_price=0)
        db.add(item)
        items.append(item)

    await db.commit()
    await db.refresh(order)

    order_id = order.id  # capture as a plain string before expiring anything below

    initial_state: OrderState = {
        "order_id": order_id,
        "customer_id": order.customer_id,
        "items": [
            {"order_item_id": i.id, "product_id": i.product_id, "quantity": i.quantity, "in_stock": False}
            for i in items
        ],
    }

    graph = get_compiled_graph()
    config = {"configurable": {"thread_id": order_id}}
    await graph.ainvoke(initial_state, config=config)

    # The graph's nodes committed changes through their own DB sessions, so
    # this session's identity map may be holding a stale copy of `order` -
    # expire it before re-querying so we return the current status.
    db.expire_all()

    result = await db.execute(
        select(Order).options(selectinload(Order.items)).where(Order.id == order_id)
    )
    return result.scalar_one()


@router.get("/{order_id}", response_model=OrderOut)
async def get_order(order_id: str, db: AsyncSession = Depends(get_db)):
    order = await db.get(Order, order_id, options=[selectinload(Order.items)])
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order


@router.get("/{order_id}/negotiations", response_model=list[NegotiationOut])
async def get_negotiations(order_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Negotiation).where(Negotiation.order_id == order_id))
    return result.scalars().all()


async def _apply_customer_response(db: AsyncSession, order_id: str, negotiation_id: str, decision: str) -> None:
    """Shared logic: record the decision, then resume the paused LangGraph run."""
    negotiation = await db.get(Negotiation, negotiation_id)
    if not negotiation or negotiation.order_id != order_id:
        raise HTTPException(status_code=404, detail="Negotiation not found")

    if decision not in ("accepted", "rejected"):
        raise HTTPException(status_code=400, detail="decision must be 'accepted' or 'rejected'")

    # Already responded (e.g. link clicked twice) - don't re-run the graph.
    if negotiation.customer_response != NegotiationResponse.PENDING:
        return

    negotiation.customer_response = NegotiationResponse(decision)
    negotiation.responded_at = datetime.now(timezone.utc)
    await db.commit()

    graph = get_compiled_graph()
    config = {"configurable": {"thread_id": order_id}}
    await graph.ainvoke(Command(resume=decision), config=config)


@router.post("/{order_id}/customer-response")
async def customer_response(order_id: str, payload: CustomerResponseIn, db: AsyncSession = Depends(get_db)):
    """Programmatic version (used by the Streamlit dashboard's Accept/Reject buttons)."""
    await _apply_customer_response(db, order_id, payload.negotiation_id, payload.decision)
    return {"status": "resumed", "decision": payload.decision}


@router.get("/{order_id}/respond", response_class=HTMLResponse)
async def customer_response_link(
    order_id: str, negotiation_id: str, decision: str, db: AsyncSession = Depends(get_db)
):
    """
    Clickable-link version - this is what the Accept/Reject buttons in the
    negotiation email point at. A GET request so a plain browser click (no
    JS, no auth) is enough to resolve it. Returns a simple confirmation page.
    """
    await _apply_customer_response(db, order_id, negotiation_id, decision)

    if decision == "accepted":
        message = "Thanks! We've updated your order with the substitute item."
    else:
        message = "Got it - your order will be refunded."

    return f"""
    <html><body style="font-family: sans-serif; background:#020617; color:#e2e8f0;
        display:flex; align-items:center; justify-content:center; height:100vh; margin:0;">
      <div style="text-align:center;">
        <h2>{message}</h2>
        <p style="color:#94a3b8;">You can close this tab now.</p>
      </div>
    </body></html>
    """
