from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from typing import List, Optional
from math import radians, cos, sin, asin, sqrt
from app.core.database import get_db
from app.core.security import get_current_user, require_marketplace_user
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
async def create_product(data: ProductCreate, current_user: User = Depends(require_marketplace_user), db: AsyncSession = Depends(get_db)):
    d = data.model_dump()
    d["latitude"] = d.get("latitude") or current_user.latitude
    d["longitude"] = d.get("longitude") or current_user.longitude
    d["district"] = d.get("district") or current_user.district
    # Normalize unit; ensure quantity_kg is stored in kg
    unit = (d.get("quantity_unit") or "kg").lower()
    if unit not in ("kg", "ton", "gram"):
        unit = "kg"
    d["quantity_unit"] = unit
    if unit == "ton":
        d["quantity_kg"] = d["quantity_kg"] * 1000
    elif unit == "gram":
        d["quantity_kg"] = d["quantity_kg"] / 1000
    product = Product(farmer_id=current_user.id, **d)
    db.add(product); await db.flush(); await db.refresh(product)
    return ProductOut.model_validate(product)

@router.get("/", response_model=List[ProductOut])
async def list_products(category: Optional[str]=None, district: Optional[str]=None,
    min_price: Optional[float]=None, max_price: Optional[float]=None,
    is_organic: Optional[bool]=None, farmer_id: Optional[int]=None,
    lat: Optional[float]=Query(None),
    lon: Optional[float]=Query(None), radius_km: float=200.0,
    limit: int=Query(20, le=100), offset: int=0, db: AsyncSession=Depends(get_db)):
    filters = [Product.status == "available", Product.is_active == True]
    if category: filters.append(Product.category.ilike(f"%{category}%"))
    if district: filters.append(Product.district.ilike(f"%{district}%"))
    if min_price is not None: filters.append(Product.price_per_kg >= min_price)
    if max_price is not None: filters.append(Product.price_per_kg <= max_price)
    if is_organic is not None: filters.append(Product.is_organic == is_organic)
    if farmer_id is not None: filters.append(Product.farmer_id == farmer_id)
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

@router.get("/recommended", response_model=List[ProductOut])
async def recommended_products(
    district: Optional[str]=None,
    category: Optional[str]=None,
    limit: int=Query(8, le=20),
    radius_km: float=Query(80.0),
    max_price: Optional[float]=None,
    is_organic: Optional[bool]=None,
    lat: Optional[float]=Query(None),
    lon: Optional[float]=Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    district_name = (district or current_user.district or "").strip()
    filters = [Product.status == "available", Product.is_active == True]
    if category: filters.append(Product.category.ilike(f"%{category}%"))
    if max_price is not None: filters.append(Product.price_per_kg <= max_price)
    if is_organic is not None: filters.append(Product.is_organic == is_organic)

    result = await db.execute(select(Product).where(and_(*filters)).limit(100))
    products = []
    for p in result.scalars().all():
        po = ProductOut.model_validate(p)
        same_district = bool(p.district and district_name and p.district.lower() == district_name.lower())
        if lat and lon and p.latitude and p.longitude:
            po.distance_km = haversine(lat, lon, p.latitude, p.longitude)
            if po.distance_km > radius_km and not same_district:
                continue
        elif district_name and not same_district:
            po.distance_km = 9999
        else:
            po.distance_km = 0 if same_district else 9999
        if district_name and not same_district and not (lat and lon and p.latitude and p.longitude):
            continue
        products.append(po)

    products.sort(key=lambda x: (
        0 if (x.district and district_name and x.district.lower() == district_name.lower()) else 1,
        x.distance_km if x.distance_km is not None else 9999,
        x.created_at or 0,
    ))
    return products[:limit]

@router.get("/my", response_model=List[ProductOut])
async def my_products(current_user: User = Depends(require_marketplace_user), db: AsyncSession = Depends(get_db)):
    # Only show active listings in "My Products" (soft delete sets is_active=False)
    filters = [
        Product.farmer_id == current_user.id,
        Product.is_active == True,
        Product.status == "available",
    ]
    result = await db.execute(select(Product).where(and_(*filters)))
    return [ProductOut.model_validate(p) for p in result.scalars().all()]

@router.get("/{product_id}", response_model=ProductOut)
async def get_product(product_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Product).where(Product.id == product_id))
    p = result.scalar_one_or_none()
    if not p: raise HTTPException(404, "Product not found")
    p.views_count += 1; await db.flush()
    return ProductOut.model_validate(p)

@router.put("/{product_id}", response_model=ProductOut)
async def update_product(product_id: int, data: ProductUpdate, current_user: User = Depends(require_marketplace_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Product).where(Product.id == product_id, Product.farmer_id == current_user.id))
    p = result.scalar_one_or_none()
    if not p: raise HTTPException(404, "Product not found")
    updates = data.model_dump(exclude_unset=True)
    # If unit changes, re-normalize the quantity to kg
    if "quantity_unit" in updates and updates["quantity_unit"] is not None:
        unit = updates["quantity_unit"].lower()
        if unit not in ("kg", "ton", "gram"):
            unit = "kg"
        updates["quantity_unit"] = unit
        if "quantity_kg" in updates and updates["quantity_kg"] is not None:
            if unit == "ton":
                updates["quantity_kg"] = updates["quantity_kg"] * 1000
            elif unit == "gram":
                updates["quantity_kg"] = updates["quantity_kg"] / 1000
    for k,v in updates.items(): setattr(p, k, v)
    await db.flush(); return ProductOut.model_validate(p)

@router.delete("/{product_id}", status_code=204)
async def delete_product(product_id: int, current_user: User = Depends(require_marketplace_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Product).where(Product.id == product_id, Product.farmer_id == current_user.id))
    p = result.scalar_one_or_none()
    if not p: raise HTTPException(404, "Product not found")
    p.is_active = False; await db.flush()


@router.post("/upload-image", response_model=dict)
async def upload_product_image(
    file: UploadFile = File(...),
    current_user: User = Depends(require_marketplace_user),
):
    # Validate file type
    allowed = {"image/jpeg", "image/png", "image/webp", "image/jpg"}
    if file.content_type not in allowed:
        raise HTTPException(400, "Only JPG, PNG, WEBP images allowed")

    # Validate file size (max 5MB)
    contents = await file.read()
    if len(contents) > 5 * 1024 * 1024:
        raise HTTPException(400, "Image must be under 5MB")

    import os
    import uuid

    # In docker-compose we mount host ./uploads to container /app/uploads
    upload_dir = os.path.join("/app/uploads", "products")

    os.makedirs(upload_dir, exist_ok=True)

    ext = (file.filename.split(".")[-1] or "jpg").lower()
    if ext not in ["jpg", "jpeg", "png", "webp"]:
        ext = "jpg"

    filename = f"{uuid.uuid4().hex}.{ext}"
    filepath = os.path.join(upload_dir, filename)

    with open(filepath, "wb") as f:
        f.write(contents)

    image_url = f"/uploads/products/{filename}"
    return {"image_url": image_url, "filename": filename}
