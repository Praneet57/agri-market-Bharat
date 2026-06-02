from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, update
from typing import Dict, List
import json
from datetime import datetime
from app.core.database import get_db
from app.core.security import get_current_user, decode_token
from app.models.user import User
from app.models.payment import ChatMessage
from app.models.order import Order
from app.schemas import MessageOut

router = APIRouter(prefix="/chat", tags=["Chat"])

class ConnectionManager:
    def __init__(self):
        self.rooms: Dict[str, List[tuple]] = {}
    async def connect(self, room_id: str, user_id: int, ws: WebSocket):
        await ws.accept()
        self.rooms.setdefault(room_id, []).append((user_id, ws))
    def disconnect(self, room_id: str, user_id: int, ws: WebSocket):
        if room_id in self.rooms:
            self.rooms[room_id] = [(u,w) for u,w in self.rooms[room_id] if not (u==user_id and w==ws)]
            if not self.rooms[room_id]: del self.rooms[room_id]
    async def broadcast(self, room_id: str, message: dict, exclude: int=None):
        for uid, ws in self.rooms.get(room_id, []):
            if exclude and uid == exclude: continue
            try: await ws.send_json(message)
            except: pass
    def online_users(self, room_id: str) -> List[int]:
        return [uid for uid,_ in self.rooms.get(room_id, [])]

manager = ConnectionManager()

@router.websocket("/ws/{order_id}")
async def websocket_chat(websocket: WebSocket, order_id: int, token: str):
    try:
        payload = decode_token(token); user_id = int(payload["sub"])
    except:
        await websocket.close(code=4001, reason="Unauthorized"); return
    room_id = f"order_{order_id}"
    await manager.connect(room_id, user_id, websocket)
    await manager.broadcast(room_id, {"type":"presence","user_id":user_id,"status":"online","online_users":manager.online_users(room_id)})
    try:
        while True:
            raw = await websocket.receive_text()
            data = json.loads(raw)
            if data.get("type") == "message":
                from app.core.database import AsyncSessionLocal
                async with AsyncSessionLocal() as db:
                    msg = ChatMessage(order_id=order_id, sender_id=user_id, message=data.get("message",""), message_type=data.get("message_type","text"))
                    db.add(msg); await db.flush(); await db.refresh(msg)
                    cat = msg.created_at.isoformat() if msg.created_at else datetime.utcnow().isoformat()
                    mid = msg.id
                await manager.broadcast(room_id, {"type":"message","id":mid,"order_id":order_id,"sender_id":user_id,"message":data.get("message",""),"message_type":data.get("message_type","text"),"created_at":cat})
            elif data.get("type") == "typing":
                await manager.broadcast(room_id, {"type":"typing","user_id":user_id,"is_typing":data.get("is_typing",False)}, exclude=user_id)
    except WebSocketDisconnect:
        manager.disconnect(room_id, user_id, websocket)
        await manager.broadcast(room_id, {"type":"presence","user_id":user_id,"status":"offline","online_users":manager.online_users(room_id)})

@router.get("/{order_id}/messages", response_model=List[MessageOut])
async def get_messages(order_id: int, limit: int=50, offset: int=0, current_user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db)):
    ord_r = await db.execute(select(Order).where(Order.id==order_id))
    order = ord_r.scalar_one_or_none()
    if not order: raise HTTPException(404, "Order not found")
    if order.farmer_id != current_user.id and order.buyer_id != current_user.id: raise HTTPException(403, "Not your order")
    result = await db.execute(select(ChatMessage).where(ChatMessage.order_id==order_id).order_by(ChatMessage.created_at.asc()).offset(offset).limit(limit))
    await db.execute(update(ChatMessage).where(and_(ChatMessage.order_id==order_id,ChatMessage.sender_id!=current_user.id,ChatMessage.is_read==False)).values(is_read=True))
    return [MessageOut.model_validate(m) for m in result.scalars().all()]

@router.get("/rooms/my")
async def my_chat_rooms(current_user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db)):
    result = await db.execute(select(Order).where(Order.farmer_id==current_user.id if True else Order.buyer_id==current_user.id))
    from sqlalchemy import or_
    result = await db.execute(select(Order).where(or_(Order.farmer_id==current_user.id,Order.buyer_id==current_user.id)).order_by(Order.created_at.desc()))
    return [{"order_id":o.id,"order_number":o.order_number,"room_id":f"order_{o.id}","status":o.status,"is_online":len(manager.online_users(f"order_{o.id}"))>1} for o in result.scalars().all()]
