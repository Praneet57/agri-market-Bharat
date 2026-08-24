from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta, timezone
from pydantic import BaseModel

from app.core.database import get_db
from app.core.security import require_admin
from app.models.user import User
from app.models.product import Product
from app.models.order import Order
from app.models.payment import Payment
from app.schemas import UserOut

router = APIRouter(prefix="/admin", tags=["Admin"])

class FarmerConversionApproval(BaseModel):
    user_ids: List[int]


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _start_of_day_utc(d: datetime) -> datetime:
    return datetime(d.year, d.month, d.day, tzinfo=timezone.utc)


def _start_of_week_utc(d: datetime) -> datetime:
    # Monday as start of week
    dow = d.weekday()
    return _start_of_day_utc(d - timedelta(days=dow))


def _start_of_month_utc(d: datetime) -> datetime:
    return datetime(d.year, d.month, 1, tzinfo=timezone.utc)


def _to_iso_date(dt: datetime) -> str:
    return dt.date().isoformat()


@router.get("/stats")
async def platform_stats(db: AsyncSession = Depends(get_db), _=Depends(require_admin)):
    total_users = (await db.execute(select(func.count(User.id)))).scalar() or 0
    total_farmers = (
        await db.execute(select(func.count(User.id)).where(User.role == "farmer"))
    ).scalar() or 0
    total_buyers = (
        await db.execute(select(func.count(User.id)).where(User.role == "buyer"))
    ).scalar() or 0

    total_products = (
        await db.execute(select(func.count(Product.id)).where(Product.is_active == True))
    ).scalar() or 0

    total_orders = (await db.execute(select(func.count(Order.id)))).scalar() or 0
    pending_orders = (
        await db.execute(select(func.count(Order.id)).where(Order.status == "pending"))
    ).scalar() or 0
    completed = (
        await db.execute(select(func.count(Order.id)).where(Order.status == "completed"))
    ).scalar() or 0
    cancelled = (
        await db.execute(select(func.count(Order.id)).where(Order.status == "cancelled"))
    ).scalar() or 0
    delivered = (
        await db.execute(select(func.count(Order.id)).where(Order.status == "delivered"))
    ).scalar() or 0

    now = _utc_now()
    sod = _start_of_day_utc(now)
    sow = _start_of_week_utc(now)
    som = _start_of_month_utc(now)

    paid_completed = ["paid", "completed"]

    total_revenue_today = (
        (await db.execute(
            select(func.sum(Order.platform_fee)).where(
                Order.created_at >= sod,
                Order.status.in_(paid_completed),
            )
        )).scalar()
        or 0.0
    )
    total_revenue_week = (
        (await db.execute(
            select(func.sum(Order.net_amount)).where(
                Order.created_at >= sow,
                Order.status.in_(paid_completed),
            )
        )).scalar()
        or 0.0
    )
    total_revenue_month = (
        (await db.execute(
            select(func.sum(Order.net_amount)).where(
                Order.created_at >= som,
                Order.status.in_(paid_completed),
            )
        )).scalar()
        or 0.0
    )

    aov_total, aov_count = (
        (await db.execute(
            select(func.sum(Order.total_amount), func.count(Order.id)).where(
                Order.created_at >= sod,
                Order.status.in_(paid_completed),
            )
        )).first()
        or (0.0, 0)
    )
    average_order_value = round((aov_total / aov_count), 2) if aov_count else 0.0

    total_cnt = (
        (await db.execute(select(func.count(Order.id)).where(Order.created_at >= sod))).scalar() or 0
    )
    conv_cnt = (
        (await db.execute(
            select(func.count(Order.id)).where(
                Order.created_at >= sod,
                Order.status.in_(paid_completed),
            )
        )).scalar() or 0
    )
    conversion_rate = round((conv_cnt / total_cnt) * 100.0, 2) if total_cnt else 0.0

    subq = (
        select(Order.buyer_id)
        .where(Order.status.in_(paid_completed))
        .group_by(Order.buyer_id)
        .having(func.count(Order.id) > 1)
    )
    rows = await db.execute(subq)
    returning_customers = len(rows.scalars().all())

    products_sold_today = (
        (await db.execute(
            select(func.sum(Order.quantity_kg)).where(
                Order.created_at >= sod,
                Order.status.in_(paid_completed),
            )
        )).scalar()
        or 0.0
    )

    return {
        "users": {
            "total": int(total_users),
            "farmers": int(total_farmers),
            "buyers": int(total_buyers),
        },
        "orders": {
            "total": int(total_orders),
            "pending": int(pending_orders),
            "delivered": int(delivered),
            "cancelled": int(cancelled),
            "completed": int(completed),
        },
        "products": {
            "active": int(total_products),
            "sold_today_qty_kg": round(float(products_sold_today), 2),
        },
        "financials": {
            "revenue": {
                "today": round(float(total_revenue_today), 2),
                "week": round(float(total_revenue_week), 2),
                "month": round(float(total_revenue_month), 2),
            },
            "gmv": round(float(total_revenue_today), 2),
            "average_order_value": average_order_value,
            "conversion_rate": conversion_rate,
            "returning_customers": int(returning_customers),
        },
    }


