from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from typing import List, Optional
from math import radians, cos, sin, asin, sqrt
from app.core.database import get_db
from app.core.security import get_current_user, require_farmer
from app.models.user import User
from app.models.product import Product
from app.schemas import ProductCreate, ProductOut, ProductUpdate

router = APIRouter(prefix="/products", tags=["Products"])

def haversine(lat1,lon1,lat2,lon2):
    if None in (lat1,lon1,lat2,lon2): return 9999.0
    R=6371; lat1,lon1,lat2,lon2=map(radians,[lat1,lon1,lat2,lon2])
    a=sin((lat2-lat1)/2)**2+cos(lat1)*cos(lat2)*sin((lon2-lon1)/2)**2
    return round(2*R*asin(sqrt(a)),1)

@router.post("/", response_model=ProductOut, status_code=201)
async def create_product(data: ProductCreate, current_user: User = Depends(require_farmer), db: AsyncSession = Depends(get_db)):
    d = data.model_dump()
    d["latitude"] = d.get("latitude") or current_user.latitude
    d["longitude"] = d.get("longitude") or current_user.longitude
    d["district"] = d.get("district") or current_user.district
    product = Product(farmer_id=current_user.id, **d)
    db.add(product); await db.flush(); await db.refresh(product)
    return ProductOut.model_validate(product)

@router.get("/", response_model=List[ProductOut])
async def list_products(category: Optional[str]=None, district: Optional[str]=None,
    min_price: Optional[float]=None, max_price: Optional[float]=None,
    is_organic: Optional[bool]=None, lat: Optional[float]=Query(None),
    lon: Optional[float]=Query(None), radius_km: float=200.0,
    limit: int=Query(20, le=100), offset: int=0, db: AsyncSession=Depends(get_db)):
    filters = [Product.status == "available", Product.is_active == True]
    if category: filters.append(Product.category.ilike(f"%{category}%"))
    if district: filters.append(Product.district.ilike(f"%{district}%"))
    if min_price is not None: filters.append(Product.price_per_kg >= min_price)
    if max_price is not None: filters.append(Product.price_per_kg <= max_price)
    if is_organic is not None: filters.append(Product.is_organic == is_organic)
    result = await db.execute(select(Product).where(and_(*filters)).offset(offset).limit(limit))
    out = []
    for p in result.scalars().all():
        po = ProductOut.model_validate(p)
        if lat and lon and p.latitude and p.longitude:
            dist = haversine(lat,lon,p.latitude,p.longitude)
            if dist > radius_km: continue
            po.distance_km = dist
        out.append(po)
    if lat and lon: out.sort(key=lambda x: x.distance_km or 9999)
    return out

@router.get("/my", response_model=List[ProductOut])
async def my_products(current_user: User = Depends(require_farmer), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Product).where(Product.farmer_id == current_user.id))
    return [ProductOut.model_validate(p) for p in result.scalars().all()]

@router.get("/{product_id}", response_model=ProductOut)
async def get_product(product_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Product).where(Product.id == product_id))
    p = result.scalar_one_or_none()
    if not p: raise HTTPException(404, "Product not found")
    p.views_count += 1; await db.flush()
    return ProductOut.model_validate(p)

@router.put("/{product_id}", response_model=ProductOut)
async def update_product(product_id: int, data: ProductUpdate, current_user: User = Depends(require_farmer), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Product).where(Product.id == product_id, Product.farmer_id == current_user.id))
    p = result.scalar_one_or_none()
    if not p: raise HTTPException(404, "Product not found")
    for k,v in data.model_dump(exclude_unset=True).items(): setattr(p, k, v)
    await db.flush(); return ProductOut.model_validate(p)

@router.delete("/{product_id}", status_code=204)
async def delete_product(product_id: int, current_user: User = Depends(require_farmer), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Product).where(Product.id == product_id, Product.farmer_id == current_user.id))
    p = result.scalar_one_or_none()
    if not p: raise HTTPException(404, "Product not found")
    p.is_active = False; await db.flush()
