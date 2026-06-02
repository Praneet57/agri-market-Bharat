from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional
from pydantic import BaseModel, Field
from app.core.database import get_db
from app.core.redis import get_redis
from app.core.security import *
from app.models.user import User
from app.schemas import UserRegister, UserLogin, Token, UserOut, UserUpdate

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/register", response_model=Token, status_code=201)
async def register(data: UserRegister, request: Request, db: AsyncSession = Depends(get_db)):
    ip = request.client.host if request.client else "unknown"
    await check_rate_limit(f"register:{ip}", 5, 3600)
    r1 = await db.execute(select(User).where(User.phone == data.phone))
    if r1.scalar_one_or_none():
        raise HTTPException(400, "Phone already registered")
    if data.email:
        r2 = await db.execute(select(User).where(User.email == data.email))
        if r2.scalar_one_or_none():
            raise HTTPException(400, "Email already registered")
    user = User(full_name=data.full_name, phone=data.phone, email=data.email,
                hashed_password=get_password_hash(data.password), role=data.role.value,
                village=data.village, district=data.district, state=data.state,
                latitude=data.latitude, longitude=data.longitude)
    db.add(user); await db.flush(); await db.refresh(user)
    at = create_access_token({"sub": str(user.id), "role": user.role})
    rt = create_refresh_token({"sub": str(user.id)})
    rp = decode_token(rt); await store_refresh_token(user.id, rp["jti"])
    return Token(access_token=at, refresh_token=rt, user=UserOut.model_validate(user))

@router.post("/login", response_model=Token)
async def login(data: UserLogin, request: Request, db: AsyncSession = Depends(get_db)):
    await check_rate_limit(f"login:{data.phone}", 10, 900)
    result = await db.execute(select(User).where(User.phone == data.phone))
    user = result.scalar_one_or_none()
    if not user or not verify_password(data.password, user.hashed_password):
        raise HTTPException(401, "Invalid phone or password")
    if not user.is_active:
        raise HTTPException(400, "Account deactivated")
    at = create_access_token({"sub": str(user.id), "role": user.role})
    rt = create_refresh_token({"sub": str(user.id)})
    rp = decode_token(rt); await store_refresh_token(user.id, rp["jti"])
    return Token(access_token=at, refresh_token=rt, user=UserOut.model_validate(user))

class LogoutReq(BaseModel):
    refresh_token: Optional[str] = None