@router.get("/kpis")
async def kpis(
    range: str = "today",
    db: AsyncSession = Depends(get_db),
    _=Depends(require_admin),
):
    now = _utc_now()
    if range == "today":
        start = _start_of_day_utc(now)
    elif range == "week":
        start = _start_of_week_utc(now)
    elif range == "month":
        start = _start_of_month_utc(now)
    else:
        raise HTTPException(400, "range must be: today|week|month")

    paid_completed = ["paid", "completed"]

    revenue = (
        await db.execute(
            select(func.sum(Order.platform_fee)).where(
                Order.created_at >= start,
                Order.status.in_(paid_completed),
            )
        )
    ).scalar() or 0.0

    order_count = (
        await db.execute(select(func.count(Order.id)).where(Order.created_at >= start))
    ).scalar() or 0

    delivered = (
        await db.execute(
            select(func.count(Order.id)).where(
                Order.created_at >= start,
                Order.status == "delivered",
            )
        )
    ).scalar() or 0

    pending = (
        await db.execute(
            select(func.count(Order.id)).where(
                Order.created_at >= start,
                Order.status == "pending",
            )
        )
    ).scalar() or 0

    cancelled = (
        await db.execute(
            select(func.count(Order.id)).where(
                Order.created_at >= start,
                Order.status == "cancelled",
            )
        )
    ).scalar() or 0

    aov = (
        await db.execute(
            select(func.sum(Order.total_amount), func.count(Order.id)).where(
                Order.created_at >= start,
                Order.status.in_(paid_completed),
            )
        )
    ).first()

    total_a, total_c = aov if aov else (0.0, 0)
    average_order_value = round((total_a / total_c), 2) if total_c else 0.0

    conv_cnt = (
        await db.execute(
            select(func.count(Order.id)).where(
                Order.created_at >= start,
                Order.status.in_(paid_completed),
            )
        )
    ).scalar() or 0

    conversion_rate = round((conv_cnt / order_count) * 100.0, 2) if order_count else 0.0

    new_users = (
        await db.execute(select(func.count(User.id)).where(User.created_at >= start))
    ).scalar() or 0

    active_users = (
        await db.execute(
            select(func.count(func.distinct(Order.buyer_id))).where(Order.created_at >= start)
        )
    ).scalar() or 0

    return {
        "range": range,
        "revenue": round(float(revenue), 2),
        "total_orders": int(order_count),
        "pending": int(pending),
        "delivered": int(delivered),
        "cancelled": int(cancelled),
        "total_users": int((await db.execute(select(func.count(User.id)))).scalar() or 0),
        "new_users": int(new_users),
        "active_users": int(active_users),
        "average_order_value": average_order_value,
        "conversion_rate": conversion_rate,
    }


@router.get("/orders", response_model=List[Dict[str, Any]])
async def list_admin_orders(
    status: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_admin),
):
    q = select(Order).order_by(desc(Order.created_at))
    if status:
        q = q.where(Order.status == status)
    q = q.offset(offset).limit(limit)

    res = await db.execute(q)
    orders = res.scalars().all()

    out = []
    for o in orders:
        out.append(
            {
                "id": o.id,
                "order_number": o.order_number,
                "farmer_id": o.farmer_id,
                "buyer_id": o.buyer_id,
                "quantity_kg": o.quantity_kg,
                "price_per_kg": o.price_per_kg,
                "total_amount": o.total_amount,
                "platform_fee": o.platform_fee,
                "net_amount": o.net_amount,
                "status": o.status,
                "delivery_address": o.delivery_address,
                "notes": o.notes,
                "created_at": o.created_at,
            }
        )
    return out


