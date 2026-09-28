from fastapi import FastAPI

from app.api import orders, metrics, customers, products, negotiations

app = FastAPI(title="OrderOps AI", version="0.1.0")

app.include_router(orders.router, prefix="/orders", tags=["orders"])
app.include_router(metrics.router, prefix="/metrics", tags=["metrics"])
app.include_router(customers.router, prefix="/customers", tags=["customers"])
app.include_router(products.router, prefix="/products", tags=["products"])
app.include_router(negotiations.router, prefix="/negotiations", tags=["negotiations"])


@app.get("/health")
async def health():
    return {"status": "ok"}
