from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base

class Order(Base):
    __tablename__ = "orders"
    id = Column(Integer, primary_key=True, index=True)
    order_number = Column(String(50), unique=True, nullable=False, index=True)
    farmer_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    buyer_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=True)
    demand_id = Column(Integer, ForeignKey("demands.id"), nullable=True)
    quantity_kg = Column(Float, nullable=False)
    price_per_kg = Column(Float, nullable=False)
    total_amount = Column(Float, nullable=False)
    platform_fee = Column(Float, default=0.0)
    net_amount = Column(Float, nullable=False)
    status = Column(String(30), default="pending")
    delivery_address = Column(Text, nullable=False)
    district = Column(String(100), nullable=False)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    notes = Column(Text, nullable=True)
    accepted_at = Column(DateTime(timezone=True), nullable=True)
    paid_at = Column(DateTime(timezone=True), nullable=True)
    delivered_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    farmer = relationship("User", foreign_keys=[farmer_id], back_populates="farmer_orders")
    buyer = relationship("User", foreign_keys=[buyer_id], back_populates="buyer_orders")
    product = relationship("Product", back_populates="orders")
    demand = relationship("Demand", back_populates="orders")
    payment = relationship("Payment", back_populates="order", uselist=False)
    agreement = relationship("Agreement", back_populates="order", uselist=False)
    chat_messages = relationship("ChatMessage", back_populates="order")
    ratings = relationship("Rating", back_populates="order")
