from fastapi import APIRouter, Depends
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Negotiation, NegotiationResponse
from app.schemas import RevenueRecoveryMetric

router = APIRouter()


@router.get("/revenue-recovery", response_model=RevenueRecoveryMetric)
async def revenue_recovery(db: AsyncSession = Depends(get_db)):
    total = (await db.execute(select(func.count()).select_from(Negotiation))).scalar_one()
    accepted = (
        await db.execute(
            select(func.count()).select_from(Negotiation).where(
                Negotiation.customer_response == NegotiationResponse.ACCEPTED
            )
        )
    ).scalar_one()

    rate = (accepted / total) if total else 0.0
    return RevenueRecoveryMetric(total_negotiations=total, accepted=accepted, recovery_rate=round(rate, 4))
