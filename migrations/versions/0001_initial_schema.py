"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-09-18

"""
from alembic import op
import sqlalchemy as sa

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "customers",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        sa.Column("phone", sa.String(32), nullable=True),
        sa.Column("preferences", sa.JSON, nullable=False),
    )
    op.create_index("ix_customers_email", "customers", ["email"])

    op.create_table(
        "products",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("sku", sa.String(64), nullable=False, unique=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("stock_qty", sa.Integer, nullable=False, server_default="0"),
        sa.Column("price", sa.Float, nullable=False),
        sa.Column("category", sa.String(128), nullable=True),
        sa.Column("tags", sa.JSON, nullable=False),
    )
    op.create_index("ix_products_sku", "products", ["sku"])

    op.create_table(
        "orders",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("customer_id", sa.String(36), sa.ForeignKey("customers.id"), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "pending", "risk_flagged", "validating", "negotiating",
                "awaiting_response", "fulfilled", "refunded", "cancelled",
                name="order_status",
            ),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("risk_score", sa.Float, nullable=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now()),
    )
    op.create_index("ix_orders_customer_id", "orders", ["customer_id"])

    op.create_table(
        "order_items",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("order_id", sa.String(36), sa.ForeignKey("orders.id"), nullable=False),
        sa.Column("product_id", sa.String(36), sa.ForeignKey("products.id"), nullable=False),
        sa.Column("quantity", sa.Integer, nullable=False, server_default="1"),
        sa.Column("unit_price", sa.Float, nullable=False),
        sa.Column("stock_status", sa.String(32), nullable=False, server_default="unknown"),
    )
    op.create_index("ix_order_items_order_id", "order_items", ["order_id"])

    op.create_table(
        "negotiations",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("order_id", sa.String(36), sa.ForeignKey("orders.id"), nullable=False),
        sa.Column("original_item_id", sa.String(36), sa.ForeignKey("order_items.id"), nullable=False),
        sa.Column("alternative_product_id", sa.String(36), sa.ForeignKey("products.id"), nullable=False),
        sa.Column("discount_pct", sa.Float, nullable=False, server_default="0"),
        sa.Column("channel", sa.Enum("email", "sms", name="negotiation_channel"), nullable=False),
        sa.Column("message_sent_at", sa.DateTime, nullable=True),
        sa.Column(
            "customer_response",
            sa.Enum("pending", "accepted", "rejected", "timeout", name="negotiation_response"),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("responded_at", sa.DateTime, nullable=True),
    )
    op.create_index("ix_negotiations_order_id", "negotiations", ["order_id"])

    op.create_table(
        "audit_logs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("order_id", sa.String(36), sa.ForeignKey("orders.id"), nullable=False),
        sa.Column("event_type", sa.String(64), nullable=False),
        sa.Column("payload", sa.JSON, nullable=False),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )
    op.create_index("ix_audit_logs_order_id", "audit_logs", ["order_id"])


def downgrade() -> None:
    op.drop_table("audit_logs")
    op.drop_table("negotiations")
    op.drop_table("order_items")
    op.drop_table("orders")
    op.drop_table("products")
    op.drop_table("customers")
