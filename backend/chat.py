from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect, status, Query
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from auth import SECRET_KEY, ALGORITHM, get_current_user
from database import get_db, AsyncSessionLocal
from models import User, Room, Message
from schemas import RoomCreate, RoomOut, MessageOut

router = APIRouter(tags=["chat"])


# ── Connection Manager ────────────────────────────────────────────────────────

class ConnectionManager:
    def __init__(self):
        # { room_id: { user_id: WebSocket } }
        self.rooms: dict[int, dict[int, WebSocket]] = {}
        # { user_id: WebSocket }
        self.global_connections: dict[int, WebSocket] = {}

    async def connect(self, room_id: int, user_id: int, ws: WebSocket):
        await ws.accept()
        if room_id not in self.rooms:
            self.rooms[room_id] = {}
        self.rooms[room_id][user_id] = ws

    async def connect_global(self, user_id: int, ws: WebSocket):
        await ws.accept()
        self.global_connections[user_id] = ws

    def disconnect(self, room_id: int, user_id: int):
        if room_id in self.rooms:
            self.rooms[room_id].pop(user_id, None)
            if not self.rooms[room_id]:
                del self.rooms[room_id]

    def disconnect_global(self, user_id: int):
        self.global_connections.pop(user_id, None)

    async def broadcast(self, room_id: int, message: dict, exclude_user_id: int | None = None):
        if room_id not in self.rooms:
            return
        dead = []
        for uid, ws in self.rooms[room_id].items():
            if uid == exclude_user_id:
                continue
            try:
                await ws.send_json(message)
            except Exception:
                dead.append(uid)
        for uid in dead:
            self.disconnect(room_id, uid)

    async def broadcast_global(self, message: dict):
        dead = []
        for uid, ws in self.global_connections.items():
            try:
                await ws.send_json(message)
            except Exception:
                dead.append(uid)
        for uid in dead:
            self.disconnect_global(uid)


manager = ConnectionManager()


# ────────────────────────

async def get_user_from_token(token: str) -> User | None:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str | None = payload.get("sub")
        if user_id is None:
            return None
    except JWTError:
        return None

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(User).where(User.id == int(user_id)))
        return result.scalar_one_or_none()


# ── Routes: rooms ────────────────────────────────────────────────────────────

@router.post("/rooms", response_model=RoomOut, status_code=status.HTTP_201_CREATED)
async def create_room(
    data: RoomCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    result = await db.execute(select(Room).where(Room.name == data.name))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Комната с таким именем уже существует")

    room = Room(name=data.name)
    db.add(room)
    await db.commit()
    await db.refresh(room)

    await manager.broadcast_global({
        "type": "room_created",
        "room": {
            "id": room.id,
            "name": room.name,
            "created_at": room.created_at.isoformat(),
        },
    })
    return room


@router.get("/rooms", response_model=list[RoomOut])
async def list_rooms(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    result = await db.execute(select(Room).order_by(Room.created_at))
    return result.scalars().all()


@router.delete("/rooms/{room_id}", status_code=204)
async def delete_room(
    room_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    result = await db.execute(select(Room).where(Room.id == room_id))
    room = result.scalar_one_or_none()
    if room is None:
        raise HTTPException(status_code=404, detail="Комната не найдена")

    await db.execute(Message.__table__.delete().where(Message.room_id == room_id))
    await db.delete(room)
    await db.commit()

    await manager.broadcast(room_id, {
        "type": "room_deleted",
        "room_id": room_id,
    })
    await manager.broadcast_global({
        "type": "room_deleted",
        "room_id": room_id,
    })


@router.get("/rooms/{room_id}/messages", response_model=list[MessageOut])
async def get_history(
    room_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    limit: int = 50,
):
    result = await db.execute(
        select(Message)
        .where(Message.room_id == room_id)
        .options(selectinload(Message.author))
        .order_by(Message.created_at.desc())
        .limit(limit)
    )
    messages = result.scalars().all()
    return list(reversed(messages))


# ── WebSocket: global ────────────────────────────────────

@router.websocket("/ws/global")
async def websocket_global(
    ws: WebSocket,
    token: str = Query(...),
):
    user = await get_user_from_token(token)
    if user is None:
        await ws.close(code=4001)
        return

    await manager.connect_global(user.id, ws)
    try:
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        manager.disconnect_global(user.id)


# ── WebSocket ────────────────────────────────────────────────────────

@router.websocket("/ws/{room_id}")
async def websocket_endpoint(
    ws: WebSocket,
    room_id: int,
    token: str = Query(...),
):
    user = await get_user_from_token(token)
    if user is None:
        await ws.close(code=4001)
        return

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Room).where(Room.id == room_id))
        room = result.scalar_one_or_none()
    if room is None:
        await ws.close(code=4004)
        return

    await manager.connect(room_id, user.id, ws)
    await manager.broadcast(room_id, {
        "type": "system",
        "text": f"{user.username} вошёл в чат",
    }, exclude_user_id=user.id)

    try:
        while True:
            data = await ws.receive_json()
            text = (data.get("text") or "").strip()
            if not text:
                continue

            async with AsyncSessionLocal() as db:
                msg = Message(text=text, user_id=user.id, room_id=room_id)
                db.add(msg)
                await db.commit()
                await db.refresh(msg)

            payload = {
                "type": "message",
                "id": msg.id,
                "text": msg.text,
                "username": user.username,
                "user_id": user.id,
                "created_at": msg.created_at.isoformat(),
            }
            await manager.broadcast(room_id, payload)

    except WebSocketDisconnect:
        manager.disconnect(room_id, user.id)
        await manager.broadcast(room_id, {
            "type": "system",
            "text": f"{user.username} покинул чат",
        })
