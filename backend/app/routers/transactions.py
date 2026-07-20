from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_
from typing import List, Optional
import uuid, hmac, hashlib
from datetime import datetime
from app.core.database import get_db
from app.core.config import settings
from app.core.security import get_current_user, require_buyer, require_farmer
from app.models.user import User
from app.models.demand import Demand
from app.models.order import Order
from app.models.payment import Payment, Agreement, Rating
from app.schemas import DemandCreate, DemandOut, OrderCreate, OrderOut, OrderStatusUpdate, PaymentCreate, PaymentVerify, RatingCreate, RatingOut

demand_router = APIRouter(prefix="/demands", tags=["Demands"])

@demand_router.post("/", response_model=DemandOut, status_code=201)
async def create_demand(data: DemandCreate, current_user: User = Depends(require_buyer), db: AsyncSession = Depends(get_db)):
    d = Demand(buyer_id=current_user.id, **data.model_dump()); db.add(d); await db.flush(); await db.refresh(d)
    return DemandOut.model_validate(d)

@demand_router.get("/", response_model=List[DemandOut])
async def list_demands(category: Optional[str]=None, district: Optional[str]=None, limit: int=20, offset: int=0, db: AsyncSession=Depends(get_db)):
    q = select(Demand).where(Demand.status == "open", Demand.is_active == True)
    if category: q = q.where(Demand.category.ilike(f"%{category}%"))
    if district: q = q.where(Demand.district.ilike(f"%{district}%"))
    result = await db.execute(q.offset(offset).limit(limit))
    return [DemandOut.model_validate(d) for d in result.scalars().all()]

@demand_router.get("/my", response_model=List[DemandOut])
async def my_demands(current_user: User = Depends(require_buyer), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Demand).where(Demand.buyer_id == current_user.id))
    return [DemandOut.model_validate(d) for d in result.scalars().all()]

order_router = APIRouter(prefix="/orders", tags=["Orders"])

@order_router.post("/", response_model=OrderOut, status_code=201)
async def create_order(data: OrderCreate, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    total = round(data.quantity_kg * data.price_per_kg, 2)
    fee = round(total * 0.02, 2); net = round(total - fee, 2)
    order = Order(order_number=f"AGM-{uuid.uuid4().hex[:8].upper()}", buyer_id=current_user.id,
        farmer_id=data.farmer_id, product_id=data.product_id, demand_id=data.demand_id,
        quantity_kg=data.quantity_kg, price_per_kg=data.price_per_kg,
        total_amount=total, platform_fee=fee, net_amount=net,
        delivery_address=data.delivery_address, notes=data.notes)
    db.add(order); await db.flush(); await db.refresh(order)
    return OrderOut.model_validate(order)

@order_router.get("/", response_model=List[OrderOut])
async def list_orders(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Order).where(or_(Order.farmer_id==current_user.id, Order.buyer_id==current_user.id)).order_by(Order.created_at.desc()))
    return [OrderOut.model_validate(o) for o in result.scalars().all()]

@order_router.get("/{order_id}", response_model=OrderOut)
async def get_order(order_id: int, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Order).where(Order.id == order_id))
    o = result.scalar_one_or_none()
    if not o: raise HTTPException(404, "Order not found")
    if o.farmer_id != current_user.id and o.buyer_id != current_user.id: raise HTTPException(403, "Not your order")
    return OrderOut.model_validate(o)

@order_router.patch("/{order_id}/status", response_model=OrderOut)
async def update_order_status(order_id: int, data: OrderStatusUpdate, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Order).where(Order.id == order_id))
    o = result.scalar_one_or_none()
    if not o: raise HTTPException(404, "Order not found")
    allowed = {"pending":["accepted","rejected","cancelled"],"accepted":["payment_pending","cancelled"],
               "payment_pending":["paid","cancelled"],"paid":["in_transit"],"in_transit":["delivered"],
               "delivered":["completed","disputed"]}
    if data.status not in allowed.get(o.status, []):
        raise HTTPException(400, f"Cannot move from {o.status} to {data.status}")
    o.status = data.status
    if data.notes: o.notes = data.notes
    if data.status == "accepted": o.accepted_at = datetime.utcnow()
    elif data.status == "delivered": o.delivered_at = datetime.utcnow()
    elif data.status == "completed": o.completed_at = datetime.utcnow()
    await db.flush(); return OrderOut.model_validate(o)

payment_router = APIRouter(prefix="/payments", tags=["Payments"])

