import httpx
from app.core.config import settings

async def send_sms(to_phone: str, message: str) -> bool:
    if not settings.TWILIO_ACCOUNT_SID:
        print(f"[SMS DEMO] {to_phone}: {message}"); return False
    url = f"https://api.twilio.com/2010-04-01/Accounts/{settings.TWILIO_ACCOUNT_SID}/Messages.json"
    async with httpx.AsyncClient() as client:
        try:
            r = await client.post(url, auth=(settings.TWILIO_ACCOUNT_SID,settings.TWILIO_AUTH_TOKEN), data={"To":to_phone,"From":settings.TWILIO_PHONE_NUMBER,"Body":message}, timeout=10)
            return r.status_code==201
        except: return False

async def notify_order_event(order_number:str, status:str, farmer_phone:str=None, buyer_phone:str=None):
    msgs={"pending":"AgriMarket: New order #{n} placed!","accepted":"AgriMarket: Order #{n} accepted!","paid":"AgriMarket: Payment confirmed for order #{n}.","delivered":"AgriMarket: Order #{n} delivered. Please confirm receipt.","completed":"AgriMarket: Order #{n} complete. Thank you!"}
    msg=msgs.get(status,f"AgriMarket: Order #{order_number} updated to {status}.").replace("{n}",order_number)
    if farmer_phone: await send_sms(farmer_phone, msg)
    if buyer_phone: await send_sms(buyer_phone, msg)
