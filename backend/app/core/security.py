from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import uuid
from app.core.config import settings
from app.core.database import get_db
from app.core.redis import get_redis

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto", bcrypt__rounds=12)

def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def _build_token(data: dict, token_type: str, expires_delta: timedelta) -> str:
    payload = {**data, "jti": str(uuid.uuid4()), "type": token_type,
               "iat": int(datetime.utcnow().timestamp()), "exp": datetime.utcnow() + expires_delta}
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    return _build_token(data, "access", expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))

def create_refresh_token(data: dict) -> str:
    return _build_token(data, "refresh", timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS))

def create_verification_token(user_id: int, purpose: str) -> str:
    return _build_token({"sub": str(user_id), "purpose": purpose}, "otp", timedelta(minutes=15))

def decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except JWTError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Token invalid or expired: {str(e)}", headers={"WWW-Authenticate": "Bearer"})

async def blacklist_token(jti: str, exp: int):
    r = await get_redis()
    ttl = max(1, exp - int(datetime.utcnow().timestamp()))
    await r.setex(f"bl:jti:{jti}", ttl, "1")

async def is_token_blacklisted(jti: str) -> bool:
    r = await get_redis()
    return await r.exists(f"bl:jti:{jti}") == 1

async def blacklist_all_user_tokens(user_id: int):
    r = await get_redis()
    gen = int(datetime.utcnow().timestamp())
    await r.setex(f"bl:user:{user_id}:gen", 86400 * 30, str(gen))
    return gen

async def get_user_token_gen(user_id: int) -> Optional[int]:
    r = await get_redis()
    val = await r.get(f"bl:user:{user_id}:gen")
    return int(val) if val else None

async def store_refresh_token(user_id: int, jti: str):
    r = await get_redis()
    await r.setex(f"rt:{user_id}:{jti}", settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400, "1")

async def validate_and_rotate_refresh(user_id: int, jti: str) -> bool:
    r = await get_redis()
    return await r.getdel(f"rt:{user_id}:{jti}") is not None

async def revoke_all_refresh_tokens(user_id: int):
    r = await get_redis()
    keys = await r.keys(f"rt:{user_id}:*")
    if keys:
        await r.delete(*keys)

async def check_rate_limit(key: str, max_attempts: int, window_seconds: int):
    r = await get_redis()
    rkey = f"rl:{key}"
    count = await r.incr(rkey)
    if count == 1:
        await r.expire(rkey, window_seconds)
    if count > max_attempts:
        ttl = await r.ttl(rkey)
        raise HTTPException(status_code=429, detail=f"Too many attempts. Try again in {ttl}s.")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

async def get_current_user(request: Request, token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)):
    from app.models.user import User
    payload = decode_token(token)
    if payload.get("type") != "access":
        raise HTTPException(status_code=401, detail="Expected access token")
    jti = payload.get("jti")
    if jti and await is_token_blacklisted(jti):
        raise HTTPException(status_code=401, detail="Token revoked. Please login again.")
    user_id = int(payload.get("sub", 0))
    issued_at = payload.get("iat", 0)
    gen = await get_user_token_gen(user_id)
    if gen and issued_at < gen:
        raise HTTPException(status_code=401, detail="Session expired. Please login again.")
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Account deactivated")
    request.state.user_id = user_id
    request.state.jti = jti
    return user

async def get_optional_user(request: Request, db: AsyncSession = Depends(get_db)):
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        return None
    try:
        return await get_current_user(request, auth.split(" ")[1], db)
    except Exception:
        return None

async def require_farmer(current_user=Depends(get_current_user)):
    if current_user.role != "farmer":
        raise HTTPException(status_code=403, detail="Farmer access only")
    return current_user

async def require_buyer(current_user=Depends(get_current_user)):
    if current_user.role != "buyer":
        raise HTTPException(status_code=403, detail="Buyer access only")
    return current_user

async def require_marketplace_user(current_user=Depends(get_current_user)):
    if current_user.role == "admin":
        raise HTTPException(status_code=403, detail="Admin marketplace actions are not allowed")
    return current_user

async def require_admin(current_user=Depends(get_current_user)):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access only")
    return current_user