@payment_router.post("/create")
async def create_payment(data: PaymentCreate, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Order).where(Order.id == data.order_id))
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(404, "Order not found")
    if order.buyer_id != current_user.id:
        raise HTTPException(403, "You are not the buyer of this order")
    # Check order status allows payment (allow accepted, payment_pending, pending)
    if order.status not in ["pending", "accepted", "payment_pending"]:
        raise HTTPException(400, f"Cannot pay for order with status: {order.status}")
    # Check if payment already exists for this order - return existing if so
    existing = await db.execute(select(Payment).where(Payment.order_id == order.id))
    existing_payment = existing.scalar_one_or_none()
    if existing_payment:
        return {"razorpay_order_id": existing_payment.razorpay_order_id, "amount": int(existing_payment.amount*100), "currency": "INR", "key": settings.RAZORPAY_KEY_ID, "order_number": order.order_number}
    rzp_id = None
    # Check if using valid Razorpay credentials (not demo)
    is_real_razorpay = settings.RAZORPAY_KEY_ID and settings.RAZORPAY_KEY_SECRET and settings.RAZORPAY_KEY_SECRET != "demo_secret"
    if is_real_razorpay:
        try:
            import razorpay
            client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
            rz = client.order.create({"amount": int(order.total_amount*100), "currency":"INR", "receipt": order.order_number})
            rzp_id = rz["id"]
            print(f"Created real Razorpay order: {rzp_id}")
        except Exception as e:
            print(f"Razorpay API error: {e}")
            # Return error to client instead of creating demo order
            raise HTTPException(500, f"Payment gateway error: {str(e)}")
    else:
        rzp_id = f"order_demo_{uuid.uuid4().hex[:12]}"
    pay = Payment(order_id=order.id, razorpay_order_id=rzp_id, amount=order.total_amount)
    db.add(pay)
    await db.flush()
    # Update order status to payment_pending
    order.status = "payment_pending"
    await db.flush()
    return {"razorpay_order_id": rzp_id, "amount": int(order.total_amount*100), "currency": "INR", "key": settings.RAZORPAY_KEY_ID, "order_number": order.order_number}

@payment_router.post("/verify")
async def verify_payment(data: PaymentVerify, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Payment).where(Payment.razorpay_order_id == data.razorpay_order_id))
    pay = result.scalar_one_or_none()
    if not pay: raise HTTPException(404, "Payment not found")
    msg = f"{data.razorpay_order_id}|{data.razorpay_payment_id}"
    expected = hmac.new(settings.RAZORPAY_KEY_SECRET.encode(), msg.encode(), hashlib.sha256).hexdigest()
    is_demo = data.razorpay_order_id.startswith("order_demo_")
    if hmac.compare_digest(expected, data.razorpay_signature) or is_demo:
        pay.razorpay_payment_id = data.razorpay_payment_id
        pay.razorpay_signature = data.razorpay_signature
        pay.status = "captured"; pay.escrow_active = True
        ord_res = await db.execute(select(Order).where(Order.id == pay.order_id))
        o = ord_res.scalar_one_or_none()
        if o: o.status = "paid"; o.paid_at = datetime.utcnow()
        await db.flush()
        return {"success": True, "message": "Payment verified. Amount held in escrow."}
    pay.status = "failed"; await db.flush()
    raise HTTPException(400, "Payment verification failed")

@payment_router.post("/{order_id}/release-escrow")
async def release_escrow(order_id: int, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Order).where(Order.id==order_id, Order.buyer_id==current_user.id))
    order = result.scalar_one_or_none()
    if not order: raise HTTPException(404, "Order not found")
    if order.status != "delivered": raise HTTPException(400, "Release only after delivery")
    pr = await db.execute(select(Payment).where(Payment.order_id==order_id))
    pay = pr.scalar_one_or_none()
    if pay: pay.escrow_active=False; pay.status="escrow_released"; pay.escrow_released_at=datetime.utcnow()
    order.status="completed"; order.completed_at=datetime.utcnow(); await db.flush()
    return {"success": True, "message": "Escrow released. Farmer will receive payment."}

agreement_router = APIRouter(prefix="/agreements", tags=["Agreements"])

@agreement_router.post("/{order_id}/generate")
async def generate_agreement(order_id: int, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Order).where(Order.id==order_id))
    order = result.scalar_one_or_none()
    if not order: raise HTTPException(404, "Order not found")
    if order.farmer_id != current_user.id and order.buyer_id != current_user.id: raise HTTPException(403, "Not your order")
    from app.services.pdf_service import generate_agreement_pdf
    pdf_path = await generate_agreement_pdf(order, db)
    existing = await db.execute(select(Agreement).where(Agreement.order_id==order_id))
    ag = existing.scalar_one_or_none()
    if not ag: ag = Agreement(order_id=order_id, pdf_key=pdf_path); db.add(ag)
    else: ag.pdf_key = pdf_path
    await db.flush()
    return {"pdf_url": f"/api/v1/agreements/{order_id}/download", "message": "Agreement generated"}

@agreement_router.post("/{order_id}/sign")
async def sign_agreement(order_id: int, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Agreement).where(Agreement.order_id==order_id))
    ag = result.scalar_one_or_none()
    if not ag: raise HTTPException(404, "Agreement not found")
    ord_r = await db.execute(select(Order).where(Order.id==order_id))
    order = ord_r.scalar_one_or_none()
    if current_user.id == order.farmer_id: ag.farmer_signed=True; ag.farmer_signed_at=datetime.utcnow()
    elif current_user.id == order.buyer_id: ag.buyer_signed=True; ag.buyer_signed_at=datetime.utcnow()
    else: raise HTTPException(403, "Not your agreement")
    await db.flush()
    return {"farmer_signed":ag.farmer_signed,"buyer_signed":ag.buyer_signed,"fully_signed":ag.farmer_signed and ag.buyer_signed}

rating_router = APIRouter(prefix="/ratings", tags=["Ratings"])

@rating_router.post("/", response_model=RatingOut, status_code=201)
async def create_rating(data: RatingCreate, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    rating = Rating(order_id=data.order_id, rater_id=current_user.id, rated_id=data.rated_id, score=data.score, comment=data.comment)
    db.add(rating); await db.flush(); await db.refresh(rating)
    return RatingOut.model_validate(rating)
