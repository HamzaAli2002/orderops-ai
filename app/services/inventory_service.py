from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Product


async def check_stock(db: AsyncSession, product_id: str, quantity: int) -> bool:
    """Return True if the product has enough stock for the requested quantity."""
    product = await db.get(Product, product_id)
    if product is None:
        return False
    return product.stock_qty >= quantity
