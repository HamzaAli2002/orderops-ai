from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import aliased
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Negotiation, Order, Customer, OrderItem, Product
from app.schemas import NegotiationHistoryOut

router = APIRouter()

AltProduct = aliased(Product)
OriginalProduct = aliased(Product)


@router.get("", response_model=list[NegotiationHistoryOut])
async def list_negotiations(limit: int = 50, db: AsyncSession = Depends(get_db)):
    """Full negotiation history across every order, newest first."""
    stmt = (
        select(
            Negotiation,
            Customer.name.label("customer_name"),
            OriginalProduct.name.label("original_product_name"),
            AltProduct.name.label("alternative_product_name"),
        )
        .join(Order, Negotiation.order_id == Order.id)
        .join(Customer, Order.customer_id == Customer.id)
        .join(OrderItem, Negotiation.original_item_id == OrderItem.id)
        .join(OriginalProduct, OrderItem.product_id == OriginalProduct.id)
        .join(AltProduct, Negotiation.alternative_product_id == AltProduct.id)
        .order_by(Negotiation.message_sent_at.desc())
        .limit(limit)
    )
    result = await db.execute(stmt)

    history = []
    for negotiation, customer_name, original_name, alt_name in result.all():
        history.append(
            NegotiationHistoryOut(
                id=negotiation.id,
                order_id=negotiation.order_id,
                customer_name=customer_name,
                original_product_name=original_name,
                alternative_product_name=alt_name,
                discount_pct=negotiation.discount_pct,
                channel=negotiation.channel.value,
                customer_response=negotiation.customer_response.value,
                message_sent_at=negotiation.message_sent_at,
                responded_at=negotiation.responded_at,
            )
        )
    return history