@router.patch("/orders/{order_id}/status", response_model=Dict[str, Any])
async def admin_update_order_status(
    order_id: int,
    status: str,
    notes: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_admin),
):
    result = await db.execute(select(Order).where(Order.id == order_id))
    o = result.scalar_one_or_none()
    if not o:
        raise HTTPException(404, "Order not found")

    o.status = status
    if notes is not None:
        o.notes = notes
    await db.flush()
    return {"order_id": order_id, "status": o.status}


@router.get("/products", response_model=List[Dict[str, Any]])
async def list_admin_products(
    limit: int = 50,
    offset: int = 0,
    active: Optional[bool] = None,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_admin),
):
    q = select(Product)
    if active is not None:
        q = q.where(Product.is_active == active)
    q = q.offset(offset).limit(limit)

    res = await db.execute(q)
    ps = res.scalars().all()
    out = []
    for p in ps:
        out.append(
            {
                "id": p.id,
                "farmer_id": p.farmer_id,
                "name": p.name,
                "category": p.category,
                "quantity_kg": p.quantity_kg,
                "price_per_kg": p.price_per_kg,
                "status": p.status,
                "is_organic": p.is_organic,
                "is_active": p.is_active,
                "views_count": p.views_count,
                "district": p.district,
                "image_url": p.image_url,
                "created_at": p.created_at,
            }
        )
    return out


@router.patch("/products/{product_id}", response_model=Dict[str, Any])
async def admin_update_product(
    product_id: int,
    name: Optional[str] = None,
    category: Optional[str] = None,
    description: Optional[str] = None,
    quantity_kg: Optional[float] = None,
    price_per_kg: Optional[float] = None,
    status: Optional[str] = None,
    is_active: Optional[bool] = None,
    image_url: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_admin),
):
    result = await db.execute(select(Product).where(Product.id == product_id))
    p = result.scalar_one_or_none()
    if not p:
        raise HTTPException(404, "Product not found")

    for k, v in {
        "name": name,
        "category": category,
        "description": description,
        "quantity_kg": quantity_kg,
        "price_per_kg": price_per_kg,
        "status": status,
        "is_active": is_active,
        "image_url": image_url,
    }.items():
        if v is not None:
            setattr(p, k, v)

    await db.flush()
    return {"product_id": product_id, "status": p.status, "is_active": p.is_active}


@router.delete("/products/{product_id}", response_model=Dict[str, Any])
async def admin_delete_product(product_id: int, db: AsyncSession = Depends(get_db), _=Depends(require_admin)):
    result = await db.execute(select(Product).where(Product.id == product_id))
    p = result.scalar_one_or_none()
    if not p:
        raise HTTPException(404, "Product not found")
    p.is_active = False
    await db.flush()
    return {"product_id": product_id, "is_active": p.is_active}


@router.delete("/users/{user_id}", response_model=Dict[str, Any])
async def admin_delete_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_admin),
):
    result = await db.execute(select(User).where(User.id == user_id))
    u = result.scalar_one_or_none()
    if not u:
        raise HTTPException(404, "User not found")
    u.is_active = False
    await db.flush()
    return {"user_id": user_id, "is_active": u.is_active}


@router.patch("/users/{user_id}/block", response_model=Dict[str, Any])
async def admin_set_user_blocked(
    user_id: int,
    blocked: bool = True,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_admin),
):
    result = await db.execute(select(User).where(User.id == user_id))
    u = result.scalar_one_or_none()
    if not u:
        raise HTTPException(404, "User not found")
    u.is_active = not blocked
    await db.flush()
    return {"user_id": user_id, "is_active": u.is_active}


