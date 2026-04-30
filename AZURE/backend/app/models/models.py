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
    seller_name = Column(Text, nullable=False, index=True)
    marketplace = Column(Text, nullable=False, default="multi")
    region      = Column(Text, nullable=False, default="IN")
    email       = Column(Text, unique=True, index=True)
    is_active   = Column(Boolean, nullable=False, default=True)
    created_at  = Column(DateTime(timezone=True), server_default=func.now())

    products   = relationship("Product", back_populates="seller", lazy="selectin")


# ── Product ────────────────────────────────────────────────────
class Product(Base):
    __tablename__ = "products"
    __table_args__ = (UniqueConstraint("seller_id", "sku", "marketplace"),)

    product_id   = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    seller_id    = Column(UUID(as_uuid=True), ForeignKey("sellers.seller_id", ondelete="CASCADE"), nullable=False, index=True)
    sku          = Column(Text, nullable=False, index=True)
    product_name = Column(Text, nullable=False, index=True)
    category     = Column(Text, index=True)
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
    external_order_id   = Column(Text, index=True)
    seller_id           = Column(UUID(as_uuid=True), ForeignKey("sellers.seller_id", ondelete="CASCADE"), nullable=False, index=True)
    product_id          = Column(UUID(as_uuid=True), ForeignKey("products.product_id", ondelete="SET NULL"), index=True)
    marketplace         = Column(Text, nullable=False, index=True)
    order_status        = Column(Text, nullable=False, index=True)
    quantity            = Column(Integer, nullable=False, default=1)
    selling_price       = Column(Numeric(12, 2), nullable=False)
    discount            = Column(Numeric(12, 2), default=0)
    tax                 = Column(Numeric(12, 2), default=0)
    shipping_fee        = Column(Numeric(12, 2), nullable=True, default=0)
    order_date          = Column(Date, nullable=False, index=True)
    delivery_date       = Column(Date)
    return_flag         = Column(Boolean, default=False, index=True)
    cancellation_reason = Column(Text)
    snapshot_date       = Column(Date, nullable=False, default=date.today, index=True)
    created_at          = Column(DateTime(timezone=True), server_default=func.now())


# ── InventorySnapshot ──────────────────────────────────────────
class InventorySnapshot(Base):
    __tablename__  = "inventory_snapshots"
    __table_args__ = (UniqueConstraint("seller_id", "product_id", "marketplace", "snapshot_date"),)

    id                = Column(BigInteger, primary_key=True, autoincrement=True)
    seller_id         = Column(UUID(as_uuid=True), ForeignKey("sellers.seller_id", ondelete="CASCADE"), nullable=False, index=True)
    product_id        = Column(UUID(as_uuid=True), ForeignKey("products.product_id", ondelete="CASCADE"), nullable=False, index=True)
    marketplace       = Column(Text, nullable=False, index=True)
    available_stock   = Column(Integer, nullable=False, default=0)
    reserved_stock    = Column(Integer, nullable=False, default=0)
    reorder_threshold = Column(Integer, default=10)
    days_of_stock     = Column(Numeric(6, 1))
    warehouse_location= Column(Text)
    snapshot_date     = Column(Date, nullable=False, default=date.today, index=True)
    created_at        = Column(DateTime(timezone=True), server_default=func.now())


# ── PricingSnapshot ────────────────────────────────────────────
class PricingSnapshot(Base):
    __tablename__  = "pricing_snapshots"
    __table_args__ = (UniqueConstraint("seller_id", "product_id", "marketplace", "snapshot_date"),)

    id                  = Column(BigInteger, primary_key=True, autoincrement=True)
    seller_id           = Column(UUID(as_uuid=True), ForeignKey("sellers.seller_id", ondelete="CASCADE"), nullable=False, index=True)
    product_id          = Column(UUID(as_uuid=True), ForeignKey("products.product_id", ondelete="CASCADE"), nullable=False, index=True)
    marketplace         = Column(Text, nullable=False, index=True)
    selling_price       = Column(Numeric(12, 2), nullable=False)
    cost_price          = Column(Numeric(12, 2))
    mrp                 = Column(Numeric(12, 2))
    commission_pct      = Column(Numeric(5, 2), default=0)
    commission_amount   = Column(Numeric(12, 2), default=0)
    discount_percentage = Column(Numeric(5, 2), default=0)
    snapshot_date       = Column(Date, nullable=False, default=date.today, index=True)
    created_at          = Column(DateTime(timezone=True), server_default=func.now())


# ── TrafficMetric ──────────────────────────────────────────────
class TrafficMetric(Base):
    __tablename__  = "traffic_metrics"
    __table_args__ = (UniqueConstraint("seller_id", "product_id", "marketplace", "metric_date"),)

    id               = Column(BigInteger, primary_key=True, autoincrement=True)
    seller_id        = Column(UUID(as_uuid=True), ForeignKey("sellers.seller_id", ondelete="CASCADE"), nullable=False, index=True)
    product_id       = Column(UUID(as_uuid=True), ForeignKey("products.product_id", ondelete="CASCADE"), nullable=False, index=True)
    marketplace      = Column(Text, nullable=False, index=True)
    metric_date      = Column(Date, nullable=False, default=date.today, index=True)
    impressions      = Column(Integer, default=0)
    clicks           = Column(Integer, default=0)
    sessions         = Column(Integer, default=0)
    page_views       = Column(Integer, default=0)
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


# ── AIProductAnalysis ──────────────────────────────────────────
class AIProductAnalysis(Base):
    __tablename__  = "ai_product_analyses"
    __table_args__ = (UniqueConstraint("seller_id", "product_id", "analysis_date"),)

    id                 = Column(BigInteger, primary_key=True, autoincrement=True)
    seller_id          = Column(UUID(as_uuid=True), ForeignKey("sellers.seller_id", ondelete="CASCADE"), nullable=False)
    product_id         = Column(UUID(as_uuid=True), ForeignKey("products.product_id", ondelete="CASCADE"), nullable=False)
    analysis_date      = Column(Date, nullable=False, default=date.today)
    
    product_metrics    = Column(JSON, nullable=False, default=dict)
    revenue_insights   = Column(JSON)
    ops_insights       = Column(JSON)
    marketing_insights = Column(JSON)
    market_insights    = Column(JSON)
    executive_summary  = Column(JSON)
    
    status             = Column(Text, nullable=False, default="pending")
    error_message      = Column(Text)
    
    created_at         = Column(DateTime(timezone=True), server_default=func.now())
    updated_at         = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
