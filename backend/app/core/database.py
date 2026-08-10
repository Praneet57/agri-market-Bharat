from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from app.core.config import settings

engine = create_async_engine(settings.DATABASE_URL, echo=settings.DEBUG, pool_pre_ping=True, pool_size=10, max_overflow=20)
AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

class Base(DeclarativeBase):
    pass

async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise

async def _ensure_columns(conn):
    """Add missing columns to existing tables (create_all only creates tables)."""
    from sqlalchemy import text

    # products: quantity_unit
    prod_cols = await conn.execute(text(
        "SELECT column_name FROM information_schema.columns WHERE table_name='products'"
    ))
    prod_existing = {r[0] for r in prod_cols.fetchall()}
    if "quantity_unit" not in prod_existing:
        await conn.execute(text(
            "ALTER TABLE products ADD COLUMN quantity_unit VARCHAR(10) DEFAULT 'kg'"
        ))

    # orders: district, latitude, longitude
    order_cols = await conn.execute(text(
        "SELECT column_name FROM information_schema.columns WHERE table_name='orders'"
    ))
    existing = {r[0] for r in order_cols.fetchall()}
    if "district" not in existing:
        await conn.execute(text(
            "ALTER TABLE orders ADD COLUMN district VARCHAR(100) NULL"
        ))
    if "latitude" not in existing:
        await conn.execute(text(
            "ALTER TABLE orders ADD COLUMN latitude FLOAT NULL"
        ))
    if "longitude" not in existing:
        await conn.execute(text(
            "ALTER TABLE orders ADD COLUMN longitude FLOAT NULL"
        ))

async def init_db():
    from app.models import user, product, demand, order, payment  # noqa
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await _ensure_columns(conn)
