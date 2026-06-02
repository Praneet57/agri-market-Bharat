from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import List
from app.core.database import get_db
from app.core.security import require_admin
from app.models.user import User
from app.models.product import Product
from app.models.demand import Demand
from app.models.order import Order
from app.models.payment import Payment, Rating
from app.schemas import UserOut

router = APIRouter(prefix="/admin", tags=["Admin"])

@router.get("/stats")
async def platform_stats(db:AsyncSession=Depends(get_db),_=Depends(require_admin)):
    total_users=(await db.execute(select(func.count(User.id)))).scalar()
    total_farmers=(await db.execute(select(func.count(User.id)).where(User.role=="farmer"))).scalar()
    total_buyers=(await db.execute(select(func.count(User.id)).where(User.role=="buyer"))).scalar()
    total_products=(await db.execute(select(func.count(Product.id)).where(Product.is_active==True))).scalar()
    total_orders=(await db.execute(select(func.count(Order.id)))).scalar()
    completed=(await db.execute(select(func.count(Order.id)).where(Order.status=="completed"))).scalar()
    gmv=(await db.execute(select(func.sum(Order.total_amount)).where(Order.status.in_(["paid","completed"])))).scalar() or 0
    revenue=(await db.execute(select(func.sum(Order.platform_fee)).where(Order.status.in_(["paid","completed"])))).scalar() or 0
    return {"users":{"total":total_users,"farmers":total_farmers,"buyers":total_buyers},"products":{"active":total_products},"orders":{"total":total_orders,"completed":completed},"financials":{"gmv":round(gmv,2),"revenue":round(revenue,2)}}

@router.get("/users", response_model=List[UserOut])
async def list_all_users(role:str=None,limit:int=50,offset:int=0,db:AsyncSession=Depends(get_db),_=Depends(require_admin)):
    q=select(User)
    if role: q=q.where(User.role==role)
    result=await db.execute(q.offset(offset).limit(limit))
    return [UserOut.model_validate(u) for u in result.scalars().all()]

@router.patch("/users/{user_id}/toggle-active")
async def toggle_user(user_id:int,db:AsyncSession=Depends(get_db),_=Depends(require_admin)):
    result=await db.execute(select(User).where(User.id==user_id))
    user=result.scalar_one_or_none()
    if not user: raise HTTPException(404,"User not found")
    user.is_active=not user.is_active; await db.flush()
    return {"user_id":user_id,"is_active":user.is_active}
