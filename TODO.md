# TODO

## Admin Dashboard (Phase 1: KPIs + Orders + Users + Products + Basic Analytics)
- [x] Inspect existing admin UI/backend endpoints and data models.
- [x] Extend backend `agri/backend/app/routers/admin.py` with dashboard KPIs + time-series analytics endpoints.
- [x] Add backend endpoints for admin order listing + admin order status update.
- [x] Add backend endpoints for admin product listing + CRUD (create/update/delete + stock status signals).
- [x] Add backend endpoints for user search/filter and delete/export.

- [x] Update frontend `agri/frontend/admin/dashboard.html` to a modern responsive layout with KPI cards + charts.
- [x] Extend `agri/frontend/static/js/api.js` with `API.admin*` methods.
- [x] Update `agri/frontend/static/css/style.css` with dashboard-specific chart/table controls.
- [ ] Smoke test: open `/admin/dashboard.html` and validate admin gating + charts load.



## Admin Dashboard (Phase 2: Live monitoring + audit logs + sessions)
- [ ] Add DB models/tables for sessions/online presence/activity and audit logs.
- [ ] Implement live monitoring endpoints + websocket/SSE (or polling).
- [ ] Audit log table + admin action tracking middleware.

