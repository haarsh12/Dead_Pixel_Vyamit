"""Authenticated HTTP and WebSocket voice billing endpoints."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, Dict, List, Optional, Tuple

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect, status
from pydantic import BaseModel, Field
from sqlmodel import Session, select

from core.security import get_current_user, verify_token
from core.shop_categories import stored_category
from db.database import database_is_configured, engine, get_session
from db.models import Item, User
from services.voice_service import voice_service


logger = logging.getLogger(__name__)
router = APIRouter()


class VoiceRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=1_000)
    # Kept for Flutter request compatibility. The authenticated user's stored
    # category is used instead so a client cannot override shop context.
    shop_category: Optional[str] = Field(default=None, max_length=60)


def _context_from_session(session: Session, user_id: int) -> Tuple[List[Dict[str, Any]], str]:
    user = session.get(User, user_id)
    if user is None or not user.is_active:
        raise LookupError("Account is unavailable")
    shop_category = stored_category(user.shop_category)
    items = session.exec(
        select(Item).where(
            Item.owner_id == user_id,
            Item.shop_category == shop_category,
        )
    ).all()
    inventory = [
        {
            "master_id": item.master_id,
            "names": item.names,
            "price": item.price,
            "unit": item.unit,
            "category": item.category,
        }
        for item in items
    ]
    return inventory, shop_category


def _load_context(user_id: int) -> Tuple[List[Dict[str, Any]], str]:
    if not database_is_configured() or engine is None:
        raise RuntimeError("The database is not configured")
    with Session(engine) as session:
        return _context_from_session(session, user_id)


def _process_command(user_id: int, text: str, session: Session | None = None) -> Dict[str, Any]:
    inventory, shop_category = (
        _context_from_session(session, user_id) if session is not None else _load_context(user_id)
    )
    return voice_service.process(text, inventory, shop_category)


@router.post("/process")
def process_voice(
    request: VoiceRequest,
    user_id: int = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> Dict[str, Any]:
    """HTTP fallback used by Flutter when the continuous WebSocket is offline."""
    try:
        return _process_command(user_id, request.text.strip(), session)
    except LookupError:
        from fastapi import HTTPException

        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is unavailable")


async def _stream_response(websocket: WebSocket, response: Dict[str, Any]) -> None:
    """Send a UI-compatible token stream followed by the authoritative object."""
    payload = json.dumps(response, ensure_ascii=False, separators=(",", ":"))
    accumulated = ""
    for start in range(0, len(payload), 64):
        token = payload[start : start + 64]
        accumulated += token
        await websocket.send_json({"type": "stream_token", "token": token, "accumulated": accumulated})
        await asyncio.sleep(0)
    await websocket.send_json({"type": "complete", "response": response})


@router.websocket("/ws/stream")
async def voice_websocket_stream(websocket: WebSocket, token: Optional[str] = None) -> None:
    """Continuous, authenticated voice protocol used by ``VoiceAssistantScreen``."""
    user_id = verify_token(token) if token else None
    if user_id is None:
        await websocket.close(code=1008, reason="Authentication is required")
        return

    await websocket.accept()
    await websocket.send_json({"type": "connected", "message": "Voice stream connected"})
    active_task: asyncio.Task[None] | None = None

    async def process_message(text: str) -> None:
        try:
            await websocket.send_json({"type": "processing", "msg": "Vyamit AI is processing..."})
            response = await asyncio.to_thread(_process_command, user_id, text)
            await _stream_response(websocket, response)
        except LookupError:
            await websocket.send_json({"type": "error", "message": "Account is unavailable"})
        except RuntimeError as exc:
            logger.warning("Voice WebSocket unavailable user=%s reason=%s", user_id, type(exc).__name__)
            await websocket.send_json({"type": "error", "message": "Voice service is temporarily unavailable"})
        except Exception:
            logger.exception("Voice WebSocket processing failed user=%s", user_id)
            await websocket.send_json({"type": "error", "message": "Unable to process the voice request"})

    try:
        while True:
            raw_message = await websocket.receive_text()
            try:
                message = json.loads(raw_message)
            except json.JSONDecodeError:
                message = {"action": "process", "text": raw_message}
            if not isinstance(message, dict):
                await websocket.send_json({"type": "error", "message": "Invalid request"})
                continue
            action = message.get("action", "process")
            if action == "ping":
                await websocket.send_json({"type": "pong"})
                continue
            if action == "interrupt":
                if active_task and not active_task.done():
                    active_task.cancel()
                await websocket.send_json({"type": "interrupted"})
                continue
            if action != "process":
                await websocket.send_json({"type": "error", "message": "Unsupported action"})
                continue
            text = str(message.get("text") or "").strip()
            if not text or len(text) > 1_000:
                await websocket.send_json({"type": "error", "message": "Voice text must be between 1 and 1000 characters"})
                continue
            if active_task and not active_task.done():
                active_task.cancel()
            active_task = asyncio.create_task(process_message(text))
    except WebSocketDisconnect:
        logger.info("Voice WebSocket disconnected user=%s", user_id)
    finally:
        if active_task and not active_task.done():
            active_task.cancel()
