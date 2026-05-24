from __future__ import annotations

import asyncio
import json
import uuid
from collections import defaultdict
from datetime import datetime, timezone

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

ws_router = APIRouter()


class ConnectionManager:
    """Manages WebSocket connections per exam_id."""

    def __init__(self) -> None:
        self._connections: dict[str, set[WebSocket]] = defaultdict(set)

    async def connect(self, exam_id: str, websocket: WebSocket) -> None:
        await websocket.accept()
        self._connections[exam_id].add(websocket)

    def disconnect(self, exam_id: str, websocket: WebSocket) -> None:
        self._connections[exam_id].discard(websocket)

    async def broadcast(self, exam_id: str, message: dict) -> None:
        dead: list[WebSocket] = []
        for ws in list(self._connections.get(exam_id, [])):
            try:
                await ws.send_text(json.dumps(message, default=str))
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(exam_id, ws)


manager = ConnectionManager()


@ws_router.websocket("/ws/exams/{exam_id}/monitor")
async def exam_monitor(websocket: WebSocket, exam_id: uuid.UUID) -> None:
    exam_id_str = str(exam_id)
    await manager.connect(exam_id_str, websocket)
    try:
        while True:
            snapshot = {
                "type": "snapshot",
                "exam_id": exam_id_str,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "sessions": [],
            }
            try:
                await websocket.send_text(json.dumps(snapshot, default=str))
            except Exception:
                break
            try:
                await asyncio.wait_for(websocket.receive_text(), timeout=10.0)
            except asyncio.TimeoutError:
                pass
            except WebSocketDisconnect:
                break
    finally:
        manager.disconnect(exam_id_str, websocket)
