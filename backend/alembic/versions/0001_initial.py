"""Initial schema
Revision ID: 0001_initial
Revises: 
Create Date: 2024-01-01 00:00:00
"""
from alembic import op
import sqlalchemy as sa

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    op.create_table("users",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("full_name", sa.String(100), nullable=False),
        sa.Column("phone", sa.String(20), unique=True, nullable=False),
        sa.Column("email", sa.String(150), unique=True, nullable=True),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("role", sa.String(20), nullable=False),
        sa.Column("is_active", sa.Boolean, server_default="true"),
        sa.Column("is_verified", sa.Boolean, server_default="false"),
        sa.Column("latitude", sa.Float), sa.Column("longitude", sa.Float),
        sa.Column("village", sa.String(100)), sa.Column("district", sa.String(100)), sa.Column("state", sa.String(100)),
        sa.Column("profile_image", sa.String(500)), sa.Column("bio", sa.String(500)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True)))

    op.create_table("products",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("farmer_id", sa.Integer, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(150), nullable=False), sa.Column("category", sa.String(100), nullable=False),
        sa.Column("description", sa.Text), sa.Column("quantity_kg", sa.Float, nullable=False),
        sa.Column("price_per_kg", sa.Float, nullable=False), sa.Column("min_order_kg", sa.Float, server_default="1"),
        sa.Column("status", sa.String(30), server_default="available"),
        sa.Column("latitude", sa.Float), sa.Column("longitude", sa.Float), sa.Column("district", sa.String(100)),
        sa.Column("image_url", sa.String(500)), sa.Column("harvest_date", sa.DateTime(timezone=True)),
        sa.Column("expiry_date", sa.DateTime(timezone=True)),
        sa.Column("is_organic", sa.Boolean, server_default="false"), sa.Column("is_active", sa.Boolean, server_default="true"),
        sa.Column("views_count", sa.Integer, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True)))

    op.create_table("demands",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("buyer_id", sa.Integer, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("product_name", sa.String(150), nullable=False), sa.Column("category", sa.String(100), nullable=False),
        sa.Column("description", sa.Text), sa.Column("quantity_kg", sa.Float, nullable=False),
        sa.Column("max_price_per_kg", sa.Float, nullable=False),
        sa.Column("latitude", sa.Float), sa.Column("longitude", sa.Float), sa.Column("district", sa.String(100)),
        sa.Column("delivery_address", sa.Text), sa.Column("status", sa.String(30), server_default="open"),
        sa.Column("required_by", sa.DateTime(timezone=True)), sa.Column("is_active", sa.Boolean, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True)))

    op.create_table("orders",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("order_number", sa.String(50), unique=True, nullable=False),
        sa.Column("farmer_id", sa.Integer, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("buyer_id", sa.Integer, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("product_id", sa.Integer, sa.ForeignKey("products.id")),
        sa.Column("demand_id", sa.Integer, sa.ForeignKey("demands.id")),
        sa.Column("quantity_kg", sa.Float, nullable=False), sa.Column("price_per_kg", sa.Float, nullable=False),
        sa.Column("total_amount", sa.Float, nullable=False), sa.Column("platform_fee", sa.Float, server_default="0"),
        sa.Column("net_amount", sa.Float, nullable=False), sa.Column("status", sa.String(30), server_default="pending"),
        sa.Column("delivery_address", sa.Text), sa.Column("notes", sa.Text),
        sa.Column("accepted_at", sa.DateTime(timezone=True)), sa.Column("paid_at", sa.DateTime(timezone=True)),
        sa.Column("delivered_at", sa.DateTime(timezone=True)), sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True)))

    op.create_table("payments",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("order_id", sa.Integer, sa.ForeignKey("orders.id", ondelete="CASCADE"), unique=True, nullable=False),
        sa.Column("razorpay_order_id", sa.String(100)), sa.Column("razorpay_payment_id", sa.String(100)),
        sa.Column("razorpay_signature", sa.String(300)), sa.Column("amount", sa.Float, nullable=False),
        sa.Column("currency", sa.String(10), server_default="INR"), sa.Column("status", sa.String(30), server_default="created"),
        sa.Column("payment_method", sa.String(50)), sa.Column("escrow_active", sa.Boolean, server_default="false"),
        sa.Column("escrow_released_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True)))

    op.create_table("agreements",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("order_id", sa.Integer, sa.ForeignKey("orders.id", ondelete="CASCADE"), unique=True, nullable=False),
        sa.Column("pdf_url", sa.String(500)), sa.Column("pdf_key", sa.String(300)),
        sa.Column("farmer_signed", sa.Boolean, server_default="false"), sa.Column("buyer_signed", sa.Boolean, server_default="false"),
        sa.Column("farmer_signed_at", sa.DateTime(timezone=True)), sa.Column("buyer_signed_at", sa.DateTime(timezone=True)),
        sa.Column("terms", sa.Text), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True)))

    op.create_table("chat_messages",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("order_id", sa.Integer, sa.ForeignKey("orders.id", ondelete="CASCADE"), nullable=False),
        sa.Column("sender_id", sa.Integer, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("message", sa.Text, nullable=False), sa.Column("message_type", sa.String(20), server_default="text"),
        sa.Column("file_url", sa.String(500)), sa.Column("is_read", sa.Boolean, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")))

    op.create_table("ratings",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("order_id", sa.Integer, sa.ForeignKey("orders.id", ondelete="CASCADE"), nullable=False),
        sa.Column("rater_id", sa.Integer, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("rated_id", sa.Integer, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("score", sa.Integer, nullable=False), sa.Column("comment", sa.Text),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")))

def downgrade():
    for t in ["ratings","chat_messages","agreements","payments","orders","demands","products","users"]:
        op.drop_table(t)
