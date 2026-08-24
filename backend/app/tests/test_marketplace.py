import pytest
from httpx import AsyncClient
pytestmark = pytest.mark.asyncio

class TestProducts:
    async def test_create_product(self, client: AsyncClient, farmer_token):
        r = await client.post("/api/v1/products", headers={"Authorization": f"Bearer {farmer_token}"},
            json={"name":"Test Mangoes","category":"Fruits","quantity_kg":500,"price_per_kg":120,"is_organic":True})
        assert r.status_code == 201; assert r.json()["name"] == "Test Mangoes"

    async def test_buyer_can_create_product(self, client: AsyncClient, buyer_token):
        r = await client.post("/api/v1/products", headers={"Authorization": f"Bearer {buyer_token}"},
            json={"name":"X","category":"Fruits","quantity_kg":10,"price_per_kg":5})
        assert r.status_code == 201

    async def test_list_products(self, client: AsyncClient):
        r = await client.get("/api/v1/products")
        assert r.status_code == 200; assert isinstance(r.json(), list)

    async def test_recommended_products_for_buyer_district(self, client: AsyncClient, farmer_token, buyer_token):
        await client.post("/api/v1/products", headers={"Authorization": f"Bearer {farmer_token}"},
            json={"name":"Chennai Rice","category":"Grains","quantity_kg":200,"price_per_kg":32,"district":"Chennai"})
        await client.post("/api/v1/products", headers={"Authorization": f"Bearer {farmer_token}"},
            json={"name":"Coimbatore Mangoes","category":"Fruits","quantity_kg":150,"price_per_kg":60,"district":"Coimbatore"})
        r = await client.get("/api/v1/products/recommended?district=Chennai", headers={"Authorization": f"Bearer {buyer_token}"})
        assert r.status_code == 200
        data = r.json()
        assert len(data) >= 1
        assert all(item["district"] == "Chennai" for item in data)

    async def test_product_views_increment(self, client: AsyncClient, farmer_token):
        cr = await client.post("/api/v1/products", headers={"Authorization": f"Bearer {farmer_token}"},
            json={"name":"View Test","category":"Grains","quantity_kg":100,"price_per_kg":30})
        pid = cr.json()["id"]
        r = await client.get(f"/api/v1/products/{pid}")
        assert r.json()["views_count"] >= 1

class TestDemands:
    async def test_create_demand(self, client: AsyncClient, buyer_token):
        r = await client.post("/api/v1/demands", headers={"Authorization": f"Bearer {buyer_token}"},
            json={"product_name":"Tomatoes","category":"Vegetables","quantity_kg":500,"max_price_per_kg":25})
        assert r.status_code == 201

    async def test_farmer_cannot_create_demand(self, client: AsyncClient, farmer_token):
        r = await client.post("/api/v1/demands", headers={"Authorization": f"Bearer {farmer_token}"},
            json={"product_name":"X","category":"Fruits","quantity_kg":10,"max_price_per_kg":5})
        assert r.status_code == 403

class TestOrders:
    async def test_farmer_can_buy_product(self, client: AsyncClient, farmer_token, buyer_token):
        buyer = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {buyer_token}"})
        product = await client.post("/api/v1/products", headers={"Authorization": f"Bearer {buyer_token}"},
            json={"name":"Buyer Listed Rice","category":"Grains","quantity_kg":100,"price_per_kg":45})
        cr = await client.post("/api/v1/orders", headers={"Authorization": f"Bearer {farmer_token}"},
            json={"product_id":product.json()["id"],"farmer_id":buyer.json()["id"],"quantity_kg":20,"price_per_kg":45,
                  "delivery_address":"Farm","district":"Dindigul"})
        assert cr.status_code == 201

    async def test_order_lifecycle(self, client: AsyncClient, farmer_token, buyer_token):
        fm = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {farmer_token}"})
        farmer_id = fm.json()["id"]
        pr = await client.post("/api/v1/products", headers={"Authorization": f"Bearer {farmer_token}"},
            json={"name":"Order Test Rice","category":"Grains","quantity_kg":100,"price_per_kg":45})
        pid = pr.json()["id"]
        cr = await client.post("/api/v1/orders", headers={"Authorization": f"Bearer {buyer_token}"},
            json={"product_id":pid,"farmer_id":farmer_id,"quantity_kg":20,"price_per_kg":45})
        assert cr.status_code == 201; oid = cr.json()["id"]
        assert cr.json()["status"] == "pending"
        ar = await client.patch(f"/api/v1/orders/{oid}/status", headers={"Authorization": f"Bearer {farmer_token}"},
            json={"status":"accepted"})
        assert ar.json()["status"] == "accepted"
        br = await client.patch(f"/api/v1/orders/{oid}/status", headers={"Authorization": f"Bearer {farmer_token}"},
            json={"status":"completed"})
        assert br.status_code == 400
