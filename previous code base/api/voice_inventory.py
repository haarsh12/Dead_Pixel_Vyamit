"""
Voice Inventory API
Handles voice-based inventory addition
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from pydantic import BaseModel
from typing import List, Dict, Any
from app.db.database import get_session
from app.db.models import Item
from app.core.security import jwt, SECRET_KEY, ALGORITHM
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.services.voice_inventory_service import parse_voice_inventory
import json

security = HTTPBearer()
router = APIRouter()


# Request/Response Models
class VoiceInventoryRequest(BaseModel):
    raw_text: str


class VoiceInventoryResponse(BaseModel):
    categories: List[Dict[str, Any]]
    raw_text: str


# Helper: Get current user from Token
def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    session: Session = Depends(get_session)
):
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid authentication credentials")
            
        return int(user_id)
    except Exception as e:
        print(f"DEBUG: Token Error: {e}")
        raise HTTPException(status_code=401, detail="Invalid authentication credentials")


@router.post("/voice-parse", response_model=VoiceInventoryResponse)
async def parse_voice_inventory_endpoint(
    request: VoiceInventoryRequest,
    session: Session = Depends(get_session),
    user_id: int = Depends(get_current_user)
):
    """
    Parse voice input into structured inventory items
    Uses AI to extract categories, items, prices, and units
    """
    
    try:
        print(f"[INFO] Voice inventory parse request from user {user_id}")
        print(f"📝 Raw text: {request.raw_text}")
        
        # Get user's existing inventory
        statement = select(Item).where(Item.owner_id == user_id)
        existing_items = session.exec(statement).all()
        
        # Convert to dict format
        items_data = []
        categories_set = set()
        
        for item in existing_items:
            try:
                names_array = json.loads(item.names) if item.names else []
                items_data.append({
                    "id": item.master_id,
                    "names": names_array,
                    "price": item.price,
                    "unit": item.unit,
                    "category": item.category
                })
                categories_set.add(item.category)
            except Exception as e:
                print(f"[ERROR] Error processing item {item.id}: {e}")
                continue
        
        existing_categories = list(categories_set)
        
        print(f"[INFO] User has {len(items_data)} items in {len(existing_categories)} categories")
        
        # Parse voice input using AI
        parsed_data = parse_voice_inventory(
            raw_text=request.raw_text,
            existing_items=items_data,
            existing_categories=existing_categories
        )
        
        print(f"[OK] Parsed {len(parsed_data.get('categories', []))} categories")
        
        return parsed_data
        
    except Exception as e:
        print(f"[ERROR] Voice inventory parse error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to parse voice inventory: {str(e)}")
