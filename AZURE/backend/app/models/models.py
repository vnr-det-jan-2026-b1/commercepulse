"""SQLAlchemy ORM models for all CommercePulse tables."""
import uuid
from datetime import date, datetime
from typing import Optional

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    Boolean, Column, Date, DateTime, ForeignKey,
    Integer, Numeric, String, Text, BigInteger, JSON,
    UniqueConstraint, func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.session import Base


# ── helpers ────────────────────────────────────────────────────
def now():
    return datetime.utcnow()

def new_uuid():
    return str(uuid.uuid4())


# ── Seller ─────────────────────────────────────────────────────
class Seller(Base):
    __tablename__ = "sellers"

    seller_id   = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    seller_name = Column(Text, nullable=False)
    marketplace = Column(Text, nullable=False, default="multi")
    region      = Column(Text, nullable=False, default="IN")
    email       = Column(Text, unique=True)
    is_active   = Column(Boolean, nullable=False, default=True)
    created_at  = Column(DateTime(timezone=True), server_default=func.now())

    products   = relationship("Product", back_populates="seller", lazy="selectin")


# ── Product ────────────────────────────────────────────────────
class Product(Base):
    __tablename__ = "products"
    __table_args__ = (UniqueConstraint("seller_id", "sku", "marketplace"),)

    product_id   = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    seller_id    = Column(UUID(as_uuid=True), ForeignKey("sellers.seller_id", ondelete="CASCADE"), nullable=False)
    sku          = Column(Text, nullable=False)
    product_name = Column(Text, nullable=False)
    category     = Column(Text)
    sub_category = Column(Text)
    brand        = Column(Text)
    marketplace  = Column(Text)
    is_active    = Column(Boolean, nullable=False, default=True)
    created_at   = Column(DateTime(timezone=True), server_default=func.now())

    seller     = relationship("Seller", back_populates="products")


# ── Order ──────────────────────────────────────────────────────
class Order(Base):
    __tablename__ = "orders"

    order_id            = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    external_order_id   = Column(Text)
    seller_id           = Column(UUID(as_uuid=True), ForeignKey("sellers.seller_id", ondelete="CASCADE"), nullable=False)
    product_id          = Column(UUID(as_uuid=True), ForeignKey("products.product_id", ondelete="SET NULL"))
    marketplace         = Column(Text, nullable=False)
    order_status        = Column(Text, nullable=False)
    quantity            = Column(Integer, nullable=False, default=1)
    selling_price       = Column(Numeric(12, 2), nullable=False)
    cost_price          = Column(Numeric(12, 2))
    discount            = Column(Numeric(12, 2), default=0)
    tax                 = Column(Numeric(12, 2), default=0)
    shipping_fee        = Column(Numeric(12, 2), default=0)
    order_date          = Column(Date, nullable=False)
    delivery_date       = Column(Date)
    return_flag         = Column(Boolean, default=False)
    cancellation_reason = Column(Text)
    snapshot_date       = Column(Date, nullable=False, default=date.today)
    created_at          = Column(DateTime(timezone=True), server_default=func.now())


# ── InventorySnapshot ──────────────────────────────────────────
class InventorySnapshot(Base):
    __tablename__  = "inventory_snapshots"
    __table_args__ = (UniqueConstraint("seller_id", "product_id", "marketplace", "snapshot_date"),)

    id                = Column(BigInteger, primary_key=True, autoincrement=True)
    seller_id         = Column(UUID(as_uuid=True), ForeignKey("sellers.seller_id", ondelete="CASCADE"), nullable=False)
    product_id        = Column(UUID(as_uuid=True), ForeignKey("products.product_id", ondelete="CASCADE"), nullable=False)
    marketplace       = Column(Text, nullable=False)
    available_stock   = Column(Integer, nullable=False, default=0)
    reserved_stock    = Column(Integer, nullable=False, default=0)
    reorder_threshold = Column(Integer, default=10)
    days_of_stock     = Column(Numeric(6, 1))
    warehouse_location= Column(Text)
    snapshot_date     = Column(Date, nullable=False, default=date.today)
    created_at        = Column(DateTime(timezone=True), server_default=func.now())


