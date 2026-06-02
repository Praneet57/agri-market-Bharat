from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum

class UserRole(str, Enum):
    farmer = "farmer"
    buyer = "buyer"

class UserRegister(BaseModel):
    full_name: str = Field(..., min_length=2)
    phone: str = Field(..., min_length=10)
    email: Optional[EmailStr] = None
    password: str = Field(..., min_length=6)
    role: UserRole
    village: Optional[str] = None
    district: Optional[str] = None
    state: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None

class UserLogin(BaseModel):
    phone: str
    password: str

class UserOut(BaseModel):
    id: int; full_name: str; phone: str; email: Optional[str]
    role: str; village: Optional[str]; district: Optional[str]; state: Optional[str]
    latitude: Optional[float]; longitude: Optional[float]
    profile_image: Optional[str]; bio: Optional[str]; is_verified: bool; created_at: datetime
    class Config: from_attributes = True

class Token(BaseModel):
    access_token: str; refresh_token: str; token_type: str = "bearer"; user: UserOut

class UserUpdate(BaseModel):
    full_name: Optional[str] = None; email: Optional[EmailStr] = None
    bio: Optional[str] = None; village: Optional[str] = None
    district: Optional[str] = None; state: Optional[str] = None
    latitude: Optional[float] = None; longitude: Optional[float] = None

class ProductCreate(BaseModel):
    name: str; category: str; description: Optional[str] = None
    quantity_kg: float = Field(..., gt=0); price_per_kg: float = Field(..., gt=0)
    min_order_kg: float = 1.0; district: Optional[str] = None
    latitude: Optional[float] = None; longitude: Optional[float] = None
    is_organic: bool = False; harvest_date: Optional[datetime] = None

class ProductUpdate(BaseModel):
    name: Optional[str]=None; description: Optional[str]=None
    quantity_kg: Optional[float]=None; price_per_kg: Optional[float]=None
    min_order_kg: Optional[float]=None; is_organic: Optional[bool]=None; status: Optional[str]=None

class ProductOut(BaseModel):
    id: int; farmer_id: int; name: str; category: str; description: Optional[str]
    quantity_kg: float; price_per_kg: float; min_order_kg: float; status: str
    district: Optional[str]; latitude: Optional[float]; longitude: Optional[float]
    image_url: Optional[str]; is_organic: bool; views_count: int; created_at: datetime
    distance_km: Optional[float] = None
    class Config: from_attributes = True

class DemandCreate(BaseModel):
    product_name: str; category: str; description: Optional[str] = None
    quantity_kg: float = Field(..., gt=0); max_price_per_kg: float = Field(..., gt=0)
    district: Optional[str]=None; delivery_address: Optional[str]=None
    latitude: Optional[float]=None; longitude: Optional[float]=None
    required_by: Optional[datetime]=None

class DemandOut(BaseModel):
    id: int; buyer_id: int; product_name: str; category: str; description: Optional[str]
    quantity_kg: float; max_price_per_kg: float; status: str; district: Optional[str]
    required_by: Optional[datetime]; created_at: datetime
    class Config: from_attributes = True

class OrderCreate(BaseModel):
    product_id: Optional[int]=None; demand_id: Optional[int]=None; farmer_id: int
    quantity_kg: float = Field(..., gt=0); price_per_kg: float = Field(..., gt=0)
    delivery_address: Optional[str]=None; notes: Optional[str]=None

class OrderStatusUpdate(BaseModel):
    status: str; notes: Optional[str]=None

class OrderOut(BaseModel):
    id: int; order_number: str; farmer_id: int; buyer_id: int
    quantity_kg: float; price_per_kg: float; total_amount: float
    platform_fee: float; net_amount: float; status: str
    delivery_address: Optional[str]; notes: Optional[str]; created_at: datetime
    class Config: from_attributes = True

class PaymentCreate(BaseModel):
    order_id: int

class PaymentVerify(BaseModel):
    razorpay_order_id: str; razorpay_payment_id: str; razorpay_signature: str

class MessageCreate(BaseModel):
    order_id: int; message: str; message_type: str = "text"

class MessageOut(BaseModel):
    id: int; order_id: int; sender_id: int; message: str
    message_type: str; is_read: bool; created_at: datetime
    class Config: from_attributes = True

class RatingCreate(BaseModel):
    order_id: int; rated_id: int; score: int = Field(..., ge=1, le=5)
    comment: Optional[str]=None

class RatingOut(BaseModel):
    id: int; order_id: int; rater_id: int; rated_id: int
    score: int; comment: Optional[str]; created_at: datetime
    class Config: from_attributes = True

Token.model_rebuild()
