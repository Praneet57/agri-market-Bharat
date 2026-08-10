# TODO — Quantity Unit Selector (gram/ton/kg) + Auto Stock Reduction on Order

## Goal
1. Farmers can post product quantity in grams, kg, or tons (easy unit choice).
2. When a buyer places an order, the product's remaining stock is reduced automatically (e.g. 500kg banana → buyer buys 300kg → 200kg left, shown on dashboard card).

## Backend
- [x] 1. `app/models/product.py` — add `quantity_unit` column (default `kg`)
- [x] 2. `app/schemas/__init__.py` — add `quantity_unit` to `ProductCreate`, `ProductUpdate`, `ProductOut`
- [x] 3. `app/core/database.py` — add `quantity_unit` to `_ensure_columns` for existing DBs
- [x] 4. `app/routers/products.py` — accept `quantity_unit` on create/update
- [x] 5. `app/routers/transactions.py` — reduce product stock on order create; restore on cancel/reject

## Frontend
- [x] 6. `static/js/api.js` — add `formatQty()` helper (kg/ton/gram display)
- [x] 7. `farmer/dashboard.html` — unit selector in Add Product form; convert to kg; show remaining stock in cards & overview
- [x] 8. `buyer/dashboard.html` — show quantity via `formatQty`; show available stock (auto-reduced) in marketplace & order modal
- [x] 9. `index.html` — display product quantity via `formatQty`
- [x] 10. `profile.html` — display product quantity via `formatQty`

## Follow-up
- [ ] 11. Restart backend (creates `quantity_unit` column via `_ensure_columns`), run syntax check, then test
