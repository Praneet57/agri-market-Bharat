# 🌾 Agri Marketplace

Production-ready platform connecting farmers directly with buyers. Real-time chat, location-based matching, escrow payments, JWT auth with token blacklisting, and auto-generated PDF contracts.

---

## 🚀 Run in 3 commands

```bash
git clone https://github.com/YOUR_USERNAME/agri-marketplace.git
cd agri-marketplace
make setup
```

Then open **http://localhost**

```
Farmer login:  9000000001 / farmer123
Buyer login:   9000000002 / buyer123
API Docs:      http://localhost:8000/api/docs
```

---

## 🏗 Architecture

```
Browser (HTML + CSS + JS)
         │ HTTP / WSS
         ▼
    Nginx (port 80)
         │
         ▼
  FastAPI + JWT Auth
  ├── Auth (register/login/logout/refresh/reset)
  ├── Products & Demands
  ├── Orders (full lifecycle)
  ├── Payments (Razorpay + Escrow)
  ├── Agreements (PDF auto-generation)
  ├── Real-time Chat (WebSocket)
  ├── Location Matching (haversine)
  └── Admin panel
         │
   ┌─────┴─────┐
   ▼           ▼
PostgreSQL    Redis
(data)  (JWT blacklist + Celery + WS)
              │
              ▼
         Celery Workers
         (PDF gen, SMS, scheduled)
```

---

## ⚡ Features

| Feature | Status |
|---|---|
| JWT Auth + Refresh token rotation | ✅ |
| Token blacklisting (instant logout) | ✅ |
| Password reset via token | ✅ |
| Phone verification | ✅ |
| Farmer product listings | ✅ |
| Buyer demand posting | ✅ |
| Location-based matching | ✅ |
| Real-time WebSocket chat | ✅ |
| Order lifecycle (pending→completed) | ✅ |
| Razorpay payments + UPI | ✅ |
| Escrow system | ✅ |
| Auto PDF agreements | ✅ |
| Digital signing | ✅ |
| Rating system | ✅ |
| Celery background tasks | ✅ |
| Admin dashboard | ✅ |
| Docker Compose | ✅ |
| GitHub Actions CI/CD | ✅ |
| Render.com free deployment | ✅ |

---

## 🛠 Tech Stack

| Layer | Technology |
|---|---|
| Backend | FastAPI + Python 3.11 |
| Database | PostgreSQL 15 + SQLAlchemy (async) |
| Cache / Queue | Redis 7 |
| Background jobs | Celery + Celery Beat |
| Frontend | HTML5 + CSS3 + Vanilla JS |
| Payments | Razorpay (UPI / GPay / PhonePe) |
| PDF | ReportLab |
| Auth | JWT (python-jose) + bcrypt |
| DevOps | Docker, Docker Compose, Nginx |
| CI/CD | GitHub Actions |

---

## 📁 Project Structure

```
agri-marketplace/
├── backend/
│   ├── app/
│   │   ├── core/          ← config, database, security (JWT), redis
│   │   ├── models/        ← SQLAlchemy models (user, product, order…)
│   │   ├── schemas/       ← Pydantic request/response models
│   │   ├── routers/       ← API endpoints (auth, products, orders, chat…)
│   │   ├── services/      ← PDF generator, notifications
│   │   ├── workers/       ← Celery background tasks
│   │   ├── middleware/    ← Logging, security headers
│   │   └── tests/         ← pytest test suite
│   ├── alembic/           ← Database migrations
│   ├── seed.py            ← Demo data
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── index.html         ← Landing page
│   ├── login.html / register.html
│   ├── chat.html          ← Real-time WebSocket chat
│   ├── profile.html       ← User profile + security
│   ├── farmer/dashboard.html
│   ├── buyer/dashboard.html
│   ├── admin/dashboard.html
│   └── static/css + js
├── nginx/nginx.conf
├── docker-compose.yml
├── render.yaml            ← Free Render.com deployment
├── Makefile               ← Convenient commands
└── .github/workflows/     ← CI/CD pipeline
```

