import pytest
from httpx import AsyncClient
pytestmark = pytest.mark.asyncio

class TestRegister:
    async def test_register_farmer(self, client: AsyncClient):
        r = await client.post("/api/v1/auth/register", json={"full_name":"Ravi","phone":"9200000001","password":"test1234","role":"farmer"})
        assert r.status_code == 201
        assert "access_token" in r.json()

    async def test_register_buyer_role_is_allowed(self, client: AsyncClient):
        r = await client.post("/api/v1/auth/register", json={"full_name":"Buyer One","phone":"9200000009","password":"test1234","role":"buyer"})
        assert r.status_code == 201
        assert r.json()["user"]["role"] == "buyer"

    async def test_duplicate_phone(self, client: AsyncClient):
        d = {"full_name":"X","phone":"9200000002","password":"p123456","role":"farmer"}
        await client.post("/api/v1/auth/register", json=d)
        r = await client.post("/api/v1/auth/register", json=d)
        assert r.status_code == 400

class TestLogin:
    async def test_login_success(self, client: AsyncClient, farmer_token):
        assert farmer_token is not None

    async def test_login_wrong_password(self, client: AsyncClient):
        r = await client.post("/api/v1/auth/login", json={"phone":"9111111001","password":"wrong"})
        assert r.status_code == 401

class TestRefresh:
    async def test_refresh_rotation(self, client: AsyncClient):
        reg = await client.post("/api/v1/auth/register", json={"full_name":"R","phone":"9400000001","password":"test1234","role":"farmer"})
        old_rt = reg.json()["refresh_token"]
        r1 = await client.post("/api/v1/auth/refresh", json={"refresh_token": old_rt})
        assert r1.status_code == 200
        assert r1.json()["refresh_token"] != old_rt
        r2 = await client.post("/api/v1/auth/refresh", json={"refresh_token": old_rt})
        assert r2.status_code == 401

class TestProfile:
    async def test_get_me(self, client: AsyncClient, farmer_token):
        r = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {farmer_token}"})
        assert r.status_code == 200; assert r.json()["role"] == "farmer"

    async def test_update_profile(self, client: AsyncClient, farmer_token):
        r = await client.put("/api/v1/auth/me", headers={"Authorization": f"Bearer {farmer_token}"}, json={"bio": "Mango farmer"})
        assert r.status_code == 200

class TestHealth:
    async def test_health(self, client: AsyncClient):
        r = await client.get("/api/health")
        assert r.status_code == 200; assert r.json()["status"] == "ok"
