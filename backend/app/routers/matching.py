from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from typing import Optional
from math import radians,cos,sin,asin,sqrt
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.product import Product
from app.models.demand import Demand

router = APIRouter(prefix="/match", tags=["Matching"])

def haversine(lat1,lon1,lat2,lon2):
    if None in (lat1,lon1,lat2,lon2): return 9999.0
    R=6371; lat1,lon1,lat2,lon2=map(radians,[lat1,lon1,lat2,lon2])
    a=sin((lat2-lat1)/2)**2+cos(lat1)*cos(lat2)*sin((lon2-lon1)/2)**2
    return round(2*R*asin(sqrt(a)),1)

@router.get("/products-for-demand/{demand_id}")
async def match_products(demand_id:int, radius_km:float=Query(200.0), _=Depends(get_current_user), db:AsyncSession=Depends(get_db)):
    r = await db.execute(select(Demand).where(Demand.id==demand_id))
    demand = r.scalar_one_or_none()
    if not demand: return []
    pr = await db.execute(select(Product).where(and_(Product.status=="available",Product.is_active==True,Product.category.ilike(f"%{demand.category}%"),Product.price_per_kg<=demand.max_price_per_kg)))
    matches=[]
    for p in pr.scalars().all():
        dist=haversine(demand.latitude,demand.longitude,p.latitude,p.longitude)
        if dist<=radius_km: matches.append({"product_id":p.id,"name":p.name,"category":p.category,"quantity_kg":p.quantity_kg,"price_per_kg":p.price_per_kg,"district":p.district,"distance_km":dist,"farmer_id":p.farmer_id,"is_organic":p.is_organic})
    matches.sort(key=lambda x:x["distance_km"]); return matches[:20]

@router.get("/demands-for-product/{product_id}")
async def match_demands(product_id:int, radius_km:float=Query(200.0), _=Depends(get_current_user), db:AsyncSession=Depends(get_db)):
    r = await db.execute(select(Product).where(Product.id==product_id))
    product = r.scalar_one_or_none()
    if not product: return []
    dr = await db.execute(select(Demand).where(and_(Demand.status=="open",Demand.is_active==True,Demand.category.ilike(f"%{product.category}%"),Demand.max_price_per_kg>=product.price_per_kg)))
    matches=[]
    for d in dr.scalars().all():
        dist=haversine(product.latitude,product.longitude,d.latitude,d.longitude)
        if dist<=radius_km: matches.append({"demand_id":d.id,"product_name":d.product_name,"category":d.category,"quantity_kg":d.quantity_kg,"max_price_per_kg":d.max_price_per_kg,"district":d.district,"distance_km":dist,"buyer_id":d.buyer_id})
    matches.sort(key=lambda x:x["distance_km"]); return matches[:20]

@router.get("/nearby-farmers")
async def nearby_farmers(lat:float=Query(...),lon:float=Query(...),radius_km:float=Query(100.0),category:Optional[str]=None,_=Depends(get_current_user),db:AsyncSession=Depends(get_db)):
    q=select(Product).where(Product.status=="available",Product.is_active==True)
    if category: q=q.where(Product.category.ilike(f"%{category}%"))
    result=await db.execute(q); seen=set(); farmers=[]
    for p in result.scalars().all():
        if p.farmer_id in seen: continue
        dist=haversine(lat,lon,p.latitude,p.longitude)
        if dist<=radius_km: seen.add(p.farmer_id); farmers.append({"farmer_id":p.farmer_id,"district":p.district,"distance_km":dist,"sample_product":p.name})
    farmers.sort(key=lambda x:x["distance_km"]); return farmers[:30]
