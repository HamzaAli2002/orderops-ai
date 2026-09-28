from typing import TypedDict, Optional


class OrderItemState(TypedDict):
    order_item_id: str
    product_id: str
    quantity: int
    in_stock: bool


class OrderState(TypedDict, total=False):
    order_id: str
    customer_id: str
    items: list[OrderItemState]

    # fraud check
    risk_score: float
    risk_flagged: bool

    # inventory validation
    out_of_stock_items: list[OrderItemState]

    # negotiation
    alternative_offer: Optional[dict]      # {order_item_id, alt_product_id, discount_pct}
    negotiation_id: Optional[str]
    negotiation_channel: Optional[str]     # "email" | "sms"

    # human-in-the-loop
    customer_response: Optional[str]       # None | "accepted" | "rejected" | "timeout"

    # terminal
    final_status: Optional[str]            # "fulfilled" | "refunded" | "cancelled" | "manual_audit"
