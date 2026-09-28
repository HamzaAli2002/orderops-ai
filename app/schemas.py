from pydantic import BaseModel
from datetime import datetime


class OrderItemCreate(BaseModel):
    product_id: str
    quantity: int


class OrderCreate(BaseModel):
    customer_id: str
    items: list[OrderItemCreate]


class OrderItemOut(BaseModel):
    id: str
    product_id: str
    quantity: int
    unit_price: float
    stock_status: str

    class Config:
        from_attributes = True


class OrderOut(BaseModel):
    id: str
    customer_id: str
    status: str
    risk_score: float | None
    created_at: datetime
    updated_at: datetime
    items: list[OrderItemOut]

    class Config:
        from_attributes = True


class CustomerResponseIn(BaseModel):
    negotiation_id: str
    decision: str  # "accepted" | "rejected"


class NegotiationOut(BaseModel):
    id: str
    order_id: str
    original_item_id: str
    alternative_product_id: str
    discount_pct: float
    channel: str
    customer_response: str
    message_sent_at: datetime | None
    responded_at: datetime | None

    class Config:
        from_attributes = True


class RevenueRecoveryMetric(BaseModel):
    total_negotiations: int
    accepted: int
    recovery_rate: float


class CustomerOut(BaseModel):
    id: str
    name: str
    email: str

    class Config:
        from_attributes = True


class ProductOut(BaseModel):
    id: str
    sku: str
    name: str
    stock_qty: int
    price: float
    category: str | None

    class Config:
        from_attributes = True


class NegotiationHistoryOut(BaseModel):
    id: str
    order_id: str
    customer_name: str
    original_product_name: str
    alternative_product_name: str
    discount_pct: float
    channel: str
    customer_response: str
    message_sent_at: datetime | None
    responded_at: datetime | None