---

## 📡 API Endpoints

```
POST   /api/v1/auth/register          Register farmer or buyer
POST   /api/v1/auth/login             Login → JWT tokens
POST   /api/v1/auth/logout            Blacklist token (instant)
POST   /api/v1/auth/logout-all        Logout all devices
POST   /api/v1/auth/refresh           Rotate refresh token
POST   /api/v1/auth/forgot-password   Request reset token
POST   /api/v1/auth/reset-password    Reset with token
POST   /api/v1/auth/change-password   Change password
POST   /api/v1/auth/send-verification Send phone OTP
POST   /api/v1/auth/verify-phone      Verify phone number
GET    /api/v1/auth/me                My profile
PUT    /api/v1/auth/me                Update profile
GET    /api/v1/auth/sessions          Active sessions

POST   /api/v1/products               Create listing (farmer)
GET    /api/v1/products               Browse products
GET    /api/v1/products/my            My products
PUT    /api/v1/products/{id}          Update listing
DELETE /api/v1/products/{id}          Remove listing

POST   /api/v1/demands                Post demand (buyer)
GET    /api/v1/demands                Browse demands
GET    /api/v1/demands/my             My demands

POST   /api/v1/orders                 Create order
GET    /api/v1/orders                 My orders
PATCH  /api/v1/orders/{id}/status     Update status

POST   /api/v1/payments/create        Create Razorpay order
POST   /api/v1/payments/verify        Verify + activate escrow
POST   /api/v1/payments/{id}/release-escrow  Release payment

POST   /api/v1/agreements/{id}/generate     Generate PDF
POST   /api/v1/agreements/{id}/sign         Digital sign
GET    /api/v1/agreements/{id}/download     Download PDF

WS     /api/v1/chat/ws/{order_id}?token=   Real-time chat
GET    /api/v1/chat/{order_id}/messages     Chat history
GET    /api/v1/chat/rooms/my               My chat rooms

GET    /api/v1/match/products-for-demand/{id}  Match products
GET    /api/v1/match/demands-for-product/{id}  Match demands
GET    /api/v1/match/nearby-farmers            Nearby farmers

POST   /api/v1/ratings                Create rating
GET    /api/v1/admin/stats            Platform stats (admin)
GET    /api/v1/admin/users            All users (admin)
GET    /api/health                    Health check
```

---

## 🔐 JWT Auth Flow

```
Register/Login → access_token (60 min) + refresh_token (7 days)
                        │
              Token stored in localStorage
                        │
              Every request → Authorization: Bearer <token>
                        │
              Token blacklisted on logout (Redis)
              Refresh token = one-time use (rotation)
              Replay attack → all sessions revoked
```

---

## ☁️ Free Deployment (Render.com)

1. Push to GitHub
2. Go to [render.com](https://render.com) → New → Blueprint
3. Connect your repo → it reads `render.yaml` automatically
4. Set secrets in dashboard:
   - `SECRET_KEY` = any 32+ char random string
   - `RAZORPAY_KEY_ID` / `RAZORPAY_KEY_SECRET`
5. Deploy!

---

## 🔧 Common Commands

```bash
make setup      # First-time: build + start + seed
make dev        # Start with hot reload
make stop       # Stop all containers
make test       # Run tests
make migrate    # Apply DB migrations
make seed       # Re-seed demo data
make logs       # Tail API logs
make shell      # Shell into API container
make clean      # Remove everything (containers + volumes)
```

---

## 💳 Razorpay Test Keys (Free)

1. Sign up at [razorpay.com](https://razorpay.com)
2. Dashboard → Settings → API Keys → Generate Test Key
3. Add to `backend/.env`:
   ```
   RAZORPAY_KEY_ID=rzp_test_xxxx
   RAZORPAY_KEY_SECRET=xxxx
   ```
4. Test card: `4111 1111 1111 1111`, any future date, any CVV

---

Built with ❤️ for Indian Farmers
