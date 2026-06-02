import pytest, asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from app.main import app
from app.core.database import Base, get_db

TEST_DB = "postgresql+asyncpg://agriuser:agripass@localhost:5432/agridb_test"
test_engine = create_async_engine(TEST_DB, echo=False)
TestSession = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)

@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop(); yield loop; loop.close()

@pytest.fixture(scope="session", autouse=True)
async def setup_db():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

@pytest.fixture
async def db():
    async with TestSession() as session:
        yield session; await session.rollback()

@pytest.fixture
async def client(db):
    async def override(): yield db
    app.dependency_overrides[get_db] = override
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()

@pytest.fixture
async def farmer_token(client):
    await client.post("/api/v1/auth/register", json={"full_name":"Test Farmer","phone":"9111111001","password":"farmer123","role":"farmer","district":"Coimbatore"})
    r = await client.post("/api/v1/auth/login", json={"phone":"9111111001","password":"farmer123"})
    return r.json()["access_token"]

@pytest.fixture
async def buyer_token(client):
    await client.post("/api/v1/auth/register", json={"full_name":"Test Buyer","phone":"9111111002","password":"buyer123","role":"buyer","district":"Chennai"})
    r = await client.post("/api/v1/auth/login", json={"phone":"9111111002","password":"buyer123"})
    return r.json()["access_token"]
