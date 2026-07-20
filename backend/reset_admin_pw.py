import asyncio
from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.models.user import User
from app.core.security import get_password_hash

PHONE = '9000000003'
NEW_PASSWORD = 'admin123'

# Debug: print expected hash
EXPECTED_HASH = get_password_hash(NEW_PASSWORD)
print('EXPECTED_HASH', EXPECTED_HASH)


async def main():
    async with AsyncSessionLocal() as db:
        res = await db.execute(select(User).where(User.phone == PHONE))
        u = res.scalar_one_or_none()
        if not u:
            raise SystemExit(f"User not found for phone={PHONE}")
        u.hashed_password = get_password_hash(NEW_PASSWORD)
        await db.flush()
        print('Updated hashed_password for', PHONE)

asyncio.run(main())

