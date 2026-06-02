from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
import os
from contextlib import asynccontextmanager
from app.core.config import settings
from app.core.database import init_db
from app.core.redis import get_redis, close_redis
from app.middleware.logging_middleware import LoggingMiddleware
from app.middleware.security_middleware import SecurityHeadersMiddleware
from app.routers.auth import router as auth_router
from app.routers.products import router as products_router
from app.routers.transactions import demand_router,order_router,payment_router,agreement_router,rating_router
from app.routers.chat import router as chat_router
from app.routers.matching import router as match_router
from app.routers.admin import router as admin_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db(); await get_redis()
    print(f"✅ {settings.APP_NAME} started")
    yield
    await close_redis()

app = FastAPI(title="Agri Marketplace API", version="1.0.0", lifespan=lifespan, docs_url="/api/docs", redoc_url="/api/redoc")
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(LoggingMiddleware)
app.add_middleware(CORSMiddleware, allow_origins=settings.origins_list, allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

P = "/api/v1"
for r in [auth_router,products_router,demand_router,order_router,payment_router,agreement_router,chat_router,match_router,rating_router,admin_router]:
    app.include_router(r, prefix=P)

@app.get("/api/v1/agreements/{order_id}/download")
async def download_agreement(order_id: int):
    from app.core.database import AsyncSessionLocal
    from sqlalchemy import select
    from app.models.payment import Agreement
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Agreement).where(Agreement.order_id==order_id))
        ag = result.scalar_one_or_none()
        if ag and ag.pdf_key and os.path.exists(ag.pdf_key):
            return FileResponse(ag.pdf_key, media_type="application/pdf", filename=f"agreement_order_{order_id}.pdf")
    return JSONResponse({"detail":"Not generated yet"},status_code=404)

@app.get("/api/health")
async def health():
    redis_ok=False
    try: r=await get_redis(); await r.ping(); redis_ok=True
    except: pass
    return {"status":"ok","app":settings.APP_NAME,"version":"1.0.0","redis":"connected" if redis_ok else "disconnected"}

frontend_path = os.path.join(os.path.dirname(__file__),"..","..","frontend")
if os.path.exists(frontend_path):
    app.mount("/static", StaticFiles(directory=os.path.join(frontend_path,"static")), name="static")
    @app.get("/", include_in_schema=False)
    async def root(): return FileResponse(os.path.join(frontend_path,"index.html"))
    @app.get("/{path:path}", include_in_schema=False)
    async def spa(path: str):
        fp=os.path.join(frontend_path,path)
        return FileResponse(fp) if os.path.isfile(fp) else FileResponse(os.path.join(frontend_path,"index.html"))