# ── PricingSnapshot ────────────────────────────────────────────
class PricingSnapshot(Base):
    __tablename__  = "pricing_snapshots"
    __table_args__ = (UniqueConstraint("seller_id", "product_id", "marketplace", "snapshot_date"),)

    id                  = Column(BigInteger, primary_key=True, autoincrement=True)
    seller_id           = Column(UUID(as_uuid=True), ForeignKey("sellers.seller_id", ondelete="CASCADE"), nullable=False)
    product_id          = Column(UUID(as_uuid=True), ForeignKey("products.product_id", ondelete="CASCADE"), nullable=False)
    marketplace         = Column(Text, nullable=False)
    selling_price       = Column(Numeric(12, 2), nullable=False)
    cost_price          = Column(Numeric(12, 2))
    mrp                 = Column(Numeric(12, 2))
    commission_pct      = Column(Numeric(5, 2), default=0)
    commission_amount   = Column(Numeric(12, 2), default=0)
    discount_percentage = Column(Numeric(5, 2), default=0)
    net_margin          = Column(Numeric(12, 2))
    margin_pct          = Column(Numeric(5, 2))
    snapshot_date       = Column(Date, nullable=False, default=date.today)
    created_at          = Column(DateTime(timezone=True), server_default=func.now())


# ── TrafficMetric ──────────────────────────────────────────────
class TrafficMetric(Base):
    __tablename__  = "traffic_metrics"
    __table_args__ = (UniqueConstraint("seller_id", "product_id", "marketplace", "metric_date"),)

    id               = Column(BigInteger, primary_key=True, autoincrement=True)
    seller_id        = Column(UUID(as_uuid=True), ForeignKey("sellers.seller_id", ondelete="CASCADE"), nullable=False)
    product_id       = Column(UUID(as_uuid=True), ForeignKey("products.product_id", ondelete="CASCADE"), nullable=False)
    marketplace      = Column(Text, nullable=False)
    metric_date      = Column(Date, nullable=False, default=date.today)
    impressions      = Column(Integer, default=0)
    clicks           = Column(Integer, default=0)
    add_to_cart      = Column(Integer, default=0)
    orders           = Column(Integer, default=0)
    ad_spend         = Column(Numeric(12, 2), default=0)
    revenue_from_ads = Column(Numeric(12, 2), default=0)
    created_at       = Column(DateTime(timezone=True), server_default=func.now())


# ── LogisticsMetric ────────────────────────────────────────────
class LogisticsMetric(Base):
    __tablename__ = "logistics_metrics"

    id                 = Column(BigInteger, primary_key=True, autoincrement=True)
    order_id           = Column(UUID(as_uuid=True), ForeignKey("orders.order_id", ondelete="SET NULL"))
    seller_id          = Column(UUID(as_uuid=True), ForeignKey("sellers.seller_id", ondelete="CASCADE"), nullable=False)
    marketplace        = Column(Text, nullable=False)
    courier_name       = Column(Text)
    tracking_id        = Column(Text)
    fulfillment_type   = Column(Text, default="seller")
    warehouse_id       = Column(Text)
    dispatch_date      = Column(Date)
    expected_delivery  = Column(Date)
    actual_delivery    = Column(Date)
    shipping_time_days = Column(Integer)
    delivery_status    = Column(Text, nullable=False)
    rto_flag           = Column(Boolean, default=False)
    rto_reason         = Column(Text)
    snapshot_date      = Column(Date, nullable=False, default=date.today)
    created_at         = Column(DateTime(timezone=True), server_default=func.now())


# ── ProductEmbedding ──────────────────────────────────────────
class ProductEmbedding(Base):
    __tablename__  = "product_embeddings"
    __table_args__ = (UniqueConstraint("seller_id", "product_id", "embed_date", "embed_type"),)

    id           = Column(BigInteger, primary_key=True, autoincrement=True)
    seller_id    = Column(UUID(as_uuid=True), ForeignKey("sellers.seller_id", ondelete="CASCADE"), nullable=False)
    product_id   = Column(UUID(as_uuid=True), ForeignKey("products.product_id", ondelete="CASCADE"), nullable=False)
    embed_date   = Column(Date, nullable=False, default=date.today)
    embed_type   = Column(Text, nullable=False, default="daily_snapshot")
    summary_text = Column(Text, nullable=False)
    embedding    = Column(Vector(384), nullable=False)
    meta         = Column("metadata", JSON, default=dict)
    created_at   = Column(DateTime(timezone=True), server_default=func.now())


# ── InsightEmbedding ──────────────────────────────────────────
class InsightEmbedding(Base):
    __tablename__ = "insight_embeddings"

    id           = Column(BigInteger, primary_key=True, autoincrement=True)
    seller_id    = Column(UUID(as_uuid=True), ForeignKey("sellers.seller_id", ondelete="CASCADE"), nullable=False)
    insight_date = Column(Date, nullable=False, default=date.today)
    insight_type = Column(Text, nullable=False)
    insight_text = Column(Text, nullable=False)
    embedding    = Column(Vector(384), nullable=False)
    meta         = Column("metadata", JSON, default=dict)
    created_at   = Column(DateTime(timezone=True), server_default=func.now())