@router.get("/users/search")
async def search_users(
    q: Optional[str] = None,
    role: Optional[str] = None,
    status: Optional[str] = None,  # active|blocked
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_admin),
):
    filters = []
    if role:
        filters.append(User.role == role)
    if status == "active":
        filters.append(User.is_active == True)
    elif status == "blocked":
        filters.append(User.is_active == False)

    if q:
        like = f"%{q}%"
        filters.append((User.full_name.ilike(like)) | (User.phone.ilike(like)))

    q_stmt = select(User)
    if filters:
        q_stmt = q_stmt.where(*filters)

    q_stmt = q_stmt.offset(offset).limit(limit)
    users = (await db.execute(q_stmt)).scalars().all()

    paid_completed = ["paid", "completed"]
    user_ids = [u.id for u in users]

    purchases: Dict[int, int] = {}
    sells: Dict[int, int] = {}

    if user_ids:
        pur_q = (
            select(Order.buyer_id.label("uid"), func.count(Order.id).label("cnt"))
            .where(Order.buyer_id.in_(user_ids), Order.status.in_(paid_completed))
            .group_by(Order.buyer_id)
        )
        pur_rows = (await db.execute(pur_q)).all()
        purchases = {int(r[0]): int(r[1] or 0) for r in pur_rows}

        sell_q = (
            select(Order.farmer_id.label("uid"), func.count(Order.id).label("cnt"))
            .where(Order.farmer_id.in_(user_ids), Order.status.in_(paid_completed))
            .group_by(Order.farmer_id)
        )
        sell_rows = (await db.execute(sell_q)).all()
        sells = {int(r[0]): int(r[1] or 0) for r in sell_rows}

    out: List[Dict[str, Any]] = []
    for u in users:
        u_out = UserOut.model_validate(u).model_dump()
        u_out["purchase_orders_count"] = purchases.get(u.id, 0)
        u_out["sell_orders_count"] = sells.get(u.id, 0)
        out.append(u_out)

    return out

@router.get("/farmer-conversions")
async def list_farmer_conversions(
    status: str = "pending",
    db: AsyncSession = Depends(get_db),
    _=Depends(require_admin),
):
    q = select(User).where(User.farmer_conversion_status == status).order_by(User.farmer_conversion_requested_at.asc())
    users = (await db.execute(q)).scalars().all()
    out = []
    for u in users:
        purchase_count, purchase_total = (await db.execute(
            select(func.count(Order.id), func.sum(Order.total_amount)).where(Order.buyer_id == u.id)
        )).one()
        sell_count, sell_total = (await db.execute(
            select(func.count(Order.id), func.sum(Order.total_amount)).where(Order.farmer_id == u.id)
        )).one()
        out.append({
            "id": u.id, "full_name": u.full_name, "phone": u.phone, "email": u.email,
            "district": u.district, "requested_at": u.farmer_conversion_requested_at,
            "terms_accepted": bool(u.farmer_terms_accepted), "status": u.farmer_conversion_status,
            "purchase_orders": int(purchase_count or 0), "purchase_total": round(float(purchase_total or 0), 2),
            "sell_orders": int(sell_count or 0), "sell_total": round(float(sell_total or 0), 2),
        })
    return out

async def _approve_farmer_conversion(user_id: int, admin_id: int, db: AsyncSession):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(404, f"User {user_id} not found")
    if user.role == "admin":
        raise HTTPException(400, f"Admin user {user_id} cannot be converted")
    if user.role == "farmer":
        return False
    if user.farmer_conversion_status != "pending":
        raise HTTPException(400, f"User {user_id} has no pending conversion request")
    user.role = "farmer"
    user.farmer_conversion_status = "approved"
    user.farmer_conversion_reviewed_at = datetime.now(timezone.utc)
    user.farmer_conversion_reviewed_by = admin_id
    return True

@router.post("/farmer-conversions/approve/{user_id}")
async def approve_farmer_conversion(user_id: int, db: AsyncSession = Depends(get_db), admin: User = Depends(require_admin)):
    changed = await _approve_farmer_conversion(user_id, admin.id, db)
    await db.flush()
    return {"user_id": user_id, "approved": changed}

@router.post("/farmer-conversions/approve-all")
async def approve_all_farmer_conversions(data: FarmerConversionApproval, db: AsyncSession = Depends(get_db), admin: User = Depends(require_admin)):
    approved = 0
    for user_id in data.user_ids:
        try:
            if await _approve_farmer_conversion(user_id, admin.id, db):
                approved += 1
        except HTTPException:
            continue
    await db.flush()
    return {"approved": approved, "requested": len(data.user_ids)}


@router.get("/analytics/revenue-series")
async def revenue_series(
    days: int = 14,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_admin),
):
    now = _utc_now()
    start = _start_of_day_utc(now - timedelta(days=days))
    paid_completed = ["paid", "completed"]

    date_expr = func.date(Order.created_at)
    q = (
        select(date_expr.label("d"), func.sum(Order.platform_fee).label("revenue"))
        .where(Order.created_at >= start, Order.status.in_(paid_completed))
        .group_by(date_expr)
        .order_by(date_expr)
    )
    res = await db.execute(q)
    rows = res.all()
    labels = [r[0] for r in rows]
    values = [float(r[1] or 0.0) for r in rows]
    return {"labels": labels, "series": [{"name": "Revenue", "data": values}]}


