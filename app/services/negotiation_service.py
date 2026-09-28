from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models import Product


async def pick_alternative_product(db: AsyncSession, original_product_id: str) -> Product | None:
    """
    Find the best in-stock substitute for an out-of-stock product, matched by
    category. TODO: upgrade to embedding/tag similarity for better matches.
    """
    original = await db.get(Product, original_product_id)
    if original is None:
        return None

    result = await db.execute(
        select(Product)
        .where(Product.category == original.category)
        .where(Product.id != original.id)
        .where(Product.stock_qty > 0)
        .limit(1)
    )
    return result.scalar_one_or_none()


async def build_negotiation_email(db: AsyncSession, offer: dict, order_id: str, negotiation_id: str) -> tuple[str, str]:
    """
    Draft the customer-facing negotiation email, with Accept/Reject links
    pointing at GET /orders/{order_id}/respond. Clicking either link resumes
    the paused LangGraph run - no reply-parsing or inbound-email service
    needed. TODO: replace the templated body with a real LLM call
    (LangChain + settings.llm_provider) for a more personalized message.
    """
    alt_product = await db.get(Product, offer["alt_product_id"]) if offer.get("alt_product_id") else None
    alt_name = alt_product.name if alt_product else "a similar item"
    discount = offer["discount_pct"]

    base = settings.app_base_url.rstrip("/")
    accept_url = f"{base}/orders/{order_id}/respond?negotiation_id={negotiation_id}&decision=accepted"
    reject_url = f"{base}/orders/{order_id}/respond?negotiation_id={negotiation_id}&decision=rejected"

    subject = "One item in your order is out of stock - quick decision needed"

    html = f"""
    <html><body style="font-family: sans-serif; color: #1e293b;">
      <p>Hi,</p>
      <p>One of the items in your order is currently out of stock.
         We'd like to offer you <b>{alt_name}</b> instead, with a
         <b>{discount}% discount</b> on that item.</p>
      <p>
        <a href="{accept_url}"
           style="display:inline-block;padding:10px 20px;background:#3b82f6;
                  color:#ffffff;text-decoration:none;border-radius:4px;margin-right:10px;">
          Accept substitute
        </a>
        <a href="{reject_url}"
           style="display:inline-block;padding:10px 20px;background:#334155;
                  color:#ffffff;text-decoration:none;border-radius:4px;">
          Reject and refund me
        </a>
      </p>
      <p>If you don't respond within {settings.negotiation_response_timeout_hours} hours,
         your order will be automatically refunded.</p>
      <p>- OrderOps AI</p>
    </body></html>
    """
    return subject, html
