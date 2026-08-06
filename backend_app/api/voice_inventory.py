"""Authenticated voice-to-inventory endpoint."""

from typing import Any, Dict, List

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlmodel import Session, select

from core.security import get_current_user
from db.database import get_session
from db.models import Item
from services.voice_inventory_service import voice_inventory_service


router = APIRouter()


class VoiceInventoryRequest(BaseModel):
    raw_text: str = Field(..., min_length=1, max_length=2_000)


class VoiceInventoryResponse(BaseModel):
    categories: List[Dict[str, Any]]
    raw_text: str


@router.post("/voice-parse", response_model=VoiceInventoryResponse)
def parse_voice_inventory(
    request: VoiceInventoryRequest,
    user_id: int = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> Dict[str, Any]:
    """Parse a transcription while only considering the authenticated user's stock."""
    items = session.exec(select(Item).where(Item.owner_id == user_id)).all()
    existing_items: List[Dict[str, Any]] = []
    categories = set()
    for item in items:
        existing_items.append(
            {
                "id": item.master_id,
                "names": item.names,
                "price": item.price,
                "unit": item.unit,
                "category": item.category,
            }
        )
        if item.category:
            categories.add(item.category)
    return voice_inventory_service.parse(request.raw_text, existing_items, sorted(categories))