@router.get("/analytics/orders-series")
async def orders_series(
    days: int = 14,
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_admin),
):
    now = _utc_now()
    start = _start_of_day_utc(now - timedelta(days=days))

    date_expr = func.date(Order.created_at)
    q = (
        select(date_expr.label("d"), func.count(Order.id).label("cnt"))
        .where(Order.created_at >= start)
        .group_by(date_expr)
        .order_by(date_expr)
    )
    if status:
        q = q.where(Order.status == status)

    res = await db.execute(q)
    rows = res.all()
    labels = [r[0] for r in rows]
    values = [int(r[1] or 0) for r in rows]
    return {"labels": labels, "series": [{"name": "Orders", "data": values}]}


@router.get("/analytics/top-products")
async def top_products(
    limit: int = 10,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_admin),
):
    paid_completed = ["paid", "completed"]

    q = (
        select(
            Product.id,
            Product.name,
            func.sum(Order.quantity_kg).label("qty"),
            func.sum(Order.total_amount).label("sales"),
        )
        .join(Order, Order.product_id == Product.id, isouter=False)
        .where(Order.status.in_(paid_completed), Order.product_id.isnot(None))
        .group_by(Product.id, Product.name)
        .order_by(desc("sales"))
        .limit(limit)
    )

    res = await db.execute(q)
    rows = res.all()

    return {
        "products": [
            {"id": r[0], "name": r[1], "qty": float(r[2] or 0.0), "sales": float(r[3] or 0.0)}
            for r in rows
        ]
    }


@router.get("/analytics/sales-by-category")
async def sales_by_category(
    limit: int = 10,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_admin),
):
    paid_completed = ["paid", "completed"]

    q = (
        select(Product.category.label("cat"), func.sum(Order.total_amount).label("sales"))
        .join(Order, Order.product_id == Product.id, isouter=False)
        .where(Order.status.in_(paid_completed), Order.product_id.isnot(None))
        .group_by(Product.category)
        .order_by(desc("sales"))
        .limit(limit)
    )
    res = await db.execute(q)
    rows = res.all()
    labels = [r[0] for r in rows]
    values = [float(r[1] or 0.0) for r in rows]
    return {"labels": labels, "series": [{"name": "Sales", "data": values}]}


@router.get("/analytics/sales-by-payment-method")
async def sales_by_payment_method(
    db: AsyncSession = Depends(get_db),
    _=Depends(require_admin),
):
    paid_completed = ["paid", "completed"]

    q = (
        select(Payment.payment_method.label("pm"), func.sum(Payment.amount).label("sales"))
        .join(Order, Order.id == Payment.order_id)
        .where(Order.status.in_(paid_completed))
        .group_by(Payment.payment_method)
        .order_by(desc("sales"))
    )
    res = await db.execute(q)
    rows = res.all()
    labels = [r[0] or "unknown" for r in rows]
    values = [float(r[1] or 0.0) for r in rows]
    return {"labels": labels, "series": [{"name": "Sales", "data": values}]}


@router.get("/analytics/transactions-summary")
async def transactions_summary(
    db: AsyncSession = Depends(get_db),
    _=Depends(require_admin),
):
    paid_completed = ["paid", "completed"]
    q = select(func.count(Order.id), func.sum(Order.platform_fee)).where(Order.status.in_(paid_completed))
    cnt, total_amount = (await db.execute(q)).one()
    return {
        "paid_completed_orders": int(cnt or 0),
        "total_amount_sum": round(float(total_amount or 0.0), 2),
    }


@router.get("/analytics/transactions-by-user")
async def transactions_by_user(
    user_id: int,
    type: str = "purchase",  # purchase => buyer_id, sell => farmer_id
    db: AsyncSession = Depends(get_db),
    _=Depends(require_admin),
):
    paid_completed = ["paid", "completed"]
    if type not in {"purchase", "sell"}:
        paid_completed = ["paid", "completed"]

    col = Order.buyer_id if type == "purchase" else Order.farmer_id
    q = (
        select(func.count(Order.id), func.sum(Order.total_amount))
        .where(col == user_id, Order.status.in_(paid_completed))
    )
    cnt, total_amount = (await db.execute(q)).one()
    return {
        "user_id": user_id,
        "type": type,
        "orders_count": int(cnt or 0),
        "total_amount_sum": round(float(total_amount or 0.0), 2),
    }