@router.post("/logout")
async def logout(body: LogoutReq, request: Request, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    jti = getattr(request.state, "jti", None)
    if jti:
        auth = request.headers.get("Authorization", "").replace("Bearer ", "")
        try:
            p = decode_token(auth); await blacklist_token(jti, p.get("exp", 0))
        except Exception: pass
    if body.refresh_token:
        try:
            rp = decode_token(body.refresh_token)
            if rp.get("type") == "refresh":
                await validate_and_rotate_refresh(current_user.id, rp["jti"])
        except Exception: pass
    return {"message": "Logged out successfully"}

@router.post("/logout-all")
async def logout_all(current_user: User = Depends(get_current_user)):
    await blacklist_all_user_tokens(current_user.id)
    await revoke_all_refresh_tokens(current_user.id)
    return {"message": "All sessions terminated"}

class RefreshReq(BaseModel):
    refresh_token: str

@router.post("/refresh")
async def refresh_tokens(body: RefreshReq, db: AsyncSession = Depends(get_db)):
    try: payload = decode_token(body.refresh_token)
    except: raise HTTPException(401, "Invalid refresh token")
    if payload.get("type") != "refresh":
        raise HTTPException(401, "Expected refresh token")
    user_id = int(payload.get("sub", 0)); jti = payload.get("jti")
    if not await validate_and_rotate_refresh(user_id, jti):
        await blacklist_all_user_tokens(user_id); await revoke_all_refresh_tokens(user_id)
        raise HTTPException(401, "Refresh token reuse detected. All sessions revoked.")
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user or not user.is_active: raise HTTPException(401, "User not found")
    new_at = create_access_token({"sub": str(user.id), "role": user.role})
    new_rt = create_refresh_token({"sub": str(user.id)})
    nrp = decode_token(new_rt); await store_refresh_token(user.id, nrp["jti"])
    return {"access_token": new_at, "refresh_token": new_rt, "token_type": "bearer"}

class ForgotPwdReq(BaseModel):
    phone: str

class ResetPwdReq(BaseModel):
    reset_token: str; new_password: str = Field(..., min_length=6)

@router.post("/forgot-password")
async def forgot_password(data: ForgotPwdReq, request: Request, db: AsyncSession = Depends(get_db)):
    await check_rate_limit(f"forgot:{data.phone}", 3, 3600)
    result = await db.execute(select(User).where(User.phone == data.phone))
    user = result.scalar_one_or_none()
    if not user: return {"message": "If this phone is registered, a reset link has been sent."}
    token = create_verification_token(user.id, "password_reset")
    payload = decode_token(token); r = await get_redis()
    await r.setex(f"pwd_reset:{payload['jti']}", 900, str(user.id))
    return {"message": "Reset token generated.", "reset_token": token}

@router.post("/reset-password")
async def reset_password(data: ResetPwdReq, db: AsyncSession = Depends(get_db)):
    try: payload = decode_token(data.reset_token)
    except: raise HTTPException(400, "Invalid or expired reset token")
    if payload.get("type") != "otp" or payload.get("purpose") != "password_reset":
        raise HTTPException(400, "Wrong token type")
    r = await get_redis(); uid = await r.getdel(f"pwd_reset:{payload['jti']}")
    if not uid: raise HTTPException(400, "Token already used or expired")
    result = await db.execute(select(User).where(User.id == int(uid)))
    user = result.scalar_one_or_none()
    if not user: raise HTTPException(404, "User not found")
    user.hashed_password = get_password_hash(data.new_password); await db.flush()
    await blacklist_all_user_tokens(user.id); await revoke_all_refresh_tokens(user.id)
    return {"message": "Password reset successfully. Please login."}

class ChangePwdReq(BaseModel):
    current_password: str; new_password: str = Field(..., min_length=6)

@router.post("/change-password")
async def change_password(data: ChangePwdReq, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    if not verify_password(data.current_password, current_user.hashed_password):
        raise HTTPException(400, "Current password incorrect")
    current_user.hashed_password = get_password_hash(data.new_password); await db.flush()
    await blacklist_all_user_tokens(current_user.id); await revoke_all_refresh_tokens(current_user.id)
    return {"message": "Password changed. Please login again."}

@router.post("/send-verification")
async def send_verification(current_user: User = Depends(get_current_user)):
    if current_user.is_verified: return {"message": "Already verified"}
    token = create_verification_token(current_user.id, "phone_verify")
    payload = decode_token(token); r = await get_redis()
    await r.setex(f"verify:{payload['jti']}", 900, str(current_user.id))
    return {"message": "Verification token generated.", "verify_token": token}

class VerifyReq(BaseModel):
    verify_token: str

@router.post("/verify-phone")
async def verify_phone(data: VerifyReq, db: AsyncSession = Depends(get_db)):
    try: payload = decode_token(data.verify_token)
    except: raise HTTPException(400, "Invalid token")
    if payload.get("type") != "otp" or payload.get("purpose") != "phone_verify":
        raise HTTPException(400, "Wrong token type")
    r = await get_redis(); uid = await r.getdel(f"verify:{payload['jti']}")
    if not uid: raise HTTPException(400, "Token used or expired")
    result = await db.execute(select(User).where(User.id == int(uid)))
    user = result.scalar_one_or_none()
    if user: user.is_verified = True; await db.flush()
    return {"message": "Phone verified! ✅"}

@router.get("/me", response_model=UserOut)
async def get_me(current_user: User = Depends(get_current_user)):
    return current_user

@router.put("/me", response_model=UserOut)
async def update_profile(data: UserUpdate, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(current_user, field, value)
    await db.flush(); await db.refresh(current_user); return current_user

@router.get("/sessions")
async def list_sessions(current_user: User = Depends(get_current_user)):
    r = await get_redis(); keys = await r.keys(f"rt:{current_user.id}:*")
    return {"active_sessions": len(keys)}

@router.get("/users/{user_id}", response_model=UserOut)
async def get_user(user_id: int, db: AsyncSession = Depends(get_db), _=Depends(get_current_user)):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user: raise HTTPException(404, "User not found")
    return user
