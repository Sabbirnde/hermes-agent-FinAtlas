"""COMPARE AI — WebSocket Router for live research updates."""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import asyncio
import json

router = APIRouter()
_connections: dict[str, WebSocket] = {}


@router.websocket("/{run_id}")
async def research_websocket(websocket: WebSocket, run_id: str):
    """
    WebSocket endpoint for live research pipeline updates.
    Client connects and receives state transitions in real time.
    """
    await websocket.accept()
    _connections[run_id] = websocket

    try:
        await websocket.send_json({
            "type": "connected",
            "run_id": run_id,
            "message": "Connected to COMPARE AI research stream",
        })

        while True:
            # Keep connection alive, send pings
            await asyncio.sleep(5)
            await websocket.send_json({"type": "ping"})

    except WebSocketDisconnect:
        _connections.pop(run_id, None)


async def broadcast_state(run_id: str, state: str, data: dict = None):
    """Broadcast a state change to the connected WebSocket client."""
    ws = _connections.get(run_id)
    if ws:
        try:
            await ws.send_json({
                "type": "state_change",
                "run_id": run_id,
                "state": state,
                "data": data or {},
            })
        except Exception:
            _connections.pop(run_id, None)


async def broadcast_result(run_id: str, products: list):
    """Broadcast research results to the connected client."""
    ws = _connections.get(run_id)
    if ws:
        try:
            await ws.send_json({
                "type": "results",
                "run_id": run_id,
                "products": products,
            })
        except Exception:
            _connections.pop(run_id, None)
