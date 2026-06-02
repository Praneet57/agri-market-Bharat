from celery import Celery
from app.core.config import settings

celery_app = Celery("agri", broker=settings.CELERY_BROKER_URL, backend=settings.CELERY_RESULT_BACKEND)
celery_app.conf.update(task_serializer="json", accept_content=["json"], timezone="Asia/Kolkata", enable_utc=True,
    beat_schedule={"expire-demands":{"task":"app.workers.tasks.expire_old_demands","schedule":3600.0}})

@celery_app.task(name="app.workers.tasks.send_sms_task")
def send_sms_task(phone: str, message: str):
    import asyncio
    from app.services.notification_service import send_sms
    asyncio.run(send_sms(phone, message))

@celery_app.task(name="app.workers.tasks.generate_agreement_task")
def generate_agreement_task(order_id: int):
    import asyncio
    async def _run():
        from app.core.database import AsyncSessionLocal
        from sqlalchemy import select
        from app.models.order import Order
        from app.models.payment import Agreement
        from app.services.pdf_service import generate_agreement_pdf
        async with AsyncSessionLocal() as db:
            result = await db.execute(select(Order).where(Order.id==order_id))
            order = result.scalar_one_or_none()
            if order:
                pdf_path = await generate_agreement_pdf(order, db)
                ex = await db.execute(select(Agreement).where(Agreement.order_id==order_id))
                ag = ex.scalar_one_or_none()
                if not ag: ag = Agreement(order_id=order_id, pdf_key=pdf_path); db.add(ag)
                else: ag.pdf_key = pdf_path
                await db.commit()
    asyncio.run(_run())

@celery_app.task(name="app.workers.tasks.expire_old_demands")
def expire_old_demands():
    import asyncio
    async def _run():
        from app.core.database import AsyncSessionLocal
        from sqlalchemy import update
        from app.models.demand import Demand
        from datetime import datetime
        async with AsyncSessionLocal() as db:
            await db.execute(update(Demand).where(Demand.status=="open",Demand.required_by<datetime.utcnow()).values(status="expired"))
            await db.commit()
    asyncio.run(_run())
